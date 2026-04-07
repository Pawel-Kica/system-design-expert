## Requirements

### Functional Requirements

- Users should be able to **create a short URL** from a long URL (and optionally provide a custom alias)
- Users should be able to **be redirected** to the original long URL when visiting the short URL
- Users should be able to **view click analytics** for a short URL (total clicks, clicks over time, referrers)

### Non-Functional Requirements

- **High availability for redirects (AP)**: The redirect path is the core product. If the system is down for even a second, every link shared anywhere on the internet is broken. Availability is paramount. Consistency for writes matters too (no two long URLs should map to the same short code), but this is a much lower-volume path.
- **Ultra-low latency redirects**: Users click a short link expecting instant navigation. Every millisecond of redirect latency is noticeable. This is the defining performance characteristic of the system.
- **Read >> Write (100:1 to 1000:1)**: URL creation is relatively rare compared to redirects. A URL might be created once and clicked thousands of times. This heavily skews the optimization toward read performance.
- **Scale to billions of URLs**: Over years, the system accumulates billions of mappings. Must handle sustained high read throughput with burst traffic (viral links can spike from 0 to millions of clicks in minutes).

### Out of Scope

- User authentication / account management
- URL expiration and TTL management
- Custom branded domains
- Spam / phishing detection
- GDPR compliance

---

## Core Entities

- **URL**: shortCode, longUrl, userId, createdAt, expiresAt
- **Key**: key (pre-generated short code), used (boolean)
- **Click**: id, shortCode, timestamp, userAgent, ipAddress, referrer

---

## APIs

### Create Short URL

```
POST /urls
Body: { longUrl, customAlias? }
→ { shortCode, shortUrl }
```

If `customAlias` is provided, check availability first. Otherwise, assign a pre-generated key. Returns the full short URL (e.g., `https://short.ly/abc1234`).

### Redirect

```
GET /{shortCode}
→ 302 Redirect (Location: longUrl)
```

Returns HTTP 302 (temporary redirect). Why 302 and not 301? A 301 (permanent redirect) tells the browser to cache the redirect and never ask the server again. This is great for reducing load, but it completely kills analytics: you never see repeat clicks from the same user. Use 302 to ensure every click hits the server for tracking. If analytics are not needed, 301 is the better choice for performance.

### Get Analytics

```
GET /urls/{shortCode}/stats
→ { totalClicks, clicksByDay[], topReferrers[], topCountries[] }
```

Aggregated analytics. This is a read from the analytics data store, not from the main URL database.

---

## High-Level Design

### Architecture Overview

Microservices architecture with an API Gateway as the single entry point.

**Create flow:**
1. Client sends `POST /urls` to the API Gateway
2. API Gateway routes to the **URL Service**
3. URL Service grabs a pre-generated key from the **Key Generation Service (KGS)**
4. URL Service writes the `shortCode → longUrl` mapping to the **database**
5. Returns the short URL to the client

**Redirect flow:**
1. Client visits `GET /{shortCode}`
2. API Gateway routes to the **URL Service**
3. URL Service checks **Redis cache** first
4. On cache hit: return 302 redirect immediately
5. On cache miss: query the database, populate the cache, return 302
6. Asynchronously push the click event to a **message queue** (Kafka / SQS)

**Analytics flow:**
1. Click events are consumed from the message queue by the **Analytics Service**
2. Analytics Service writes to the **Analytics DB** (ClickHouse / TimescaleDB, optimized for time-series aggregation)
3. `GET /urls/{shortCode}/stats` reads from the Analytics DB

### Database Schema

**URL table** (primary data store):

| Column     | Type      | Notes                    |
| ---------- | --------- | ------------------------ |
| shortCode  | string PK | 7-char base62 code       |
| longUrl    | string    | original URL             |
| userId     | string    | optional, who created it |
| createdAt  | timestamp |                          |
| expiresAt  | timestamp | optional TTL             |

**Key table** (KGS data store):

| Column | Type       | Notes                        |
| ------ | ---------- | ---------------------------- |
| key    | string PK  | pre-generated 7-char base62  |
| used   | boolean    | false = available             |

**Click table** (analytics data store):

| Column    | Type      | Notes                     |
| --------- | --------- | ------------------------- |
| id        | UUID PK   |                           |
| shortCode | string FK | which URL was clicked     |
| timestamp | timestamp | when the click happened   |
| userAgent | string    | browser/device info       |
| ipAddress | string    | for geo lookup            |
| referrer  | string    | where the click came from |

### Database Choice

**Main URL store: DynamoDB or Cassandra.** The access pattern is almost exclusively key-value lookup (`shortCode → longUrl`). No complex joins, no transactions across entities. Needs to scale to billions of records with consistent low-latency reads. NoSQL key-value stores are purpose-built for this. Postgres would work too at moderate scale (with an index on shortCode, lookups are fast), but the simplicity of the access pattern makes NoSQL a natural fit.

**Analytics store: ClickHouse or TimescaleDB.** Click data is append-only, time-series, and queried with aggregations (clicks per day, top referrers). Column-oriented databases like ClickHouse are optimized for exactly this pattern.

---

## Deep Dives

### Deep Dive 1: Key Generation Service (KGS)

**The problem:** How do we generate unique, short, non-colliding codes at massive scale? This is the most interesting design challenge in a URL shortener.

**Approaches compared:**

| Approach                   | How it works                                | Pros                                          | Cons                                      |
| -------------------------- | ------------------------------------------- | --------------------------------------------- | ----------------------------------------- |
| Hash + truncate            | MD5/SHA256 the long URL, take first 7 chars | Simple                                        | Collisions, must check DB on every write  |
| Auto-increment → base62    | DB counter, convert to base62               | No collisions                                 | Predictable (sequential), counter is SPOF |
| **Key Generation Service** | Pre-generate random keys offline            | No collision check at write time, distributed | Extra service to manage                   |
| Snowflake ID               | timestamp + machine ID + sequence → base62  | No coordination needed                        | More complex, longer codes                |

**The KGS approach (senior/staff):**

1. A background process pre-generates millions of random 7-character base62 keys and stores them in the Key table with `used = false`
2. With 7 characters and base62 encoding: `62^7 ≈ 3.5 trillion` unique codes. That is enough for centuries of usage.
3. When the URL Service needs a key, it atomically marks one as `used = true` and takes it
4. To avoid the KGS becoming a bottleneck, each URL Service instance **pre-fetches a batch** of keys (e.g., 1,000) into memory on startup
5. The instance hands out keys from its local batch. When the batch runs low, it fetches another.
6. If an instance crashes, the ~1,000 pre-fetched keys are lost. This is acceptable: 1,000 out of 3.5 trillion is negligible.

**Custom alias handling:** If the user provides a `customAlias`, skip KGS entirely. Check if the alias exists in the URL table. If not, use it. If taken, return an error. This is a simple DB lookup.

**Mid-level answer:** Hash the URL and check for collisions. Works, but doesn't scale well under high write throughput.

**Senior answer:** KGS with batch allocation. No collisions, no coordination, horizontally scalable.

---

### Deep Dive 2: Caching for Sub-Millisecond Redirects

**The problem:** The redirect path must be as fast as possible. Querying the database on every redirect adds latency and puts unnecessary load on the DB, especially given the 100:1+ read/write ratio.

**Solution: Multi-layer caching**

**Layer 1: Redis (server-side cache)**
- Cache-aside pattern: on redirect, check Redis first (`shortCode → longUrl`)
- On cache hit: return 302 immediately. No DB query.
- On cache miss: query DB, populate Redis, return 302.
- TTL: 24 hours (URLs rarely change, and the Pareto principle applies: 20% of URLs get 80% of traffic)
- Eviction: LRU. Cold URLs get evicted, hot URLs stay cached.
- **Expected cache hit rate: 80-90%** for a well-sized Redis cluster, given the power-law distribution of link popularity.

**Layer 2: CDN caching (staff-level optimization)**
- CDN edge servers can cache 302 responses for short durations (30-60 seconds)
- For viral links getting millions of clicks per minute, the CDN absorbs the vast majority of traffic before it even reaches the API Gateway
- Trade-off: CDN-cached redirects don't generate click events for analytics during the cache window. For a 30-second cache window, this means analytics may undercount by the number of clicks within that window. Whether this is acceptable depends on the analytics SLA.

**Layer 3: Browser caching (careful)**
- If using 301 (permanent redirect), the browser itself caches the redirect. Zero server load for repeat visits from the same user.
- But: kills analytics and makes it impossible to change the destination URL later.
- Recommendation: use 302 (no browser caching) by default. Offer 301 as an option for users who don't need analytics.

**Write-through on creation:** When a new URL is created, write it to both the database and Redis simultaneously. This ensures the first redirect after creation is a cache hit, which matters for URLs shared immediately after creation (the common case).

---

### Deep Dive 3: Database Scaling

**The problem:** Do we need to shard? Let's do the math (math should drive design decisions, not check a box).

**Back-of-envelope:**
- Assume 500M new URLs per year
- After 5 years: 2.5 billion URL records
- Each record: ~500 bytes (shortCode 7B + longUrl ~200B + metadata ~293B)
- Total storage: 2.5B × 500B = **1.25 TB**
- This fits in a single large database instance, but read throughput is the real concern.

**Read throughput:**
- 500M writes/year ≈ 16 writes/sec average
- At 100:1 read ratio: ~1,600 reads/sec average
- Viral link spike: could easily hit 100K+ reads/sec for a single link
- The cache absorbs most of this (80-90% hit rate), so the DB sees ~160-320 reads/sec normally
- But during cache misses on viral links, the DB needs to handle spikes

**Scaling strategy:**

1. **Read replicas**: Given the extreme read/write imbalance, add 3-5 read replicas. Writes go to the primary, reads distribute across replicas. This alone handles the normal load comfortably.

2. **Sharding** (if needed at larger scale): Shard by hash of `shortCode`. Since short codes are random (from KGS), the hash distributes uniformly across shards. No hot-shard problem. This is the simplest and most effective shard key for this system.

3. **DynamoDB approach**: If using DynamoDB, sharding is automatic (partition key = shortCode). DynamoDB handles the distribution, replication, and throughput scaling. You configure read/write capacity units or use on-demand mode. This is the path of least resistance for this specific access pattern.

**Analytics DB scaling:** Click data grows much faster than URL data (every click = a row). ClickHouse handles this natively with column compression and distributed table engines. Partition by date, drop old partitions for retention management.
