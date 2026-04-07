Last updated: 2026-04-07

> For deeper detail on any topic, browse the full transcripts and notes in this folder.

## Networking & Communication

**Client-Server Architecture** -- The foundation of web applications. A client (browser, mobile app) sends requests to a server, which processes them and returns responses. The server runs continuously, waiting for incoming connections. The client locates the server via its IP address, resolved through DNS.

**IP Addresses & DNS** -- Every publicly deployed server has a unique IP address. DNS (Domain Name System) maps human-readable domain names to IP addresses. When you type a URL, your browser queries a DNS server for the corresponding IP, then connects to that address. IPv4 uses 32-bit addresses (~4 billion), IPv6 uses 128-bit for vastly more. DNS records include A records (domain -> IPv4) and AAAA records (domain -> IPv6). DNS is overseen by ICANN; registrars like Namecheap sell domain names. DNS mappings are cached at browser, OS, ISP, and replicated DNS servers globally. Updating DNS records can take hours or even days because of global replication. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] covers DNS caching at multiple stages and geo-replication in detail.

**HTTP/HTTPS** -- HTTP is the request-response protocol for web communication. Requests include headers (metadata, cookies) and optionally a body (form data). Responses carry status codes: 2xx success, 3xx redirect, 4xx client error, 5xx server error. Common methods: GET (read), POST (create), PUT/PATCH (update), DELETE (remove). HTTP sends data in plain text; HTTPS encrypts it via SSL/TLS. HTTP is stateless: each request is independent, containing all necessary information.

**TCP & UDP** -- TCP (transport layer) ensures reliable, ordered delivery via sequence numbers and a three-way handshake. Each packet has a TCP header with port numbers and control flags. UDP is faster but unreliable: no connection setup, no delivery guarantee. UDP is preferred for time-sensitive applications (video calls, live streaming) where speed matters more than occasional data loss.

**Data Packets** -- When computers communicate over a network, they exchange packets. Each packet contains an IP header (sender/receiver addresses) and application-layer data formatted per the protocol (HTTP, etc.). The Internet Protocol governs how packets are sent and received.

**WebSockets** -- Enable persistent, bidirectional communication between client and server over a single connection. The client initiates a WebSocket handshake, and once established, either side can send messages at any time. Eliminates the need for polling. Used for chat apps, live dashboards, multiplayer games, stock tickers. [[Problems/Uber/Uber|Uber]] uses WebSockets for real-time ride tracking. For scaling WebSocket connections across multiple service instances, combine with Redis Pub/Sub: publishers (e.g., Location Service) write to a channel, and whichever Tracking Service instance holds the rider's WebSocket receives the message and forwards it.

**Server-Sent Events (SSE)** -- A persistent unidirectional connection (server -> client only). Lighter than WebSockets when you only need the server to push updates to the client. Used for real-time seat maps, live feeds, notifications. [[Problems/Ticketmaster/Ticketmaster|Ticketmaster]] uses SSE for real-time seat availability updates. Choose SSE over WebSockets when communication is strictly one-way (server to client).

**Long Polling** -- The client sends an HTTP request that the server holds open (30-60 seconds) until it has data to return. The client immediately re-sends. Simplest real-time approach, requires no extra infrastructure. Best when users are on the page briefly (1-5 minutes).

**Webhooks** -- Allow a server to notify another server when an event occurs via HTTP POST. The receiver registers a callback URL with the provider. When the event fires, the provider sends data to that URL. Eliminates polling between servers. Example: Stripe sends a webhook to your booking service when a payment succeeds.

**Proxy Servers** -- Act as intermediaries between clients and servers. A **forward proxy** sits in front of clients, hiding their IP and controlling outbound access (use cases: internet monitoring in organizations, caching, anonymizing web access). A **reverse proxy** sits in front of servers, handling load balancing, SSL termination, caching, and security. Reverse proxies hide backend server topology from clients. Application servers behind a reverse proxy can be in a private network, disconnected from internet. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] covers forward/reverse proxy types in depth: open, transparent, anonymous, distorting, and high-anonymity (elite) proxies.

**Firewalls & Ports** -- Firewalls monitor and control network traffic. Ports identify specific processes on a device; combined with an IP address, they create a unique network service identifier. Reserved ports: 80 (HTTP), 443 (HTTPS), 22 (SSH).

## APIs & Protocols

**REST API** -- The most widely used API style. Stateless (each request is self-contained), resource-oriented (users, orders, products), uses standard HTTP methods. Simple, scalable, easy to cache. Downsides: can overfetch or underfetch data, may need multiple requests for related resources. Uses JSON for data exchange.

**GraphQL** -- Introduced by Facebook in 2015. Clients request exactly the fields they need in a single query, avoiding overfetch/underfetch. Strongly typed. All requests are POST. Returns HTTP 200 even for errors (details in response body). Trade-offs: more server-side processing, harder to cache than REST.

**gRPC** -- Google's RPC framework built on HTTP/2. Uses Protocol Buffers for serialization (efficient but less human-readable than JSON). Supports multiplexing and server push. Excellent for microservice-to-microservice communication where bandwidth efficiency matters. Requires HTTP/2 support.

**RPC (Remote Procedure Call)** -- A protocol allowing a program to execute code on a remote machine as if it were local. Abstracts network communication details. Many application-layer protocols use RPC internally (HTTP requests can trigger backend RPC calls, SMTP servers use RPC for database interaction).

**API Gateway** -- A centralized entry point for all client requests in a microservices architecture. Handles routing to the correct service, authentication, rate limiting, logging, and monitoring. Examples: AWS API Gateway (managed, auto-scaling). Simplifies client interaction since they hit one endpoint instead of multiple services.

**API Best Practices** -- Design endpoints reflecting resource relationships (`/users/:userId/orders`). Use pagination (limit/offset or cursor-based). GET requests must be idempotent and never mutate data. Maintain backward compatibility with versioning (`/v2/products`). Set rate limits to prevent DDoS. Configure CORS to control which domains can access your API. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] emphasizes: always start with RDBMS-based schema in interviews (jumping to NoSQL is a red flag), and never name a technology (Redis, Elasticsearch) without explaining the architectural decisions behind it.

**Cursor-Based Pagination** -- For feeds with rapidly changing data, use cursor-based pagination instead of offset-based. With offset, new items inserted at the top shift all offsets, causing users to see duplicate or skipped items. Cursor pagination uses a stable reference point (e.g., a post ID or timestamp) so the next page always starts right after the last item seen, regardless of insertions. [[Problems/Twitter Feed/Twitter Feed|Twitter Feed]] uses cursor-based pagination for the home feed.

**Email Protocols** -- SMTP for sending email between servers. IMAP for retrieving email while keeping it on the server (multi-device access). POP3 for downloading email to a single local client.

**WebRTC** -- Enables browser-to-browser communication (voice, video, file sharing) without plugins. Essential for video conferencing and live streaming.

**MQTT & AMQP** -- MQTT is lightweight, ideal for IoT devices with limited processing power and low bandwidth. AMQP provides robust, secure message-oriented middleware for enterprise systems (used by RabbitMQ).

## Data Storage

**SQL Databases** -- Store data in tables with strict schemas and relationships (foreign keys). Follow ACID properties: Atomicity (all-or-nothing transactions), Consistency (valid state after each transaction), Isolation (concurrent transactions don't interfere), Durability (committed data persists). Ideal for structured data requiring strong consistency: banking, financial systems, booking platforms. Examples: PostgreSQL, MySQL, SQLite.

**NoSQL Databases** -- Flexible, schema-less databases optimized for scalability and performance. Types: key-value (Redis), document (MongoDB), graph (Neo4j), wide-column (Cassandra). Trade off strict consistency for horizontal scalability. Good for unstructured data, rapid iteration, simple queries. Many modern NoSQL databases now support ACID (e.g., DynamoDB transactions). The SQL vs NoSQL debate is less relevant than identifying the specific database qualities you need. [[System Design Interview - Design Ticketmaster w a Ex-Meta Staff Engineer|Ticketmaster interview]] notes that senior candidates recognize this and focus on required qualities rather than the debate itself.

**In-Memory Databases** -- Store data entirely in RAM for sub-millisecond access. Examples: Redis, Memcache. Used for caching, session storage, distributed locks, sorted sets (priority queues), geospatial indexes. Volatile: data lost on restart unless persistence is configured. Redis is single-threaded but event-driven, capable of serving ~1M QPS from a single instance. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] notes that Redis' performance comes from event-driven architecture and context switching, not multi-threading.

**Blob Storage** -- For storing large, unstructured files (images, videos, PDFs). Services like Amazon S3 store blobs in buckets, each file getting a unique URL. Scalable, pay-as-you-go, automatic replication. Common use case: streaming audio/video to applications. Profile pictures and media should store URIs pointing to S3/CDN, not binary data in the database. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] demonstrates this in the LinkedIn schema design.

**Relational Schema Design** -- [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] teaches a methodology: list all features, identify entities and relationships, underline nouns (entities/attributes) and verbs (relationships/status changes). Key patterns: one-to-many (add foreign key in dependent entity), many-to-many (create mapping table), and knowing when to split entities even if they share attributes (education vs company tables, for extensibility). Storing lists as columns (e.g., skills as comma-separated) doesn't scale because lookups become full table scans.

**Time-Series / Analytics Databases** -- Column-oriented databases like ClickHouse or TimescaleDB are optimized for append-only, time-series data queried with aggregations (clicks per day, top referrers). Partition by date, drop old partitions for retention management. [[Problems/URL Shortener/URL Shortener|URL Shortener]] uses ClickHouse for click analytics: each redirect pushes a click event to a message queue, consumed by an Analytics Service that writes to ClickHouse.

## Data Management & Performance

**Database Indexing** -- An efficient lookup structure that maps column values to row pointers, avoiding full table scans. Like a book's index. Create indexes on frequently queried columns (primary keys, foreign keys, WHERE conditions). Speeds up reads but slows writes (index updates on each write). Only index the most frequently accessed columns.

**Caching** -- Storing frequently accessed data in memory for faster retrieval than disk-based databases. The **cache-aside pattern**: check cache first (hit = instant return), on miss fetch from DB and store in cache. TTL (Time to Live) prevents serving stale data. Caching exists at multiple levels:
- **Browser cache**: stores HTML/CSS/JS locally, controlled by Cache-Control header
- **Server cache**: Redis or Memcache layer before the database
- **Database cache**: caching query results within or alongside the DB
- **CDN cache**: geographically distributed edge caching

[[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] uses the milk tea analogy: department store (hard disk) vs fridge (cache). Cache hit = milk in fridge. Cache miss = trip to store.

**Multi-Layer Caching** -- For ultra-low latency read paths, stack multiple cache layers. [[Problems/URL Shortener/URL Shortener|URL Shortener]] demonstrates three layers: (1) Redis server-side cache for shortCode->longUrl lookups (80-90% hit rate given power-law distribution), (2) CDN edge caching for 30-60s (absorbs viral link spikes before they reach the API Gateway, but trade-off: cached redirects skip analytics), (3) browser caching via 301 redirects (zero server load for repeats, but kills analytics and prevents URL changes). Write-through on creation ensures the first redirect after creation is a cache hit.

**Cache Write Strategies**: Write-around (bypass cache, write to DB directly), write-through (write to both simultaneously, ensures consistency), write-back (write to cache first, DB later, faster but risk of data loss on crash). [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] explains write-through as: every update goes through cache first, only returns success when both cache and DB are updated. Alternative: DB tells cache to invalidate stale entries on update.

**Cache Eviction Policies**: LRU (Least Recently Used), FIFO (First In First Out), LFU (Least Frequently Used). Determine which items to remove when cache is full.

**Denormalization** -- Combining related data into a single table to eliminate joins. Example: a `user_orders` table instead of separate `users` and `orders` tables. Faster reads at the cost of increased storage and more complex writes. Common in read-heavy applications.

**Database Replication** -- Creating copies of the database across multiple servers. One primary handles writes; multiple read replicas handle read queries. Data is copied from primary to replicas to stay in sync. Improves read performance and availability (a replica can become primary if the original fails). Approaches: master-slave (one writer, many readers) and master-master (multiple writers).

**Database Sharding** -- Splitting a database into smaller pieces (shards) distributed across multiple servers. Each shard holds a subset of data based on a sharding key (e.g., user ID, event ID). Reduces load per shard and speeds up queries. Also called horizontal partitioning. Strategies: range-based, directory-based, geographical. Consider shard key carefully: [[System Design Interview - Design Ticketmaster w a Ex-Meta Staff Engineer|Ticketmaster]] discusses event_id vs venue_id as candidates, each with different trade-offs. For key-value access patterns (e.g., URL shortener with random short codes), hash-based sharding distributes uniformly with no hot-shard problem.

**Vertical Partitioning** -- Splitting a table by columns instead of rows. Useful when a table has many columns but queries only need a few. Improves query performance by reducing scanned data.

**Change Data Capture (CDC)** -- A pattern where changes to a primary database are streamed to other systems. Technically: the database's write-ahead log (WAL) is read by a connector (like Debezium), published to a stream (Kafka), consumed by workers that update downstream systems (e.g., Elasticsearch). Used to keep search indexes in sync with the primary database without coupling write logic. [[System Design Interview - Design Ticketmaster w a Ex-Meta Staff Engineer|Ticketmaster]] uses CDC to sync Postgres -> Elasticsearch.

## Scaling & Load Balancing

**Vertical Scaling (Scale Up)** -- Upgrading a single machine: more CPU, RAM, storage. Quick fix but limited: machines have max capacity, cost grows exponentially, single point of failure. Not a long-term solution for high traffic. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] illustrates this with the Delicious.com story: founder kept buying better hardware until even the best wasn't enough.

**Horizontal Scaling (Scale Out)** -- Adding more machines to distribute workload. More capacity, better fault tolerance (one server down, others take over). Introduces the challenge of request routing, solved by load balancers. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]]: Delicious founder's friends offered their laptops, distributing incoming requests across multiple computers.

**Load Balancing** -- Distributes incoming requests across multiple servers. Sits between clients and backend servers. If a server fails, the load balancer redirects traffic to healthy ones. Load balancers maintain a registry of all available servers with health status. Algorithms:
- **Round Robin**: sequential rotation, simple, works for uniform servers
- **Weighted Round Robin**: servers assigned weights by capacity, more powerful servers get proportionally more requests
- **Least Connections**: routes to server with fewest active connections, good for variable-length tasks
- **Weighted Least Connections**: combines least connections with capacity weights
- **Least Response Time**: combines fewest connections with lowest latency
- **IP Hashing**: consistent routing based on client IP, ensures session persistence
- **Geographical**: routes to closest server, reduces latency
- **Consistent Hashing**: uses a hash ring, ensures minimal redistribution when servers are added/removed

**Load Balancer Types**: Hardware (F5 BIG-IP, Citrix), Software (HAProxy, Nginx), Cloud (AWS ELB, Azure LB, GCP LB). Load balancers are single points of failure; mitigate with redundant pairs (failover), monitoring, autoscaling, and DNS failover. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] covers Layer 4 (transport, routes by IP/port, faster, more secure) vs Layer 7 (application, routes by headers/path/method, richer but slower) load balancers. Also: load balancers provide security by keeping application servers in a private network, and handle SSL/TLS termination.

**CDN (Content Delivery Network)** -- A global network of edge servers caching content close to users. Serves static assets (images, CSS, JS, video) from the nearest server, reducing latency. Pull-based CDN fetches on first request (good for regularly updated content). Push-based CDN requires manual upload (good for large, infrequently updated files). CDNs can also cache API responses for short periods (30s-1min), extremely effective for popular queries. Benefits: reduced latency, high availability, DDoS protection. CDN caching breaks down with highly personalized content or high query permutation counts.

## Distributed Systems

**CAP Theorem** -- In a distributed system, when a network partition occurs, you must choose between Consistency and Availability. Partition tolerance is mandatory (network failures are inevitable). **CP systems** refuse requests they can't guarantee are correct (banking, airline reservations, ticket booking). **AP systems** always respond, possibly with stale data (social media feeds, live viewer counts, chat apps). The trade-off only kicks in during partitions; when healthy, you get both. The decision comes down to: what's the worse user consequence, wrong data or no service? [[CAP Theorem]] has detailed examples and decision framework. Important nuance: different parts of a system can make different CAP choices. [[System Design Interview - Design Ticketmaster w a Ex-Meta Staff Engineer|Ticketmaster]] uses strong consistency for booking but high availability for search/viewing. [[Problems/Uber/Uber|Uber]] uses strong consistency for ride matching (one ride, one driver) but eventual consistency for location updates. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] teaches CAP through the "reminder service" analogy: husband and wife with diaries, illustrating consistency problems, availability problems, and the forced choice during network partitions.

**PACELC Theorem** -- Extension of CAP: when there IS a partition, choose between Availability and Consistency. **Else** (no partition), choose between **Latency and Consistency**. Want consistency? Must wait for all nodes to sync (higher latency). Want low latency? Accept potentially stale data. CAP doesn't address latency, PACELC does. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]]

**Eventual Consistency** -- Most AP systems eventually converge to the same state. When communication resumes between nodes, they exchange data and sync. There may be temporary inconsistency, but data converges over time. Good enough for social feeds, search suggestions, and viewer counts.

**Consistent Hashing** -- A distribution scheme where adding/removing servers only relocates a minimal number of keys. Visualize a ring marked 0 to a large number. Servers and keys are hashed onto this ring. A key is assigned to the nearest server clockwise. **Virtual nodes** solve uneven distribution: each server gets multiple labels on the ring. More powerful servers get more labels, thus more keys. When a server is removed, only its keys redistribute to neighbors; all other keys stay put. Used in Kafka, Cassandra, and for sticky sessions in load balancers. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] covers this extensively including the math puzzle of data movement when changing server count.

**Distributed Locks** -- A mechanism for coordinating access to a shared resource across multiple service instances. Since horizontally scaled services run on many machines, they need a shared, external lock (not in-memory). Redis is commonly used: store a key with a TTL that auto-expires. [[System Design Interview - Design Ticketmaster w a Ex-Meta Staff Engineer|Ticketmaster]] uses a Redis lock (`ticket_id -> true, TTL: 10min`) for reservation expiry: no cron jobs, no reserved timestamps, the key simply disappears after 10 minutes. [[Problems/Uber/Uber|Uber]] uses Redis lock with `NX` flag (`SET lock:ride:{rideId} driver_id NX EX 30`) for ride matching: `NX` means "only set if key doesn't exist," so the first driver to accept wins and all subsequent attempts fail atomically.

**Idempotency** -- Ensuring that repeated identical requests produce the same result as a single request. Critical in distributed systems where retries are common (network failures, user refreshes). Implementation: assign each request a unique ID, check if already processed before executing. Prevents double-charges, duplicate orders, etc. [[Problems/Twitter Feed/Twitter Feed|Twitter Feed]] uses a unique constraint on `(postId, userId)` in the Like table to enforce idempotent likes at the database level.

**Stateless vs Stateful Systems** -- **Stateless**: every server equally equipped to handle any request, no context stored. Easy to scale, resilient to failures, but state must be stored externally (DB), adding network IO latency. **Stateful**: context lives in the application server. Lower latency (no network IO), but not resilient to failures and harder to scale (must transfer state). Use stateful for short-lived state where latency is critical (e.g., PUBG match state: player locations, health, weapons). Destroy state after match ends. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] covers this in detail with the calculator (stateless) vs chatbot (stateful) examples, and the PUBG match_ID routing problem.

**Availability, SLOs, and SLAs** -- Availability is measured as uptime percentage. "Five nines" (99.999%) means ~5 minutes of downtime per year vs. 99.9% allowing ~8.76 hours. SLOs (Service Level Objectives) are internal performance goals (e.g., respond within 300ms 99.9% of the time). SLAs (Service Level Agreements) are formal contracts with customers, with penalties for breaches. Resilience is built through redundancy, graceful degradation, fault tolerance.

**Throughput & Latency** -- Throughput measures volume over time: RPS (server), QPS (database), bytes/second (network). Latency measures time for a single request round-trip. Optimizing for one often sacrifices the other (batching increases throughput but adds latency).

## Architecture Patterns

**Microservices** -- Breaking a monolithic application into smaller, independent services, each handling a single responsibility with its own database and logic. Services communicate via APIs or message queues. Each can scale and deploy independently. Trade-off: operational complexity increases (networking, monitoring, distributed debugging).

**Message Queues** -- Enable asynchronous communication between services. A producer places a message in the queue; a consumer retrieves and processes it. Decouples services, prevents overload, improves scalability. The consumer processes at its own pace regardless of producer throughput. [[Problems/Twitter Feed/Twitter Feed|Twitter Feed]] uses Kafka for fan-out: when a user posts, a message is queued and consumed by a Fan-Out Service that writes to all followers' feed caches. [[Problems/Uber/Uber|Uber]] uses a ride request queue partitioned by geographic region to prevent head-of-line blocking (a hard-to-match ride in a remote area doesn't block easy matches in Manhattan). Bonus: if a consumer crashes mid-processing, the unacknowledged message returns to the queue for another instance. Built-in fault tolerance.

**Rate Limiting** -- Restricting the number of requests a client can make within a time frame. Prevents abuse, DDoS attacks, and resource exhaustion. Algorithms: fixed window, sliding window, token bucket. Typically handled at the API Gateway level rather than in application code.

**Fan-Out Pattern** -- Pre-computing results and distributing them to consumers ahead of time. Two fundamental approaches:

**Fan-Out On Write (Push Model)**: When a user posts, inject the post into all followers' pre-computed feed caches immediately. Feed reads become a simple cache lookup. Pros: blazing fast reads, decoupled from social graph complexity. Cons: write amplification (one post from a user with 10M followers = 10M writes). Best for: the vast majority of users with < 10K followers.

**Fan-Out On Read (Pull Model)**: Generate the feed at read time by querying all followees' posts. Pros: simple, always fresh, no extra storage. Cons: slow at read time (scales linearly with followee count), doesn't work at massive scale.

**Hybrid Approach (Staff Answer)**: Use fan-out on write for normal users, fan-out on read for celebrities (> ~10K followers). At read time, merge the pre-computed feed with real-time celebrity post queries. This is what Twitter actually does. Additional optimization: don't pre-compute feeds for inactive users. [[Problems/Twitter Feed/Twitter Feed|Twitter Feed]] and [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] both cover this pattern in detail.

**Two-Phase Booking** -- A pattern where a transaction is split into reserve and confirm steps. The user first reserves a resource (seat, item), gets a time window to complete payment. If the window expires, the reservation releases automatically. [[Problems/Ticketmaster/Ticketmaster|Ticketmaster]] implements this with two endpoints: `POST /booking/reserve` (creates Redis lock with TTL) and `PUT /booking/confirm` (processes payment via Stripe webhook, updates DB to booked). Security note: never put userId in the request body; use JWT/session token in headers.

**Virtual Waiting Queue** -- A pattern for handling massive traffic surges (Taylor Swift tickets, Super Bowl). Instead of letting all users hit the system simultaneously, route them into a queue (Redis sorted set, priority by arrival time or random for fairness). Batch-release users as capacity opens up. Admin-enabled per event. Notify users via SSE when it's their turn. Simple but elegant: protects backend services while improving UX. [[Problems/Ticketmaster/Ticketmaster|Ticketmaster]]

**Async Counter Aggregation** -- A pattern for handling extreme write contention on a single row (e.g., like count on a viral post receiving 100K likes/minute). Instead of updating the Post row on every like, use Redis `INCR` on a counter key (`likes:{postId}`) which is atomic and handles 100K+ ops/sec. A background worker periodically flushes the Redis counter to the database (every 5-10s). The displayed count reads from Redis (real-time), while the DB value is slightly behind (eventual consistency, fine for AP). Reconcile with the Like table's actual count during flush. [[Problems/Twitter Feed/Twitter Feed|Twitter Feed]]

**Trie (Prefix Tree)** -- A tree data structure for efficient prefix-based lookups. Each node represents a character, terminal nodes mark complete words and store frequency counts. Used for search autocomplete/type-ahead. Attach a **min-heap of size K** to every node to store the top K most popular completions, enabling O(1) query time. Reduce write contention by batching frequency updates in a hash map (only flush to trie when threshold reached) or by **sampling** (process every 100th request; for popular queries, random sampling captures them with 99%+ probability). Shard tries by prefix using consistent hashing. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] covers this in the Google Search Type-Ahead mock interview.

**Inverted Index / Search** -- Text is tokenized into terms, and an inverted index maps each term to the documents containing it. Used by Elasticsearch and Twitter's Early Bird (built on Lucene). Supports geospatial queries (quadtrees + geohashing). Should NOT be used as a primary data store. Keep in sync with primary DB via CDC or application-level dual writes. Twitter uses **scatter and gather**: search query distributed across global data center shards, results merged and re-ranked.

**Elasticsearch & Search Optimization** -- A search-optimized database using inverted indexes. AWS OpenSearch (managed Elasticsearch) supports node query caching (LRU cache of top 10K queries per shard). [[Problems/Ticketmaster/Ticketmaster|Ticketmaster]] uses CDC to sync Postgres -> Elasticsearch for event search.

**Stripe Integration Pattern** -- Offload payment processing to Stripe. Post payment details via Stripe's client libraries. Stripe processes asynchronously and calls back via webhook when payment succeeds or fails. Your service exposes a webhook endpoint to receive the callback and update the order/ticket status accordingly.

**Redis Pub/Sub for Real-Time Tracking** -- Redis Pub/Sub decouples real-time event publishers from subscribers. [[Problems/Uber/Uber|Uber]] uses this for ride tracking: the Location Service publishes driver GPS updates to a `ride:{rideId}` channel, and the Tracking Service instance holding the rider's WebSocket subscribes and forwards updates. It doesn't matter which Tracking Service instance the rider connects to; Redis routes the message. When the ride completes, close the WebSocket and unsubscribe.

**Feed Cache Design** -- For social feeds at scale, use Redis sorted sets as the backbone. One sorted set per user (`feed:{userId}`), score = timestamp, member = postId. `ZREVRANGE` for newest-first pagination. Cache only postIds (not full posts), then "hydrate" by looking up a separate post cache (`post:{postId}` -> full JSON). Sizing example from [[Problems/Twitter Feed/Twitter Feed|Twitter Feed]]: 200M active users x 800 entries x 40 bytes/entry = ~6.4 TB, fits in a Redis cluster. When a feed cache is cold (user inactive for months), fall back to fan-out on read for that user, rebuild the cache asynchronously in the background.

## Geospatial Systems

**Geospatial Indexing** -- Standard B-tree indexes are optimized for one-dimensional data and perform poorly on two-dimensional lat/lng queries. Geospatial indexes solve this. Two main approaches:

**Quad Trees**: Recursively split a map into 4 regions. Each region is a tree node. A threshold K determines when to split further (if a region has more than K entities, split again). Good for **uneven density** (dense NYC, empty Atlantic Ocean). Bad for high-frequency writes because adding/removing entities requires re-indexing the tree. PostGIS (Postgres extension) supports quad trees. [[Design Uber w a Ex-Meta Staff Engineer - System Design Interview breakdown|Uber interview]]

**Geohashing**: Recursively split the map into 4 regions (like quad trees) but density-independent: split until reaching desired precision. Results in a base-32 encoded string; longer string = more precise. Easy to calculate, easy to store (just a string), no re-indexing on writes. Redis supports geohashing natively via `GEOADD` and `GEOSEARCH` commands. Less good for uneven distribution but excellent for high-frequency writes. [[Design Uber w a Ex-Meta Staff Engineer - System Design Interview breakdown|Uber interview]]

**Decision framework**: Quad tree for read-heavy with uneven density (Yelp, Google Maps POIs). Geohash for write-heavy with frequent updates (Uber driver locations, 600K updates/sec). Uber actually uses H3 (hexagonal grid system) in production, which solves the issue that distance from center-to-corner of a square differs from center-to-edge, but knowing quad trees + geohashing is sufficient for interviews.

**Redis Geospatial for Location Tracking** -- [[Problems/Uber/Uber|Uber]] uses Redis `GEOADD drivers:{city} lng lat driver_id` for writes and `GEOSEARCH drivers:{city} FROMLONLAT lng lat BYRADIUS 3 km ASC COUNT 20` for proximity queries. O(log N) for both. Partition by city/region for smaller working sets and regional data center placement. Ephemeral data: if Redis crashes, drivers resend location within 5 seconds, so zero practical data loss. **Adaptive updates**: reduce the 600K TPS by having the driver client send updates conditionally (not accepting rides? don't update. Parked for 20 minutes? reduce frequency. In remote area? lower precision). Can cut TPS from 600K to 100K or less.

## URL Shortening

**URL Shortening** -- [[Problems/URL Shortener/URL Shortener|URL Shortener]]: use base-62 encoding (a-z, A-Z, 0-9) for short codes. 62^7 gives ~3.5 trillion unique URLs, enough for centuries. Pre-generate keys via a **Key Generation Service (KGS)** to avoid collision: a background process creates millions of random 7-char keys stored with `used = false`. Each URL Service instance pre-fetches a batch (e.g., 1,000 keys) into memory; if it crashes, those ~1,000 keys are lost (negligible out of trillions). Use 302 redirects (not 301) to preserve analytics: 301 tells the browser to cache the redirect permanently, so repeat clicks never hit the server. Cache shortCode->longUrl in Redis for ultra-low latency reads. Push click events to message queue for async analytics processing in ClickHouse. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] adds: don't use auto-increment IDs (guessable), don't use UUID/MD5 (too long, collision-prone as pool depletes).

## Computer Architecture Basics

**Storage Hierarchy** -- Disk (HDD/SSD, non-volatile, TB-scale, slowest), RAM (volatile, GB-scale, ~5000 MB/s), Cache (L1/L2/L3, MB-scale, nanosecond access), CPU (fetches/decodes/executes instructions from compiled machine code). The CPU checks L1 -> L2 -> L3 -> RAM in order. Motherboard connects all components.

**Production App Architecture** -- CI/CD pipelines (Jenkins, GitHub Actions) automate deployment. Load balancers/reverse proxies (Nginx) distribute traffic. External storage servers hold data. Logging/monitoring systems (PM2 backend, Sentry frontend) track issues on external services. Alerting integrates with Slack for instant developer notification. Debugging follows: identify -> replicate in staging -> debug -> hotfix.

## System Design Interview Framework

**5-Step Roadmap**: Requirements -> Core Entities -> APIs -> High-Level Design -> Deep Dives. The first 3 steps take ~15 minutes. High-level design satisfies functional requirements. Deep dives satisfy non-functional requirements. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]] presents a similar 5-step framework: Gather Requirements -> Estimate Scale -> Design Goals -> Design for Single Server -> Scale for Numbers.

**Functional Requirements** -- Features of the system ("users should be able to..."). Walk backwards through the user flow to derive them. Keep to 3-5 core features.

**Non-Functional Requirements** -- What makes the system unique and challenging. Don't just list "-ilities." Identify the CAP trade-off, read/write ratio, scaling concerns specific to this system. Note out-of-scope items below the line and check in with the interviewer.

**Scale Estimation** -- Start with daily active users, derive storage needs and TPS. [[System Design Full Course - Software Architecture - Caching - CAP Theorem @SCALER|SCALER course]]: for URL shortener with 1M users, 10% writers, 1KB per record = ~100MB/day, ~36GB/year. If data fits in one box, no sharding needed. If TPS is too high for one server, need caching/replication.

**Core Entities** -- The data persisted and exchanged. List them early but don't detail fields until the high-level design evolves them naturally.

**APIs** -- User-facing REST endpoints, one per functional requirement. Use the core entities as inputs/outputs. Use cursor-based pagination for feeds with rapidly changing data (not offset-based).

**Database Choice** -- Focus on required qualities (ACID, scalability, query patterns) rather than the SQL vs NoSQL debate. Pick what you know and justify briefly. Always start with RDBMS in interviews.

**Back-of-Envelope Math** -- Only do calculations when the result directly influences a design decision ("Do I need to shard?" "Does this fit in one Postgres instance?" "Can Postgres handle 600K TPS?"). Math without purpose is wasted time. [[Design Uber w a Ex-Meta Staff Engineer - System Design Interview breakdown|Uber interview]]: tell the interviewer upfront that you'll do estimations during the design when results directly influence decisions, not as a checkbox exercise. 99.9% of interviewers say yes.

**Level Expectations**: Mid-level candidates pass with a solid high-level design and a basic solution (cron job for reservation expiry). Senior candidates need optimized solutions (Redis lock, Elasticsearch, one solid deep dive). Staff/principal need all of the above plus creative solutions (virtual waiting queue, SSE, nuanced trade-off analysis).

**Interview Red Flags**: Jumping directly to NoSQL without justification. Naming technologies (Redis, Elasticsearch) without explaining architectural decisions. Not asking clarifying questions. Spending too long on scale estimation.
