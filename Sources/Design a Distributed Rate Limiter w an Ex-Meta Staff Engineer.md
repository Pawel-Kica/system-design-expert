This is a HelloInterview walkthrough (Evan, ex-Meta staff engineer) of the classic "Design a Distributed Rate Limiter" problem, still asked heavily at Microsoft and reportedly at OpenAI. A rate limiter controls how many requests a client can make in a given time frame (for example 100 requests per minute per user) to protect backend services from abuse and overload. The core challenge is not the algorithm itself but making the limiter fast (sub 10ms added latency), globally consistent across many gateway instances, scalable to a million requests per second, and fault tolerant, while choosing a counting algorithm whose accuracy and memory cost fit the workload. The design is explicitly server side; client side limiting is dismissed as spoofable and low value.

## Requirements

Functional requirements (framed in the order a request flows through the limiter):

1. Identify the client. The limiter must know who is making the request (user ID, IP address, or API key) so it can attribute counts and apply the correct limit.
2. Limit requests based on configurable rules. The heart of the system. A rule looks like "any user can make 100 requests per minute," possibly scoped to a specific endpoint.
3. Return proper error headers and status codes. Do not return an opaque 500. Tell the client they are rate limited and give metadata so they can decide what to do next.

Non-functional requirements (the qualities, each one is later addressed in a deep dive):

- Availability over consistency (CAP). Partition tolerance is a given. We choose AP: if a new rule is propagating, the limiter should keep working on slightly stale rules rather than go offline. The limiter must always be up because it protects the system.
- Low latency rate limit checks, target under 10ms added per request. The limiter sits in the hot path of every user request, so it must not noticeably slow the call.
- Scalable to 1 million requests per second (assumed scale: 100M daily active users on a social media style app).

Scale clarification matters here. Always ask the interviewer "what am I rate limiting?" (user facing app vs developer tooling vs intra microservice traffic). The canonical answer is a user facing social app at 100M DAU, roughly 1M req/s.

## Core Entities

- Request: the incoming request, carrier of the identifying information.
- Client: the "who," derived from IP address, user ID, or API key.
- Rule: the limit definition, for example "100 requests per user per second."

These are sketched in under a minute for a backend component; they matter less than for a user facing product but still frame the problem.

## APIs

Because the client does not call the rate limiter directly (it calls the app's API, and the system internally checks the limiter), this is a system interface, not a public API. Model it as a single internal function (RPC or in-process call):

```
isAllowed(clientId, rule) -> { allowed: boolean, remaining: int, resetAt: timestamp }
```

It returns whether the request passes, plus the metadata the functional requirements demand (requests remaining, when the window resets). The exact metadata depends on the chosen algorithm.

## High-Level Design

Two coupled questions drive the design: where does the limiter live, and how do we identify clients. Placement determines what client context is accessible, and identification influences placement.

Where to place the limiter, three options:

1. Inside each microservice (in application code). The server checks its local in-memory counts, updates, and decides. Extremely fast, no network calls, no external dependency. Fatal flaw: no global picture. If one user request hits service A and another hits service B, each sees only one request while the user globally made two. Lack of coordination makes this a poor option.
2. As its own standalone rate limiter service. Every microservice calls it before processing. Solves global coordination, but adds a network hop (gateway to microservice to separate limiter service and back) on every request, eating into the tight latency budget. The added network overhead is not worth it.
3. At the edge, inside the API gateway or load balancer (the chosen approach, and what most production systems do). Every incoming request hits the limiter first, before routing. The analogy: a bouncer at the club, troublemakers turned away at the door rather than after they are inside causing problems.

Edge placement trades away deep business context. In application code you can see everything (for example "premium users get 10x limits" using DB state). At the edge you only see the HTTP request: headers, URL, IP, and auth tokens. The fix: encode the needed context in the request, typically a JWT in the headers that asserts premium status. Microservices then focus purely on serving requests and know nothing about rate limiting.

How to identify clients: the three options are user ID, IP address, API key. The strongest answer is a combination with layered rules rather than one global limit. For example authenticated users get higher limits than anonymous IPs, premium users get more still: "Alice can make 1000 req/s, any IP can make 100 req/s, an API key can handle 50,000 req/s." All identifiers come from the request, usually the headers.

The counting itself uses a per-client counter that resets each window in the simplest form, with the algorithm choice (below) determining accuracy and memory.

## Deep Dives

### Choosing the rate-limiting algorithm

In a system design interview the algorithm is usually not the main focus (unlike low-level design). You must know the options, weigh trade-offs, and justify a choice, but you will likely not implement it, not even in pseudocode. Four algorithms worth knowing, simplest to most capable:

**Fixed window counter.** Users get N requests per fixed window (for example 100 per minute). Maintain a per-client counter that resets at the start of each window; reject once it exceeds the limit. Implementation: a hash table mapping client ID to (counter, window start). Trivial to implement. Downsides: the boundary effect, a user can fire 100 requests at 12:01:59 and another 100 at 12:02:00, getting 200 in roughly two seconds across the boundary; and starvation, if you spend your 100 early you wait the rest of the window with zero allowance.

**Sliding window log.** Track the exact timestamp of every request in a rolling window (for example "max 100 requests in the last rolling minute"). Eliminates the boundary effect and burst problem and gives perfect accuracy because it knows every request time. Downside: typically implemented with a heap or deque, so it costs far more memory per user, needs more instances, and is more expensive at scale.

**Sliding window counter.** The memory fix for the sliding window log. Keep only two counters per user: the previous fixed window and the current one. Estimate a true sliding window by weighting the previous window by the fraction of the current window remaining. Example: previous window had 8 requests; we are 70% (42s) into the current minute with 6 requests so far. Estimate = current 6 + 30% of previous 8 = 6 + 2.4 = 8.4. If the limit is 10, 8.4 < 10, so allow. Far better accuracy than fixed window using only two integers per user (no heap). Downside: it is an approximation that assumes requests are evenly spread across each window, which is not always true.

**Token bucket (the chosen algorithm).** Each client has a bucket holding tokens. The bucket size is the burst capacity; tokens are added at a steady refill rate. Each request consumes one token; if no tokens are available, reject. Two knobs cleanly separate two concerns: bucket size handles bursts (a bucket of 100 absorbs a burst of 100), refill rate sets the sustained rate (refill 10 tokens/minute means a steady 10 req/min). So a client can fire 100 immediately, then waits for refill at the slower steady rate. Elegant and simple: store only two numbers per client, the current token count and the last refill timestamp. The challenge is choosing the right bucket size and refill rate and handling cold starts.

### Storing and computing the token bucket (distributed state in Redis)

Each bucket tracks token count and last refill timestamp. The state must be shared across all gateway instances, because production runs many gateways; without shared state you reproduce the per-microservice coordination problem. Pull the state into an in-memory cache (Redis). All gateways read and write the same shared bucket state.

Per-request flow:

1. Request comes in.
2. Gateway fetches the bucket from Redis. Use `HMGET` to read multiple fields in one command, for example Alice's tokens and last refill together.
3. Compute tokens to add based on elapsed time since last refill. If last update was 30s ago and refill is 1 token/sec, add 30 tokens. If she was at 20, she is now at 50.
4. Respond pass or fail based on whether tokens after refill is greater than zero.
5. Update the bucket: write back the new token count and set last refill to the current timestamp (`HSET`).

### Race conditions and atomicity via Lua scripts

The read-then-write flow has a read-after-write race. Picture gateway A and gateway B, with Alice sending two requests, one to each. Both read Redis and see tokens = 1. Both check 1 > 0 and accept. Both write back. The second write overwrites the first, so two requests passed against a single token. The read and the write must happen atomically as one unit.

In Postgres this is done with transactions and locking. In Redis, it is single threaded and supports atomic transactions, which makes this easier: use Lua scripting. Bundle the `HMGET`, the refill computation, and the `HSET` into a single Redis Lua script. It goes over the wire once, does the read and write atomically, and returns pass or fail. One script runs to completion while any other waits, eliminating the race. Proactively recognizing this race and explaining Lua scripting is flagged as a staff-level move.

### Returning errors (fail fast)

One decision: on exceeding the limit, reject immediately or queue and retry later. Choose fail fast: send failure back at once, do not queue. Queuing an interactive request means the user waits, assumes it is broken, retries, and the backlog grows into a worse problem. Queuing only makes sense for niche batch processing or intra-service communication that can afford to wait. For an interactive API, fail fast is correct.

Return HTTP 429 (Too Many Requests), the standard code, plus best-practice headers: `X-RateLimit-Limit` (the ceiling), `X-RateLimit-Remaining` (requests left in the current window, semantics depend on the algorithm), `X-RateLimit-Reset` (when it resets), and commonly `Retry-After` (for example "try again in 60 seconds"). Interviewers expect you to know 429; you do not need to memorize the exact header names, just say you will return a 429 with appropriate headers telling the user when to retry and how many remain.

### Scalability to 1M req/s (sharding)

A single Redis instance handles roughly 100k ops/sec depending on hardware, a tenth of what is needed. Each rate-limit check is two operations (the read and the write), so effectively about 50k req/s per instance. Solution: shard the data across multiple Redis instances by client ID, so Alice's bucket lives on instance 1 and Bob's on instance 2. At 1M / 50k that is at least 20 instances, plus headroom. The gateway must always route to the instance holding that client's bucket; you cannot check a random instance, and replicating all data everywhere reinstates the problem and blows past in-memory size limits (instances are bounded, for example 64GB+). Shard on the client ID using consistent hashing. In practice use Redis Cluster, which manages sharding for you via hash slots (around 16,384 slots, stated loosely as "60,000" in the talk) distributed across nodes rather than raw consistent hashing. The conceptual takeaway: multiple instances, so you must shard.

### Availability and fault tolerance (replicas, fail open vs fail closed)

If a Redis node holding Alice's bucket dies, Alice cannot be rate limited. Two failure stances:

- Fail open: limiter down, let every request through. Risk: backends lose the protection they relied on (DB read limits, cache, CPU/GPU compute budgets), microservices get overwhelmed one by one, cascading failures, potentially worse than the original problem.
- Fail closed: limiter down, reject everything. Risk: the site appears down, angry users.

No universally right answer. The talk leans fail closed for a protective limiter (take the strictest stance and reject). In real production a smarter fallback is common: keep a single in-memory fixed-window counter in each gateway as a temporary degraded mode while Redis recovers, accepting the loss of cross-gateway coordination, which beats both pure stances because some limiting survives.

To minimize downtime, use replicas. Configure a replication factor so each Redis shard has one or two replicas; writes propagate to replicas, and if a primary dies its replica is promoted and reads move to it. Redis Cluster supports this with async replication, consistent with the AP choice: a write that fails before async propagation loses a little data (Alice ends at 99 instead of 100, one extra request, not catastrophic). The keys to availability and fault tolerance: sharding and read replicas, both provided by Redis Cluster.

### Low latency (connection pooling, geographic co-location)

Every check now needs a network round trip to Redis. Redis ops are sub-millisecond, but network overhead can be several ms, and a fresh TCP handshake can add 20 to 50ms depending on distance. The key optimization is connection pooling: the gateway keeps a pool of persistent TCP connections to Redis and reuses them, eliminating per-request handshake cost. Most Redis clients do this automatically; you may need to tune pool size to request volume and Redis response time. Mention that you understand the client likely handles pooling. Second lever: geographic distribution. Place gateways close to users (a gateway in Asia/Japan for Tokyo users) and co-locate Redis with the gateway, ideally the same data center, to minimize latency.

### Dynamic rule configuration

So far rules were assumed static (hardcoded at gateway deploy, changing them requires a redeploy). In production rules are configurable, often per user or per tier. Options:

- Store rules in a database, gateway polls every N seconds (5 to 20s). Downsides: propagation delay, and tighter polling burns gateway CPU that should serve traffic.
- Store rules in Redis and poll, or check rules on every rate-limit request. Adds operations and latency to every check for data that rarely changes. Workable but not ideal.
- Best: push-based configuration management via ZooKeeper (older) or a more modern equivalent. The gateway fetches rules at startup, holds them in memory (no per-request network check), and subscribes for changes over a persistent TCP connection. When a rule changes, it is pushed to the gateway, which updates its in-memory copy. No polling, no added latency, fresh rules.

### Level expectations

- Mid-level: ~80% breadth, 20% depth. Know the algorithms, pick and justify one, understand them conceptually (no need to code them), place the limiter at the edge, propose shared global state (Redis/Memcached) and justify it, and problem solve toward reasonable answers when the interviewer probes single-instance limits and failure modes.
- Senior: proactively identify issues. State unprompted that a single Redis node is insufficient, show the math, give the shard count and shard key, and discuss fault tolerance and overload failure modes (fail open vs fail closed).
- Staff: this question is rarely asked at staff level (easy-to-medium). If asked, lead proactively through everything above and steer toward areas of deep experience, for example real Redis Cluster connection-pool sizing mistakes, or proactively naming the race condition and explaining the Lua scripting fix.

## Key Concepts

- Token bucket: per-client bucket, size = burst capacity, refill rate = sustained rate, one token per request; stores only count + last refill timestamp.
- Fixed window counter: per-window count; trivial but suffers boundary bursts and starvation.
- Sliding window log: exact timestamps in a rolling window; perfect accuracy, heavy memory (heap/deque).
- Sliding window counter: weighted blend of previous and current fixed windows; near-sliding accuracy with two integers, an even-distribution approximation.
- Edge placement of the limiter (API gateway / load balancer) as the standard production choice; context must be carried in the request (JWT in headers).
- Distributed counters in Redis: shared bucket state across gateways via an in-memory cache.
- Redis atomic ops and Lua scripting: bundle read + compute + write into one atomic script to kill the read-after-write race (Redis single-threaded).
- Sharding with Redis Cluster: shard by client ID via hash slots (conceptually consistent hashing) to scale past a single instance's ~50k req/s for rate checks.
- Replication for fault tolerance: async replicas per shard, promote on failure (AP trade-off, minor data loss acceptable).
- Fail open vs fail closed: the limiter's failure stance; in-memory fixed-window fallback as a degraded middle ground.
- Fail fast: reject over-limit requests immediately with HTTP 429 plus rate-limit headers, never queue interactive requests.
- Connection pooling and geographic co-location: latency optimizations for the Redis round trip in the request hot path.
- Push-based dynamic configuration (ZooKeeper or modern equivalent): rules held in gateway memory, updates pushed over a persistent connection, no polling.
