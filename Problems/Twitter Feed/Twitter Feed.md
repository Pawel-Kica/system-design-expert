## Requirements

### Functional Requirements

- Users should be able to **scroll their home feed** (a personalized timeline of posts from people they follow)
- Users should be able to **create a post** (tweet: text, optionally images/video)
- Users should be able to **like a post**

### Non-Functional Requirements

- **High availability (AP)**: The feed is the core product. If the feed doesn't load, the entire app is useless. Availability wins over consistency. If a user likes a post and the count shows 99 instead of 100 for a second, nobody notices. But if the feed is down, users leave.
- **Read >> Write (extremely)**: The read/write ratio is massive, probably 10,000:1 or higher. Hundreds of millions of users scroll their feed every minute. A tiny fraction of them are posting or liking at any given moment. This means the feed read path must be hyper-optimized.
- **Low latency feed loading**: Users expect the feed to load instantly. Every 100ms of delay increases bounce rate. The feed is the first thing users see when opening the app.
- **Fan-out at scale**: When a user with 10M followers posts, that post needs to appear in 10M feeds. This is the defining scaling challenge. A celebrity post is the "Taylor Swift problem" of Twitter.

### Out of Scope

- Retweets / reposts
- Comments / replies
- Direct messages
- Hashtags / trending topics
- Search
- Media upload pipeline (assume uploaded to blob storage, URL available)
- Recommendation / ranking algorithm (we show chronological feed)

---

## Core Entities

- **User**: id, username, displayName, avatarUrl, followerCount, followingCount
- **Post**: id, userId, content, mediaUrls[], createdAt
- **Like**: id, postId, userId, createdAt
- **Follow**: followerId, followeeId, createdAt
- **FeedItem**: userId, postId, timestamp (denormalized feed entry)

---

## APIs

### Get Home Feed

```
GET /feed?cursor={cursor}&limit={limit}
Header: JWT
→ { posts: Post[], nextCursor }
```

Returns a paginated list of posts from users the authenticated user follows, sorted by newest first. Cursor-based pagination (not offset) because new posts are constantly being added at the top, which would shift offsets.

### Create Post

```
POST /posts
Header: JWT
Body: { content, mediaUrls[]? }
→ { post: Post }
```

Creates a new post. The post gets stored in the database and must eventually appear in the feeds of all followers.

### Like a Post

```
POST /posts/{postId}/likes
Header: JWT
→ { success: true }
```

Records a like. Must be idempotent: liking the same post twice should not create a duplicate.

---

## High-Level Design

### Architecture Overview

Microservices architecture: Post Service, Feed Service, Like Service, each behind an API Gateway.

### Create Post Flow

1. Client sends `POST /posts` to the API Gateway
2. API Gateway routes to the **Post Service**
3. Post Service writes the post to the **Posts database**
4. Returns the created post to the client

At this point the post exists in the database, but it's not in anyone's feed yet. How does it get there? This is the central design question.

### Get Feed Flow (Naive: Pull Model)

The simplest approach to generate the feed at read time:

1. Client sends `GET /feed` to the API Gateway
2. API Gateway routes to the **Feed Service**
3. Feed Service queries the **Follow table**: "who does this user follow?"
4. For each followee, query the **Posts table**: "get recent posts by this user"
5. Merge all posts, sort by timestamp, apply pagination
6. Return the feed to the client

**Why this is terrible at scale:** If a user follows 500 people, this is 500 queries to the Posts table (or one massive JOIN), merged in memory, sorted, and paginated. This happens on every single feed load. With hundreds of millions of feed loads per minute, this is a guaranteed meltdown.

But for the high-level design, this satisfies the functional requirement. We'll optimize in deep dives.

### Like Flow

1. Client sends `POST /posts/{postId}/likes` to the API Gateway
2. API Gateway routes to the **Like Service**
3. Like Service writes to the **Likes table** (with a unique constraint on `postId + userId` for idempotency)
4. Returns success

### Database Schema

**User table:**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| username | string | unique |
| displayName | string | |
| avatarUrl | string | |
| followerCount | int | denormalized counter |
| followingCount | int | denormalized counter |

**Post table:**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| userId | UUID FK | who posted |
| content | string | up to 280 chars |
| mediaUrls | string[] | optional |
| likeCount | int | denormalized counter |
| createdAt | timestamp | indexed, for feed sorting |

**Follow table:**

| Column | Type | Notes |
| --- | --- | --- |
| followerId | UUID FK | who is following |
| followeeId | UUID FK | who is being followed |
| createdAt | timestamp | |

Composite PK: `(followerId, followeeId)` for uniqueness and fast lookups.

**Like table:**

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| postId | UUID FK | |
| userId | UUID FK | |
| createdAt | timestamp | |

Unique constraint on `(postId, userId)` for idempotency.

### Database Choice

**Postgres** for Users, Posts, Likes, Follows. ACID properties ensure likes aren't duplicated and follow relationships are consistent. The data has clear relationships (user → posts, user → follows). At this scale we'll need to shard, but the relational model fits the data well.

---

## Deep Dives

### Deep Dive 1: Feed Generation — Fan-Out On Write vs Fan-Out On Read

**The problem:** The naive pull model (fan-out on read) queries hundreds of users' posts on every feed load. This is far too slow at Twitter's scale (~500M DAU).

**Two fundamental approaches:**

#### Fan-Out On Read (Pull Model)

What we have in the base design. When a user opens their feed, query all followees' posts in real time.

- **Pros:** Simple. Posts are always fresh. No extra storage.
- **Cons:** Extremely slow at read time. Feed latency grows linearly with the number of people you follow. Doesn't work at scale.
- **Best for:** Users who follow very few people, or systems with low read volume.

#### Fan-Out On Write (Push Model) — The Senior Answer

Pre-compute every user's feed when a post is created, not when the feed is read.

**How it works:**

1. User A creates a post
2. Post Service writes the post to the Posts database
3. Post Service pushes a message to a **message queue** (Kafka)
4. A **Fan-Out Service** consumes the message
5. Fan-Out Service looks up User A's followers (from the Follow table)
6. For each follower, it writes a **FeedItem** entry: `{ userId: followerId, postId: postId, timestamp: now }`
7. These FeedItem entries are stored in a **Feed Cache** (Redis) as a sorted set per user: `feed:{userId}` → sorted set of postIds by timestamp

**Reading the feed is now trivial:**

1. `GET /feed` hits the Feed Service
2. Feed Service reads from Redis: `ZREVRANGE feed:{userId} cursor limit`
3. Gets a list of postIds, hydrates them from the Posts database (or a post cache)
4. Returns the feed. Sub-millisecond for the feed lookup itself.

- **Pros:** Feed reads are blazing fast (just a Redis read). Read path is completely decoupled from social graph complexity.
- **Cons:** Write amplification. If a user has 10M followers, one post = 10M writes to Redis. This is expensive and slow.
- **Best for:** The vast majority of users (who have < 10K followers).

#### Hybrid Approach (Staff Answer)

The write amplification problem makes pure fan-out on write impractical for celebrities (users with millions of followers). The solution: **use both strategies**.

- **Regular users** (< ~10K followers): fan-out on write. Pre-compute feeds as described above. This covers 99%+ of all users.
- **Celebrities** (> ~10K followers): fan-out on read. Do NOT pre-compute their posts into millions of feeds. Instead, when a user loads their feed, merge the pre-computed feed (from Redis) with real-time queries for celebrity posts.

**Feed read with hybrid:**

1. Read the pre-computed feed from Redis (covers posts from regular followees)
2. Check if the user follows any "celebrity" accounts (a flag on the User entity, or a separate set)
3. For each celebrity followee, query their recent posts from the Posts DB or a celebrity-posts cache
4. Merge the two lists, sort by timestamp, return

This gives you the speed of fan-out on write for 99% of the feed, while avoiding the write amplification bomb for celebrities.

**This is exactly what Twitter actually does.** The threshold varies, but the principle is the same: hybrid fan-out.

**Level expectations:**
- **Mid-level:** Describes the pull model, maybe mentions caching
- **Senior:** Fan-out on write with message queue, explains the celebrity problem
- **Staff:** Hybrid approach, can discuss thresholds, trade-offs, cache sizing

---

### Deep Dive 2: Feed Cache Design

**The problem:** Redis is the backbone of the feed read path. How do we size it, structure it, and keep it consistent?

**Data structure:** Redis sorted sets. One sorted set per user: `feed:{userId}`.
- Score = post timestamp (or snowflake ID for ordering)
- Member = postId
- `ZREVRANGE` for newest-first pagination. `ZRANGEBYSCORE` for cursor-based pagination.

**Cache sizing math:**
- 500M users, but only ~200M have active feeds (logged in within last 30 days)
- Keep the last 800 posts per user's feed (enough for deep scrolling)
- Each entry: postId (16 bytes) + score (8 bytes) + overhead ≈ 40 bytes
- Per user: 800 × 40 bytes = 32 KB
- Total: 200M × 32 KB = **6.4 TB**
- This fits in a Redis cluster (sharded across machines). Redis Cluster handles this comfortably.

**Post hydration:** The feed cache only stores postIds, not full post objects. When returning the feed, we need to "hydrate" each postId into a full Post object (content, user info, like count, media). This is a separate cache-aside lookup:
- **Post cache** (Redis): `post:{postId}` → full Post JSON
- On cache miss, query the Posts DB
- TTL: 24 hours (posts don't change often, and like count being slightly stale is fine for AP)

**What happens when the feed cache is cold?** (User hasn't logged in for months, their feed was evicted)
- Fall back to fan-out on read for that specific user
- Rebuild their feed asynchronously in the background
- Next feed load hits the fresh cache

**Cache eviction:** LRU at the Redis cluster level. Inactive users' feeds get evicted first. When they return, the cache is rebuilt.

---

### Deep Dive 3: Like Count at Scale

**The problem:** Like counts can spike massively. A viral post might receive 100K likes per minute. Updating the `likeCount` column on the Post row for every single like creates a hot-row problem: every like tries to write to the same row, causing lock contention.

**Solution: Async aggregation with a counter service**

1. When a user likes a post, write to the **Like table** (the source of truth)
2. Also increment a counter in **Redis**: `INCR likes:{postId}`
3. A background worker periodically flushes Redis counters to the Post table's `likeCount` column (batch update, every 5-10 seconds)

**Why this works:**
- Redis INCR is atomic and handles extreme throughput (100K+ operations/sec on a single key)
- The Post row is only updated every few seconds, not on every like
- The like count shown to users is from Redis (real-time), while the DB value is slightly behind (eventual consistency, which is fine for AP)

**Idempotency:** The Like table has a unique constraint on `(postId, userId)`. If the same user tries to like twice, the DB rejects the duplicate. The Redis INCR might over-count briefly, but the periodic flush reconciles with the actual count from the Like table: `SELECT COUNT(*) FROM likes WHERE postId = ?` or just the delta since last flush.

**Level expectations:**
- **Mid-level:** Direct update to Post.likeCount, no consideration of hot rows
- **Senior:** Redis counter with async flush, understands eventual consistency trade-off
- **Staff:** Discusses reconciliation strategy, sharding of the likes table by postId, and how the counter service handles Redis failures (fall back to DB count)
