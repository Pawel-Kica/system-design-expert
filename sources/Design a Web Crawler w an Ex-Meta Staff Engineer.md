Source: HelloInterview, "Design a Web Crawler" by Evan (ex-Meta staff engineer and interviewer, co-founder of HelloInterview).

A web crawler is a program that traverses the web by downloading pages and recursively following the links it finds. The scoped version of the problem: build a crawler that extracts text data from the web and stores it, with the goal of feeding that text to train an LLM. The hard constraint is time. The crawl must finish in 5 days, so the design is not about clever features but about running a fault-tolerant, polite, and efficient pipeline at the scale of 10 billion pages. The job ends when text lands in storage; tokenization and training belong to the ML team.

## Requirements

Functional:

1. Crawl the full web starting from a set of seed URLs.
2. Extract text data from those pages and store it somewhere (a database / blob store).

Scale assumptions (asked of the interviewer or estimated):

- 10 billion web pages.
- 2 MB average page size.
- 5 days to complete the crawl (hard deadline, "OpenAI is killing it, we need this data ASAP").
- Resources: effectively unlimited within reason (not cost-constrained).

Non-functional (the "how", and quantified where reasonable):

- Fault tolerant: handle failures gracefully, resume without losing significant progress.
- Polite: adhere to robots.txt and per-domain rate limits so we never effectively DOS a site.
- Scalable: reach 10 billion pages.
- Efficient: complete the crawl in under 5 days.

Note on estimation: the presenter deliberately skips back-of-envelope math up front. Doing math just to conclude "that's a lot" teaches nobody anything. Math should be done at a specific decision junction where the number changes the design (here, computing how many crawler machines are needed). That is a more senior, more realistic habit.

## Core Entities

- Text data: the output, the parsed text per page.
- URL metadata: the URL itself plus whether it has been crawled, the S3 link to its stored HTML, last-crawled time, content hash, crawl depth.
- Domain metadata: per-domain because robots.txt rules apply at the domain level, not the URL level. Holds the domain, last-crawled time, and the robots.txt fields (user-agent, disallow paths, crawl-delay).

## Interface

Not a user-facing product, so describe the interface (inputs/outputs) rather than a REST API.

- Input: a set of seed URLs (plus URL metadata).
- Output: the text data parsed from all crawled pages.

## Data Flow

The crawl loop, kept deliberately high level so it can drive the high-level design:

1. Take a URL off the frontier (the set of URLs yet to be crawled, initially the seed set) and resolve its IP via DNS.
2. Fetch the HTML for the page.
3. Extract text from the HTML.
4. Store the text in a database.
5. Extract the URLs found in the page and add them to the frontier.
6. Repeat 1 through 5 until the frontier is empty.

## High-Level Design

A frontier queue holds URLs to crawl, seeded with the seed URLs. This queue is a message queue (Kafka or SQS, decided later in deep dives).

A pool of crawler workers pulls a URL off the queue and does everything: resolve DNS, fetch the page HTML, extract text, extract URLs. DNS and the target web pages are external to the system.

The worker writes the extracted text to blob storage (S3, the right tool for large binary/text payloads). Any URLs it pulled off the page go straight back onto the frontier queue. Loop forever until the frontier drains.

This simple design satisfies the functional requirements. Everything interesting happens in the deep dives, where it is evolved to satisfy the non-functional requirements.

## Deep Dives

### Fault tolerance: split the monolithic worker into pipeline stages

Problem: the single crawler does too much (pull URL, fetch HTML, extract text, extract URLs). If any step fails, all prior work is lost. Even with idempotency hacks (store HTML, then re-check on retry), one worker doing everything gives no separation of responsibility, no independent scaling per stage, poor observability (you cannot see where a URL is in the process), and fragility against changing requirements.

Solution: for any data-pipeline question, split the work into smaller stages. Here, two phases:

- Phase 1 (crawler): pull URL off frontier queue, fetch the page, store raw HTML in S3, update URL metadata (URL as primary key, plus the S3 link to the HTML). Fetching is the most error-prone step (sites down, slow servers, errors, rate limiting), so isolate it. Once raw HTML is safely in S3, the hard part is done.
- Phase 2 (parsing worker): a new parsing queue connects the stages. The crawler puts a small JSON pointer ({ URL, S3 link }) on this queue. The parsing worker fetches HTML from S3, extracts text, stores text back in S3, extracts URLs, and pushes new URLs back onto the frontier queue.

Why a pointer on the queue, not the HTML itself: SQS/Kafka default to roughly 1 MB max message size (configurable), and pages average 2 MB. Best practice is to keep queue payloads tiny and let blob storage hold the bytes. Putting the S3 link directly in the message means the parser does a single fetch from S3 rather than first looking up URL metadata.

Trade-off win: the pipeline is now robust to changing requirements. If the ML team later wants OCR text or image alt-text, you do not re-crawl the internet. You reload all URLs into the parsing queue, update parsing logic, and rerun phase 2 against the already-stored HTML.

### Retries with exponential backoff

Problem: fetching a URL often fails (500s, timeouts). The naive fix is an in-memory timer in the crawler (wait 5 to 10 seconds, retry). Bad: if the crawler dies the timer is lost, and 5 seconds is rarely long enough for a struggling server to recover.

Solution: a real retry strategy with exponential backoff, which needs persisted state.

- Kafka option: Kafka has no built-in retries. Implement them with a separate topic for failed URLs. The crawler computes the backoff and writes into the message the absolute time the URL should next run, then puts it on the fail topic. The next worker reads that time, waits until then, and retries, increasing the backoff exponentially on each failure. Works, but it is manual and messy. The upside: if the crawler dies, another worker still has the correct retry time because it lives in the message.
- SQS option (chosen): SQS supports retries with configurable exponential backoff out of the box. Failed messages are retried once per visibility timeout (default 30 seconds), and the timeout grows exponentially per attempt (30s, 2m, 5m, 15m). Configured by file, not code.

Visibility timeout: the period during which other consumers cannot receive or process a message that one consumer has pulled. Central to both retries and crash recovery below.

Cap the retries: do not retry forever (the site may simply be gone). Set a maximum via the SQS `approximate receive count` field (for example, 5). On the fifth attempt, SQS automatically moves the message to a configured dead-letter queue. A dead-letter queue is a special message queue holding messages that cannot be processed. These are likely dead pages, so we ignore them or ask the product team what to do.

Level expectation: no candidate is expected to know SQS-vs-Kafka internals at this depth. It is one optional place to show technical depth. Staff candidates should show real depth in about three places; senior in one or two; mid-level much less. A perfectly good answer at any level is "an in-memory timer will not work, I need exponential backoff with persisted state."

### Crash recovery: messages stay until confirmed processed

Problem: what if a crawler dies mid-fetch?

Solution: spin up a new crawler. The URL is not truly removed from the queue when pulled. It stays until the fetch is confirmed (HTML written to S3), then it is removed.

- Kafka: each message has an offset. Crawlers share a consumer group, which guarantees each message is read by only one worker in the group (no duplicate processing). After storing to S3, the worker commits the offset so others know it is done. Messages are not deleted on commit; they age out by a retention policy (default about 7 days, also a size cap, roughly 10 GB, both configurable).
- SQS: messages remain until explicitly deleted. The visibility timeout hides a pulled message from other crawlers (for example 30 seconds). If the owning crawler dies, the timeout elapses and the message becomes visible again for another crawler. On success, the crawler issues a delete command to remove it.

### Politeness: robots.txt and per-domain crawl delay

robots.txt is a per-domain file specifying crawl rules. Key fields: `user-agent` (which crawler the rules apply to, `*` means all), `disallow` (paths that may not be crawled, for example `/private`), `crawl-delay` (seconds to wait between requests to this domain, for example 10).

Solution: the first time a domain is seen, fetch its robots.txt and store it in a domain table in the metadata DB (domain, last-crawled time, user-agent, disallow, crawl-delay). On subsequent crawls, read from this table. For each URL:

1. Check the domain rules. If the path is disallowed, acknowledge the message (Kafka: move the cursor; SQS: delete it) to drop it without crawling.
2. Check timing: if `now - last_crawled_time > crawl_delay`, crawl it. Otherwise put it back on the queue, setting the SQS visibility timeout to the remaining crawl delay so it waits the right amount.

Refinements to mention but not necessarily build: robots.txt can change, so give it a TTL and refetch when expired. A cache (Redis) for domain rules speeds the read, though we are IO-bound on the page fetch so this is minor.

### General rate limiting and jitter

Even without a crawl-delay (most sites set none), the internet standard is no more than 1 request per second per domain.

Solution: a per-domain rate limiter, for example Redis with a sliding-window algorithm counting requests in the last second. The crawler checks the limiter (tens of milliseconds). If over the limit, put the URL back on the queue with a visibility timeout.

Apply jitter: add randomness to the wait. Without it, 10 crawlers all rate-limited on the same domain re-enqueue, get pulled at the same time, hit the limiter together, only one passes, and the herd repeats. Jitter spreads them out.

### Smart scheduler (the per-domain backlog problem)

Problem: even with jitter, extracting URLs from one page tends to yield many URLs from the same domain. You enqueue a backlog of 20 to 500 same-domain URLs, they get pulled, all hit the crawl-delay or rate limiter, all bounce back. Wasted cycles.

Solution (described, not drawn, because it is somewhat abstract): a smart scheduler. Instead of pushing extracted URLs straight onto the frontier queue, write them into URL metadata (with crawled/not-crawled state and last-crawled time). When the frontier queue runs low, the scheduler queries the metadata, applies an ordering algorithm (or a priority queue) to interleave domains, and feeds URLs onto the queue. This avoids hammering one domain. Valid and worth raising for senior and especially staff candidates who want to go deep; excluded from the main design for simplicity.

### Scale and efficiency: how many crawler machines

Save scalability for last, because the system keeps evolving (scaling the crawler early would have missed the later parsing stage and parsing queue).

This is the right place to do math, because it drives a real decision (machine count).

- Top AWS network-optimized instances handle about 400 Gbit/s.
- Pages average 2 MB.
- 400 Gbit/s divided by 8 bits/byte, divided by 2 MB/page = roughly 25,000 pages/second per machine. That is absurdly high and would finish in under 5 days on one machine, but you can never use 100% of bandwidth.
- Real overheads (DNS, rate limiting, crawl delays, slow responses, retries) make full utilization impossible. Assume roughly 30% usable: 25,000 * 0.3 ~ 10,000 pages/second (10^4).
- 10 billion pages (10^10) / 10^4 = 10^6 seconds on one machine.
- 10^6 seconds / ~10^5 seconds-per-day ~ 10 days on one machine.
- It scales linearly: 2 machines = 5 days. Add leeway for errors and the parsing stage: about 4 network-optimized crawler instances.

Caveat the presenter states explicitly: in reality you would run a throughput test and multiply out. The interview math is intentionally hand-wavy.

Parsing workers: the bottleneck is fetching, so everything downstream just needs to keep up. Scale the parsing workers dynamically off the parsing queue depth (EC2, Lambda, any containerized compute). If the queue backs up, add workers.

### DNS as a bottleneck

Often overlooked. A third-party DNS provider has rate limits.

Solutions:

- Throw money at it to raise the rate limit (we are not cost-constrained).
- DNS caching: reuse the existing Redis instance (already doing rate limiting) to cache domain to IP. Hit DNS once per domain, then serve from cache. Big reduction in DNS requests.
- Round-robin across multiple DNS providers: distributes load and reduces the risk of any single provider rate-limiting or having an outage. Praised as a practical, real-world answer (a staff candidate suggested it). It signals you think like an engineer in a room solving a live problem, not someone reciting a textbook.

### URL deduplication (do not crawl the same URL twice)

Extracting URLs yields heavy duplication; most extracted URLs are already known.

Solution: make the URL the primary key in URL metadata and check existence on insert. To avoid enqueuing duplicates onto the frontier, have the parsing worker write the new URL into the metadata DB at enqueue time (with last-crawled time = undefined), and fill in real last-crawled time and S3 link once parsed.

Scale: 10 billion rows is large, so shard on the primary key (the URL). Lookups stay O(log n), fast, and this is not the bottleneck anyway.

### Content deduplication (do not parse duplicate content)

Less obvious: two different URLs, even on different domains, can have identical content. This happens far more than expected.

Solution: hash the HTML in the crawler and store the hash in URL metadata. Before pushing to the parsing queue, check whether that content hash already exists; if so, skip it. The check must be efficient. Options:

- Global secondary index on the hash (presenter's pick). With DynamoDB, a GSI on the hash gives O(log n) lookups, more than fast enough, and these stores are colocated in the same VPC. Simple, no extra hardware.
- Auxiliary in-memory hash set in Redis (a Redis set of hashes). O(1) lookups, tens of milliseconds, nothing hits disk. Math: 10^10 pages * ~20 bytes/hash ~ 200 GB, which still fits a single 256 GB Redis instance. Trade-offs: extra hardware, extra cost, must maintain fault tolerance and persistence if Redis dies.
- Bloom filter: a space-efficient probabilistic structure for set membership. Returns "possibly in set" or "definitely not in set"; false positives are possible, false negatives are not. A false positive means we wrongly think content is already parsed and silently drop real content. The presenter pushes back hard: candidates reach for the bloom filter reflexively (from Alex Xu's books, Grokking, etc.) without first establishing that they are memory-constrained. Given we are not memory-constrained and 200 GB fits one Redis box, the bloom filter is the wrong default. Reciting it without justifying the constraint is a weak signal. Only consider it if explicitly told Redis must be tiny.

### Crawler traps

Pages designed to keep crawlers on a site indefinitely: a page linking to itself many times, or linking to endless near-empty pages on the same domain (hundreds of thousands deep), yielding no useful content.

Solution: enforce a max crawl depth (for example 20). Add a `depth` field to each URL in metadata. When the parsing worker adds a newly extracted URL, set its depth to the current URL's depth + 1. If depth exceeds the threshold, do not enqueue it.

### Other deep dives (mentioned, not built)

- Dynamic content: JS-rendered sites (React, Angular) need a headless browser (Puppeteer) in the crawler to render before extraction. Slower, more error-prone, more expensive. Worth asking the interviewer about up front.
- Monitoring: data dog, New Relic, etc., to track where URLs sit per phase and surface main errors. The phase split already aids observability.
- Large pages: use the `Content-Length` header to skip downloading oversized files.
- Continual updates: for an indexer (Google) or periodic retraining, run the crawler continuously via the smart URL scheduler. It periodically queries URL metadata, uses last-crawled time, and re-enqueues stale URLs onto the frontier.

## Level Expectations

- Mid-level: about 80% breadth, 20% depth. Reach the high-level design, then competently answer the interviewer's follow-ups (retries, crashes, dedup) and evolve the design. Missing some depth (for example DNS) is fine.
- Senior: somewhere in the middle, lead the conversation where it makes sense, show one or two genuinely deep areas.
- Staff: reach the high-level design fast, confidently work through each non-functional requirement, and show real technical depth in about three places (message-queue internals, DNS strategy, dedup trade-offs are all candidates). Never monopolize the conversation; leave room for interviewer steering.

## Key Concepts

- Frontier queue: the set of URLs yet to be crawled, implemented as a message queue (SQS or Kafka), seeded with seed URLs, drained as the loop runs.
- Pipeline staging: split a monolithic worker into independent stages (fetch HTML, then parse) connected by queues, for independent scaling, observability, retry isolation, and robustness to changing requirements.
- Pointer-on-queue pattern: keep queue payloads tiny by storing a pointer (S3 link) instead of the large blob, which lives in blob storage.
- Exponential backoff with persisted state: never retry on an in-memory timer; encode the next run time in the message (Kafka) or use the SQS visibility timeout, capped by a max receive count into a dead-letter queue.
- Visibility timeout: SQS mechanism that hides a pulled message from other consumers, powering both retries and crash recovery (message reappears if the owner dies).
- Politeness and per-domain rate limiting: honor robots.txt (disallow, crawl-delay) plus a default 1 req/sec/domain ceiling, enforced by a Redis sliding-window limiter, with jitter to prevent thundering-herd re-enqueues.
- Smart scheduler: feed the frontier from URL metadata in a domain-interleaved order to avoid same-domain backlogs starving on the rate limiter.
- DNS caching and provider round-robin: cache domain to IP in Redis and rotate multiple DNS providers to dodge rate limits and outages.
- URL dedup: URL as sharded primary key, existence check before enqueue.
- Content dedup via hashing: hash the HTML and check set membership before parsing. Prefer a DynamoDB global secondary index or a Redis hash set over a bloom filter unless genuinely memory-constrained.
- Bloom filter: space-efficient probabilistic membership test, trades accuracy for space, false positives possible (here meaning silently dropped content). Justify the memory constraint before reaching for it.
- Crawler traps and max depth: bound recursion with a per-URL depth counter to escape self-referential or infinite same-domain link farms.
- Backpressure / dynamic downstream scaling: scale parsing workers off queue depth since fetching is the bottleneck; downstream stages only need to keep up.
- Estimate to decide, not to impress: do scale math only at a junction where the number changes the design (machine count), and prefer a real throughput test in practice.
