Source: Hello Interview, "Design FB News Feed" system design walkthrough, presented by Stefan (ex-Meta and ex-Amazon interviewer and bar raiser, 2,000+ interviews conducted up to senior staff and manager level).

This breakdown designs a now dated, chronological variant of Facebook News Feed: users follow one another unidirectionally and view a time-ordered feed of posts from the people they follow. Modern feeds lean heavily on ML ranking, but this version stays chronological so the focus lands on the real crux: data modeling and fan-out. The core challenge is that News Feed is fundamentally about finding the posts from users you follow, and the cost of that lookup explodes at the tails of the follow graph. Users who follow thousands of accounts make the read path expensive, and accounts followed by millions make the write path expensive. The design works fine for the median user and falls apart at both extremes, so almost all the engineering goes into taming those extremes.

## Requirements

Functional requirements (kept to the core three or four, everything else marked below the line):

1. Users can create posts.
2. Users can follow other users (unidirectional).
3. Users can view a chronological feed of posts from users they follow.
4. Users can paginate through the feed (infinite scroll, consume a page then keep going).

Below the line (bonus, out of scope): likes, comments, post privacy settings. The advice: if you are short on time, do not even enumerate below-the-line items, just move to non-functional requirements. Do not rush requirements, but do not spend more than a few minutes here.

Non-functional requirements (the scaling and quality constraints, ideally quantified):

- Consistency model: eventual consistency is acceptable. When a user creates a post, they do not expect it to be in followers' feeds instantly, but they expect it to appear quickly. Budget: 1 minute for a post to propagate into followers' feeds. This number is later used to justify async propagation.
- Latency: responsive UI, a few hundred ms before users get annoyed. Target 500 ms for both posting and viewing.
- Scale: Facebook-sized, roughly 2 billion users. The exact number does not matter, it just sets bounds on storage and throughput.
- Read-heavy: far more feed reads than post writes, so the read path must absorb the bulk of traffic.

## Core Entities

The nouns in the design, kept minimal with no attributes attached yet (those get filled in as the high-level design develops):

- User
- Post (tracks creator, content, creation timestamp)
- Follow (a directed relationship: follower to followed)

The framing matters: News Feed is "finding the posts from users you follow," so the Follow edge and the Post-by-creator lookup are the entities that drive everything.

## APIs

Three REST endpoints, one per functional requirement. REST is recommended as the safe default. gRPC or plain function signatures are fine if you control the clients, but going non-standard without reason risks yellow flags from REST-zealot interviewers.

1. Create post:
   `POST /posts` with body `{ content }`, returns `201` with `{ postId }`.

2. Follow a user (create a follower edge, REST convention of putting to a sub-collection):
   `PUT /users/{id}/followers`. No body needed, there is no metadata on the edge.

3. Get feed with cursor pagination:
   `GET /feed?pageSize=25&cursor=<timestamp>`, returns `{ posts, nextCursor }`.

   The cursor is a `startAt` timestamp marking how deep into the feed the user has scrolled. On first load the user sees items from now back to some point X in the past (the timestamp of the last item returned). On the next request they pass that timestamp and get the next N items, all older than it. This guarantees the user can page through every published item even as they go deeper, with no gaps or duplicates from new posts arriving at the head.

## High-Level Design

The strategy is to build the simplest system that satisfies the functional requirements first, accept that it has warts, note them, and fix them in deep dives. Candidates who chase micro-optimizations before getting a working system on the board lose time and get stuck.

Post creation (write path):
- A Post Service sits behind an API gateway and load balancer, accepts `POST /posts`, and writes to a Post table.
- Backing store: DynamoDB (Cassandra or any scalable wide-column store is an equivalent substitute). Each post row stores creator, content, and timestamp.
- Scaling: add more Post Service instances as write volume grows. As long as you do not overload DynamoDB, this is genuinely scalable. First requirement done.

Follow (write path, with a deliberate anti-pattern call-out):
- A Follow Service writes to a Follow table. No graph database needed. Graph DBs (Neo4j, Cypher) earn their keep for multi-hop comprehensions like "find all users followed by at least two men who also follow each other." Here the only queries are "who does A follow" and "who follows A," which a wide-column store handles directly.
- Table design supports both directions:
  - Base table: partition key = userFollowing, sort key = userFollowed. Lists everyone a given user follows.
  - Global Secondary Index (GSI), Cassandra calls it a secondary index: partition key = userFollowed, sort key = userFollowing. Lists everyone who follows a given user. A GSI behaves like a second table that DynamoDB maintains internally and consistently.
- DynamoDB caps a range query at 1 MB of returned data. At ~10 bytes per user ID entry, that is a bit under 100,000 entries per request, then you page. Fine for everyone except the most-followed accounts, which foreshadows the celebrity problem.
- Lesson: start with the simple approach tightly fit to your needs and layer complexity only as required. Reaching for a graph DB early is a junior tell; simplicity is a hallmark differentiator of senior candidates.

Feed read (the naive read path, knowingly broken):
- A separate Feed Service handles reads because it is read-heavy and bears the full brunt of traffic, and merging feeds can be CPU-heavy.
- It can query the Post and Follow tables directly. Wrapping each table behind its own microservice API is rejected as over-engineering here: the decoupling benefit is dwarfed by the overhead. Do it only if the interviewer is a microservices stickler.
- Naive flow: take the requesting user ID, query the Follow table for everyone they follow, then for each followed user query the Post table for recent posts, then merge all those lists by time before returning.
- Needed index fix: the Post table's primary key is the post ID (good for fetching one post, useless for "posts by user X"). Add a GSI on the Post table keyed by creator and sorted by creation time so you can pull a user's recent posts.
- Acknowledged problems (deferred to deep dives, verbally flagged to keep momentum): a user following thousands of people triggers thousands of queries; creators with many posts return huge result sets. Roughly 10,000 follows could mean ~10 million aggregate posts merged in near real time.

Pagination:
- Reuse the cursor (oldest timestamp seen). When querying each followed user's Post GSI, fetch at most pageSize elements with `createdAt < cursor`, i.e. the most recent posts before that date. This pages backward infinitely.

The honest verdict on the high-level design: it satisfies the functional requirements and works for users with moderate follow counts, but breaks for users who follow or are followed by a lot of people.

## Deep Dives

### Deep dive 1: fan-out on read vs fan-out on write, and the high-follow-count problem

Problem: in the naive design (fan-out on read), a user following 10,000 people forces the Feed Service to make 10,000 Post GSI queries, returning maybe 10 million posts, all merged and sorted in near real time on every feed load. That is enormous CPU, network, and tail-latency cost, before even considering partial failures.

Solution: precompute the feed at write time instead of read time (fan-out on write). Add a Precomputed Feed table (could be a cache, kept in DynamoDB here for simplicity). When a post is created, read the post's followers from the Follow GSI and write the post ID into each follower's precomputed feed. The Feed Service then reads a user's feed directly from this table, which is very fast.

Sizing: cap the table at the latest ~200 post IDs per user. At ~10 bytes per ID, that is ~2 KB per user. For 2 billion users that is ~2 TB total. Cheap and reasonable (gut check: Facebook earns ~$100 per US user per year, so 2 KB of storage per user is trivial).

Trade-off: fan-out on write makes reads cheap but makes writes expensive, and shifts the cost to the worst place when a popular account posts. This is the central tension that the rest of the design negotiates.

Sub-problem, fan-out write cost for high-follower accounts: a user with 10,000+ followers generating one post now requires tens of thousands of precomputed-feed writes. Do not do this synchronously inside the Post Service, or a page like "Hello Interview" would wait up to 60 seconds to publish a status. Use an async worker pool:
- On post creation, enqueue an entry on a centralized queue of post updates.
- Workers pull the job, read the Follow GSI for all followers, and write the post ID into each follower's precomputed feed.
- If the follower set is large, split it into smaller sub-jobs pushed back onto the queue, spreading load across many feed workers.
- The 1-minute eventual-consistency budget from the NFRs is what makes this async propagation acceptable.

### Deep dive 2: the celebrity / mega-account problem and the hybrid approach

Problem: even async fan-out on write does not work for mega accounts (e.g. Justin Bieber) with hundreds of millions of followers. Broadcasting a write to every follower is inappropriate at that scale, and pulling that many followers out of DynamoDB requires heavy paging through the 1 MB-per-query limit.

Solution: a hybrid of fan-out on write (for normal accounts) and fan-out on read (for celebrities). Add a column on the Follow table that flags whether the relationship is precomputed. Set the flag off when the followed account has a ton of followers, threshold around 100,000+.
- If the flag is set (normal account): when that user posts, feed workers write the post ID into followers' precomputed feeds (the write path).
- If the flag is not set (celebrity): feed workers ignore that follow, no fan-out on write.
- At feed-read time, the Feed Service does both: it reads the user's precomputed feed table, and separately lists the not-precomputed (celebrity) follows and pulls their latest N posts live, then merges the two lists at runtime before returning.

Trade-off: this caps the number of writes per post creation (no broadcast for mega accounts) and caps the number of live reads per feed query (only the handful of celebrities a user follows). It blends the strengths of both fan-out strategies.

The rabbit hole keeps going (good follow-up territory left as exercises): what if a user follows a large number of huge accounts? What happens on unfollow? Does the precomputed flag ever reverse? Pragmatic note: many platforms enforce product limits rather than engineer to infinity. Google will not page you to result 1000, LinkedIn caps connections. It is often not worth engineering around the 0.001% of users; at some point you throw in the towel.

### Deep dive 3: the hot-key / hot-shard problem and feed caching

Problem: when a popular account publishes, that single post ID lands at the top of millions of feeds, so a huge number of accounts simultaneously query for one post ID in the Post table. DynamoDB (and similar) is only scalable when load is relatively even across keys, because partitions ultimately map to physical hosts with real performance limits. If all requests hit the host owning that key, having a thousand other idle hosts does not help, you get throttled or fail. This class of problem is the hot key or hot shard.

Solution attempt 1, cache the hot partition: put a distributed cache in front, with LFU (least-frequently-used) eviction and a short TTL. Posts rarely change, so a short TTL is safe, and you only cache the most viral / highest-reach posts, so memory is small. Ideally a million requests collapse into one DynamoDB request. This is what many mid-level and even senior candidates propose, and it is incomplete.

The catch: if the distributed cache is sharded by post ID, the cache itself has the same hot key. Because Redis is in-memory, its throughput might absorb the load, but the fundamental single-key bottleneck remains.

Solution attempt 2, replicate instead of shard the hot read: run multiple independent cache instances rather than sharding the cache. The Feed Service picks an instance at random per request. The instances do not need to be replicas of each other or coordinate in any way. Now instead of one request reaching DynamoDB, N requests do, where N is the number of cache instances. Since N is far smaller than the millions of incoming requests, this is a great trade-off and solves the hot key.

Level expectations: caching the hot partition (attempt 1) is where mid-level and even senior candidates often stop. Recognizing that the cache itself inherits the hot key, and resolving it by replicating cache instances and randomizing reads (attempt 2), is the deeper signal. There is a lot of subtlety in how data is sharded, and interviewers pick and choose where to probe. Interviewers commonly take control at this stage and drill into a specific weak point even if you already acknowledged it; that is not a sign you got something wrong, it is how they calibrate the depth of signal they need. Much of the hiring signal is implicit and never appears on the whiteboard, it is about observing your solution-design process.

## Key Concepts

- Fan-out on read vs fan-out on write: fan-out on read computes the feed at query time (cheap writes, expensive reads, bad for high-follow-count users); fan-out on write precomputes feeds at post time into a per-user precomputed-feed table (cheap reads, expensive writes, bad for high-follower-count accounts).
- Hybrid fan-out: combine both. Precompute for normal accounts (flag on), read live for celebrities above a follower threshold (~100k, flag off), then merge the precomputed list with live celebrity posts at read time. Caps both write amplification and read fan-out.
- Hot-key / hot-shard problem: skewed load on a single key (one viral post ID, one partition) throttles a single physical host regardless of total cluster capacity. Caching helps but the cache shard inherits the same hot key; the fix is multiple uncoordinated cache instances with randomized read routing (replicate the hot read, do not shard it).
- Feed caching: shield hot DynamoDB partitions with a distributed cache (LFU eviction, short TTL) holding only the most viral posts; pair with cache replication to avoid recreating the hot key.
- Async worker pool / queue-based fan-out: propagate post-creation writes off the critical path via a centralized queue and worker pool, splitting large follower sets into sub-jobs to spread load; justified by an eventual-consistency budget (here, 1 minute).
- Denormalization: the precomputed-feed table is denormalized, derived data (per-user copies of post IDs) traded for read speed at the cost of write amplification and storage.
- Wide-column data modeling with GSIs: model bidirectional relationships and creator-time lookups using partition/sort keys plus global secondary indexes (reverse the keys on the GSI) instead of reaching for a graph database.
- Cursor pagination: page an append-at-head feed by a timestamp cursor (`createdAt < cursor`) for gap-free, duplicate-free infinite scroll.
- Process over answer: identify a bottleneck, propose a solution, then find the bottleneck in that solution, and repeat. Favor simple, tightly-fit designs early and layer complexity only when needed; know when to stop via product limits rather than engineering to infinity.
