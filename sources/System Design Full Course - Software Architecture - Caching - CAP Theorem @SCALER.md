Source: [YouTube](https://www.youtube.com/watch?v=Xx1eYBlUGO8)
Transcribed: 2026-04-07

---

Topics covered: software architecture design, relational data modeling, horizontal vs vertical scaling, load balancing, stateless vs stateful systems, consistent hashing, caching, CAP theorem, interview questions, and a mock interview.

## Software Architecture Design: Twitter Example

### Gathering Requirements

The first part of any software architecture plan is to gather the requirements. What features should your product support? Understand this from different perspectives: customer pain points, wants and needs, technical feasibility.

Consider both **functional and non-functional requirements**:
- **Functional** (critical for product success): user should be able to create a profile, follow other profiles, tweet, scroll through timelines, like a tweet
- **Non-functional** (affects UX but not features): performance, reliability, uptime

Requirements are powerful: once noted down properly, a lot of technical options will be decided for you.

### High-Level to Low-Level Design

When moving from requirements to planning, think of the system as individual layers. Think of your product as a cake: each piece is a different feature, each layer is a different component interacting in the backend. Most features will have all layers (components) interacting with each other.

Two major components in software architecture design:
1. **Database design**
2. **Backend interactions** (how information flows between servers)

### Database Design for Twitter

From requirements, we need a relational SQL database because there is a relation between users and tweets.

- **Users table**: stores user information
- **Tweets table**: separate table, related via user ID as foreign key
- **Followers table**: each column belongs to a unique directional relationship between profiles

Relationships:
- **One to many**: users to tweets (one user, multiple tweets)
- **Many to many**: users to followers (one user follows many, many follow one)

### Serving Flows and Twitter Characteristics

Twitter has 300 million daily active users, 6,000 tweets per second, and 600,000 queries to fetch timelines. Key discovery: **Twitter is a read-heavy system**. Eventual consistency is fine. Space is not a huge constraint (tweets are character-limited).

Since brute force fetch operations are inefficient on databases, we use a **Redis cluster** for faster reads with horizontal scaling. Store both user and tweet info in Redis cache and database for backup.

### User Timeline Flow

1. Get user ID from users table
2. Query tweets table for that user ID
3. Return tweets sorted in chronological order
4. Use caching layer in Redis cluster instead of querying database directly

### Home Timeline Flow

**Initial approach**: Find all followed profiles, fetch all tweets, merge, sort, return. This becomes very inefficient as tweets database grows to millions of rows.

**Fan-out approach**: Move from single data source to multiple data sources, one per user. Each user gets an in-memory home timeline containing tweets from all followed profiles. When someone tweets, it gets injected into all followers' home timelines.

**Problem**: Users with millions of followers can't have their tweets injected into all follower timelines at runtime.

**Solution: Synchronized calls + fan-out**:
- Home timeline only contains tweets from profiles without large follower counts (pre-computed)
- Followers table stores a list of followed profiles with large follower counts
- At runtime, send synchronous calls to large-follower profiles, fetch their tweets, merge with pre-computed home timeline

**Additional optimizations**: Don't pre-compute home timelines for profiles that haven't been active lately.

### Search Engine

Twitter uses **Early Bird**, a real-time inverted index based on Lucene. When a tweet is posted, it does inverted full-text indexing: the tweet is broken into bits, words, and tags, each indexed into a distributed table with references to all tweets containing that word.

**Scatter and Gather**: Search query is distributed across data centers globally. Each Early Bird shard is queried, results are merged, re-ranked, sorted, and returned based on popularity.

### Software Architecture Design Tips

- Use diagrams to visualize concepts
- Don't try to fit design to a pattern on first attempt, focus on high-level design
- First design is just an iteration
- Avoid scope creep, align requirements with stakeholders
- Software architecture is more effective with stakeholder input and proper mapping of requirements to design

## Relational Data Modeling: LinkedIn Example

### Schema Design Methodology

To design any relational data store schema:
1. List down all features
2. Identify all entities and relationships
3. Underline all nouns and verbs: nouns become entities or attributes, verbs translate to status changes or relationships

### User Profile Entity

User profile has: ID, profile pic (stored as URI pointing to S3/CDN, not in database directly), name, email/phone.

### Skills: Many-to-Many Relationship

**Bad approach**: Adding skills as a list in user profile table leads to scan operations (SELECT * WHERE skills LIKE '%Java%'). Doesn't scale and can't auto-suggest.

**Correct approach**: Create separate **Skills** entity and **User Skills** mapping table (ID, user_id, skill_id). This models the many-to-many relationship properly.

### Education and Company

Initially could combine into single Organization entity with a type field, but this breaks when you want type-specific attributes (CGPA for education, salary for company). Don't enforce application logic in your database.

**Solution**: Split into separate **Education** and **Company** tables. Create mapping tables: **User Education** (ID, user_id, institution_id) and **User Company** (ID, user_id, company_id). Both are many-to-many relationships.

### Recommendations

Create a **Recommendation** entity with: ID, user_id (giver), recipient_id. No mapping table needed because one recommendation has exactly one giver and one recipient (one-to-many relationship).

### Connections and Followers

**Connection table**: ID, user_id_1, user_id_2. When A sends request to B, A becomes a follower of B. When B accepts, add another row. To optimize space, use a **Boolean is_accepted** column instead of two rows.

- If accepted = true: query where user_id_1 = A OR user_id_2 = A
- If accepted = false: only user_id_2 = A (followers only)

### Posts, Comments, and Likes

- **Post**: ID, user_id, text (one-to-many with user)
- **Comment**: ID, user_id, post_id, text (dependent on both user and post)
- **Likes**: Instead of separate post_like and comment_like tables, combine into single **Like** table with: ID, entity_id, entity_type (post/comment/blog), user_id. Extensible without adding new tables.

## Vertical Scaling vs Horizontal Scaling: Delicious Example

### Background

Delicious was a bookmarking website started in 2003, acquired by Yahoo in 2005, grew to 5 million users and 180 million bookmarks by 2008.

### How It Started

When you type a URL, DNS returns the IP address. Need a static IP that doesn't change. Two types of requests: GET (read bookmarks) and POST (write bookmarks). Both go to the same computer running an application server (HTTP port 80) and MySQL server.

### Vertical Scaling

As user base grew, the creator bought better hardware: more RAM, hard disk, multiple cores. This is **vertical scaling**: upgrading a single machine. Limitations:
- Restrained by system resources
- Lose customer data if laptop crashes
- Website unreachable when computer is off (single point of failure)

### Horizontal Scaling

Instead of upgrading one machine, use multiple servers. Uniformly distribute incoming requests across available computers.

**Problem**: DNS points to one IP, but website runs on multiple servers. If you choose any random server for DNS, all requests go to that one server.

**Solution**: Have a special machine (load balancer) that routes traffic to available instances. DNS points to this special machine's IP. The load balancer only routes traffic, doesn't do compute/memory intensive tasks, so it can handle up to 1 million requests per second.

**Handling load balancer failure**: Have a standby routing server. When main server goes down, assign the static IP to the standby server (IP swap is instant, unlike DNS changes which take minutes).

## Load Balancing

### Request Flow

Client → DNS resolution → IP address → Load Balancer → Application Server

DNS resolution latency should be extremely low. DNS mappings are cached at: browser, OS, ISPs, and replicated DNS servers. DNS is replicated across the globe (updating DNS takes hours or days).

### DNS-Level Load Balancing

For Google/Facebook scale, DNS returns a list of IPs in shuffled order. Clients connect to the first IP (waterfall model). Different clients get different IP orderings, distributing load.

**Geo-based routing**: People in India get IP addresses for Indian data centers, reducing latency.

### Benefits of Gateway/Load Balancer

- Can add more instances without DNS changes
- Security layer: application servers can be in private network
- SSL/TLS termination at load balancer level

### Types of Load Balancers

**Hardware load balancers**: Specialized hardware for routing.

**Software load balancers** (more common):
- **Layer 4 (Transport)**: Routes based on source IP and port only. Faster, more secure (minimal info exposed). Doesn't process full request.
- **Layer 7 (Application)**: Routes based on headers, query params, path params, HTTP method. Richer routing but slower (waits for all packets). Modern hardware reduces this gap.

### Routing Strategies

- **Round Robin**: Sequential rotation. Simple but doesn't account for server capacity differences.
- **Weighted Round Robin**: Servers assigned weights based on capacity. More powerful servers get proportionally more requests.
- **Least Connections**: Routes to server with fewest active connections.
- **Weighted Least Connections**: Combines least connections with capacity weights.
- **Least Response Time**: Routes based on both active connections and average response time.
- **Hash-based**: Uses source IP/URL hash for consistent routing. Used in stateful systems (see consistent hashing).

### Health Checking

Load balancers maintain a registry of all available servers with their state. Servers marked as available (green) or unavailable (red). Requests only route to available servers.

## Stateless vs Stateful Systems

### Stateless Systems

Every server is equally well-equipped to answer any query. No context or state is saved. Example: online calculator.

**Pros**:
- Easy to scale (just add/remove servers)
- Resilient to server failures (no data loss)

**Cons**:
- If state is needed, it must be stored externally (database), introducing network IO latency

### Stateful Systems

Context or state lies within the application server. Example: chatbot that remembers conversation history.

**Pros**:
- Lower latency (data is local, no network IO)

**Cons**:
- Not resilient to server failures (data lost when server goes down)
- Harder to scale (must transfer state between servers)

### When to Use Stateful

Use for short-lived state where latency matters. Example: **PUBG** multiplayer game. Player location, health, weapons, team info must be stored in-app server (not database) for real-time performance. This state is transient (destroyed after match ends).

### Load Balancing in Stateful Systems

All requests for the same match must go to the same server. Basic approach: **match_ID mod N** (number of servers).

**Problem**: When adding/removing servers (changing N), majority of keys get redistributed to new servers. Data needs to be transferred, which is not ideal.

## Consistent Hashing

### Problem Statement

Need a distribution scheme that doesn't directly depend on number of servers, minimizing key relocation when adding/removing servers.

### Solution

Visualize a circle (ring) marked 0 to a very large number (e.g., 10^18). Use two hash functions:
- **HS**: marks servers on the ring
- **HC**: marks keys/clients on the ring

To find which server handles a key: locate the key on the ring, move clockwise (or counter-clockwise) to find the nearest server.

### Problems and Solutions

**Uneven distribution**: Server at max distance gets most requests.
**Weighted routing**: Some servers have more resources.

**Solution: Virtual nodes**. Assign many labels to each server (e.g., A0-A9, B0-B9). More powerful servers get more labels, thus more keys. Ensures even distribution.

### Adding/Removing Servers

When server C is removed, only its keys get reassigned to other servers. Keys belonging to A and B remain untouched. Each server still holds approximately 1/N of data.

### Applications

- Distributed databases: Kafka, Cassandra
- Sticky sessions in load balancers
- Stateful server load distribution

## Caching

### The Milk Tea Analogy

Buying milk from department store every time = slow (fetching from hard disk). Buying a fridge to store milk = caching (faster access from temporary storage).

### How Caching Works

Machines query for information. Reading from hard disk is slow. If frequently accessed data is stored in faster memory (RAM or nearby cache), retrieval is much faster.

- **Cache hit**: Data found in cache
- **Cache miss**: Data not in cache, must fetch from original source

### Real-World Example: Browser Caching

First website load is slow. Refresh is faster because browser caches images, CSS, JS. Even when internet is spotty, cached resources load from local memory.

### Cache Consistency: Write-Through Cache

When new data arrives, it goes through the cache first:
1. Check if entry exists in cache
2. Update cache entry
3. Update hard disk/database
4. Only return success when both are updated

Alternative: Database tells cache to invalidate stale entries whenever there's an update (cache invalidation).

## CAP Theorem

### The Reminder Service Analogy

Imagine running a reminder service where people call to store reminders and call back to retrieve them.

**Scaling up**: Get wife to help take calls. Now both sit with diaries.

**Consistency problem**: Mr. X stores reminder with wife, calls back and gets routed to husband who doesn't have the entry. Solution: Both write entries in their diaries, only return success when both have noted it down.

**Availability problem**: Wife calls in sick. Husband can't confirm wife has noted down new entries, so he must reject all new requests. The system becomes unavailable.

**Improved approach**: When wife is absent, husband takes entries. When wife returns, she catches up on all missed entries before taking new calls. System stays available, eventually becomes consistent.

**Network partition**: Husband and wife stop talking (can't communicate). Now he must choose:
- **Stay consistent**: Reject new requests (unavailable)
- **Stay available**: Accept entries but become inconsistent (diaries differ)

### The Theorem

**CAP Theorem**: In a distributed system, you can only guarantee two out of three:
- **C** (Consistency): All nodes have the same data
- **A** (Availability): System always responds to requests
- **P** (Partition Tolerance): System works despite network failures

When a network partition happens, you must choose between Consistency and Availability.

### AP Systems and Eventual Consistency

Most AP (Available + Partition Tolerant) systems become **eventually consistent**. When communication resumes, nodes exchange notes and sync up. There may be temporary inconsistency, but data converges.

### PACELC Theorem

Extension of CAP: When there IS a partition, choose between Availability and Consistency. **Else** (no partition), choose between **Latency and Consistency**.

- Want consistency? Must wait for all nodes to sync before responding (higher latency)
- Want low latency? Accept potentially stale data (lower consistency)

## System Design Interview Framework

### Five-Step Framework

1. **Gather Requirements**: Ask clarifying questions even if problem seems clear. Re-iterate in your own words. Don't spend more than 2-3 minutes.

2. **Estimate Scale**:
   - Start with daily active users
   - Calculate storage requirements (e.g., 1M users × 10% writes × 1KB = ~100MB/day, ~36GB/year)
   - Calculate TPS (throughput per second) for reads and writes
   - These numbers determine if you need sharding, caching, replication

3. **Design Goals**:
   - Choose consistency vs availability (CAP theorem trade-off)
   - Determine latency requirements (real-time vs batch)
   - For URL shortener: eventual consistency is fine, availability is critical, low latency needed for reads

4. **Design for Single Server**:
   - Start with RDBMS schema (don't jump to NoSQL, it's a red flag)
   - Design APIs (e.g., POST /shorten, GET /:shortURL)
   - Write business logic
   - Example: For URL shortener, use base-62 encoding (a-z, A-Z, 0-9 = 62 chars). 62^5 gives millions of unique URLs.
   - Don't use auto-increment IDs (guessable) or UUID/MD5 (too long, collision-prone as pool depletes)
   - Pre-generate codes, store in hash set for randomization, assign batches to servers

5. **Scale for Estimated Numbers**:
   - Add multiple servers, each with pre-assigned code batches
   - Ensure no collisions across servers
   - Validate all requirements are met

### Key Interview Tips

- Always start with RDBMS, then justify if you need NoSQL
- Use short URL as primary key (not auto-increment ID) for locality of reference
- Expiry is important: truncating old data prevents needing multiple shards
- Read-heavy systems need caching/replication
- TPS estimation reveals if one server can handle the load

## Mock Interview: Design Google Search Type-Ahead

### Requirements Scoping

Functional requirements (kept for discussion):
- Sort suggestions by **popularity** (decreasing order)
- Show **top 5** suggestions

Deprioritized: muted word filtering, typo handling, personalization, location-based suggestions.

### Non-Functional Requirements

- Partition tolerance (always needed)
- **Availability over consistency** (eventual consistency is fine: showing slightly outdated top results is acceptable)
- Very low latency (suggestions must appear in milliseconds as user types)

### Scale Estimation

- Google: ~1 billion users, each queries at least once/day
- 1 billion queries/day
- Read and write ratio approximately 1:1
- Storage: not all queries are unique, need to store unique phrases with frequency counts

### Data Structure: Trie

Store all search terms in a **Trie** (prefix tree). Each terminal node stores a Boolean (is_word) and a frequency count.

**Problem with finding top 5**: Must traverse entire subtree from current node to find most popular completions. Very slow.

**Solution**: Attach a **min-heap** of size 5 to every node. Each node's heap stores references to the top 5 most popular terminal nodes in its subtree. Queries answered in O(1) time.

### Reducing Write Operations

**Problem**: Every search click updates frequency at terminal node AND must propagate up through all ancestor nodes (updating their heaps). This blocks reads.

**Solution 1: Hash map batching**. Instead of updating trie on every click, accumulate frequencies in a hash map. Only update the trie when frequency reaches a threshold (e.g., 1000). For billion-scale queries, error margin of 1000 is negligible.

**Solution 2: Sampling**. Only process every 100th request. For truly popular queries, random sampling still captures them with 99%+ probability (law of large numbers). Drastically reduces writes.

### Storage: Sharding the Trie

Entire trie can't fit in one machine. Use **prefix-based sharding**: partition by prefixes (e.g., AB, AC, AD stored on different machines).

Map prefixes to machines using **consistent hashing**. The prefix becomes the shard key. This handles adding/removing servers with minimal data redistribution.

### Replication

If a server holding prefixes AA, AC, AD goes down, data is lost. Solution: **replication**. Store copies of each prefix's trie on multiple servers.

In consistent hashing, the natural replication candidate is the next server clockwise on the ring. If server 2 goes down, requests route to server 3, which already has a copy.

### Client-Side Optimization: Debouncing

Don't send a request on every keystroke. Wait for a pause (e.g., 600ms of no typing) before sending the request. Reduces server load significantly.

### Interview Discussion Points Not Fully Covered

- How to persist a trie to disk (for server restart recovery)
- Rate limiting
- Minimum prefix length for consistent hashing ring
- Personalization as an extensibility test
- When asked about NoSQL/Redis: don't just name a technology, explain the architecture and trade-offs behind it
- Caching for tries: tries are already in-memory, so a separate cache layer doesn't add much value
- Redis can serve ~1M QPS from a single thread due to event-driven architecture
