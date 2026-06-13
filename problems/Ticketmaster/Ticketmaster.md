## Requirements

### Functional Requirements

- Users should be able to **search for events** (by term, location, type, date)
- Users should be able to **view an event** (event details, venue, performer, seat map with available tickets)
- Users should be able to **book a ticket** (two-phase: reserve a seat, then confirm with payment)

### Non-Functional Requirements

- **Strong consistency for booking (CP)**: No double-booking. A ticket can only be assigned to one user. However, search and viewing can be eventually consistent (AP), it's fine if a newly added event takes a few seconds to appear.
- **Read >> Write (100:1 to 1000:1)**: Many more people search and browse events than actually book. The conversion rate for ticket purchases is around 1%. This heavily favors read optimization.
- **Scalability for popular event surges**: Normal traffic is moderate, but when Taylor Swift or the Super Bowl goes on sale, tens of millions of users hit the system simultaneously for a limited number of seats. This is the defining scaling challenge.
- **Low-latency search**: Users expect fast search results across events, locations, and categories.

### Out of Scope

- Admin event creation / management
- Notifications (email, push, SMS)
- GDPR compliance
- Payment system internals (abstracted to Stripe)
- Personalized recommendations / ranking

---

## Core Entities

- **Event**: id, venueId, performerId, name, description, date
- **Venue**: id, name, location, seatMap
- **Performer**: id, name, type
- **Ticket**: id, eventId, seat, price, status (available | reserved | booked), userId, reservedAt

---

## APIs

### Search Events

```
GET /search?term=...&location=...&type=...&date=...
-> { events: PartialEvent[] }
```

Returns a list of events matching the criteria. "Partial" because we only return enough info to render search results (name, date, venue, performer). User clicks a result to see full details.

### View Event

```
GET /events/{eventId}
-> { event: Event, venue: Venue, performer: Performer, tickets: Ticket[] }
```

Returns everything needed to render the event page: event details, venue info, performer info, and all tickets (with their status and seat location) to render the seat map.

### Reserve Ticket

```
POST /booking/reserve
Header: JWT
Body: { ticketId }
-> { success, expiresAt }
```

Reserves a ticket for the authenticated user. Starts a 10-minute countdown for the user to complete payment. No userId in the body (security: use JWT from header to prevent impersonation).

### Confirm Booking

```
PUT /booking/confirm
Header: JWT
Body: { ticketId, paymentDetails }
-> { success }
```

Confirms the purchase. Payment details are handled via Stripe's client libraries (payment intents). Stripe processes asynchronously and calls back via webhook.

---

## High-Level Design

### Architecture Overview

Microservices architecture: Event CRUD Service, Search Service, Booking Service, each behind an API Gateway (handles routing, authentication, rate limiting).

### View Event Flow

1. Client sends `GET /events/{eventId}` to the API Gateway
2. API Gateway routes to the **Event CRUD Service**
3. Service joins Event, Venue, and Performer tables, queries Tickets for this event
4. Returns everything to the client for rendering the event page and seat map

### Search Events Flow (Naive)

1. Client sends `GET /search` to the API Gateway
2. API Gateway routes to the **Search Service**
3. Search Service queries Postgres: `SELECT * FROM events WHERE type IN (...) AND name LIKE '%term%'`

**Why this is terrible:** The LIKE wildcard forces a full table scan. No index can help with leading wildcards. This works functionally but is far too slow at any meaningful scale. We'll fix this in deep dives.

### Book Ticket Flow (Two-Phase)

**Reserve:**
1. Client sends `POST /booking/reserve` with ticketId
2. Booking Service updates the ticket row: set `status = 'reserved'` and `reservedAt = NOW()`
3. Returns success with a 10-minute expiry time

**Confirm:**
1. Client sends `PUT /booking/confirm` with ticketId and paymentDetails
2. Booking Service forwards payment to **Stripe**
3. Stripe processes asynchronously and calls back via **webhook**
4. On success: Booking Service updates ticket to `status = 'booked'` and assigns `userId`
5. On failure: Booking Service reverts to `status = 'available'`

**Reservation Expiry (cron job, mid-level approach):**
A cron job runs every ~10 minutes, querying for tickets where `status = 'reserved' AND reservedAt < NOW() - INTERVAL '10 minutes'`, and resets them to `available`. Problem: there's up to a 10-minute delta where tickets are incorrectly reserved (reserved for up to 20 minutes instead of 10). Good enough for mid-level, not for senior+.

### Database Schema

**Event table:**

| Column      | Type      | Notes           |
| ----------- | --------- | --------------- |
| id          | UUID PK   |                 |
| venueId     | UUID FK   |                 |
| performerId | UUID FK   |                 |
| name        | string    |                 |
| description | string    |                 |
| date        | timestamp | indexed         |

**Venue table:**

| Column   | Type    | Notes        |
| -------- | ------- | ------------ |
| id       | UUID PK |              |
| name     | string  |              |
| location | string  | for geo      |
| seatMap  | JSON    | seat layout  |

**Performer table:**

| Column | Type    | Notes |
| ------ | ------- | ----- |
| id     | UUID PK |       |
| name   | string  |       |
| type   | string  |       |

**Ticket table:**

| Column     | Type      | Notes                            |
| ---------- | --------- | -------------------------------- |
| id         | UUID PK   |                                  |
| eventId    | UUID FK   | indexed                          |
| seat       | string    | seat location                    |
| price      | decimal   |                                  |
| status     | enum      | available, reserved, booked      |
| userId     | UUID FK   | nullable, set on booking         |
| reservedAt | timestamp | nullable, for expiry cron job    |

### Database Choice

**Postgres.** ACID properties are critical for ticket booking (no double-booking via transactions). Clear relational structure (events-venues-performers-tickets). A NoSQL database would also work, the more senior insight is that the SQL vs NoSQL debate is less important than identifying the required qualities: ACID transactions, relational joins for the event page, indexed lookups by eventId.

---

## Deep Dives

### Deep Dive 1: Low-Latency Search with Elasticsearch

**The problem:** SQL LIKE queries with leading wildcards (`%term%`) require full table scans. With millions of events, this is unacceptably slow.

**Solution: Elasticsearch with CDC sync**

Introduce Elasticsearch as a search-optimized database alongside Postgres.

**How it works:**
1. Event text (name, description, performer) is **tokenized** into terms
2. An **inverted index** maps each term to the events containing it. "Playoff" maps to Event 1, 2, 3. "Swift" maps to Event 5, 6, N.
3. Searching "playoff" instantly returns all matching events via hash map lookup
4. Elasticsearch also supports **geospatial queries** (quadtrees + geohashing) for location-based search

**Keeping ES in sync via CDC:**
- Changes to Postgres (event created/updated) are captured via **Change Data Capture** and streamed to Elasticsearch
- Write volume is very low (events/venues/performers rarely change), so direct CDC works without batching or queuing
- Important: do NOT use Elasticsearch as a primary data store (durability and transaction concerns)

**Caching search results:**
- **CDN caching**: Cache search API responses at edge (30-60s TTL). Extremely effective for popular events. Downside: less useful with high query permutation counts (lat/long precision) or personalized results.
- **OpenSearch node query caching**: LRU cache of top 10K queries per shard, enabled via config
- **Redis caching**: Cache normalized search terms with results, invalidate on updates

**Level expectations:**
- **Mid-level:** SQL LIKE query, mentions it's slow
- **Senior:** Elasticsearch with inverted index, CDC sync, explains tokenization
- **Staff:** CDN caching with trade-off analysis, geospatial support, discusses when CDN caching breaks down

---

### Deep Dive 2: Reservation Expiry with Distributed Lock

**The problem:** The cron job approach has a delta of up to N minutes where tickets remain incorrectly reserved after the 10-minute window expires. A ticket could be reserved for 19 minutes instead of 10.

**Solution: Redis distributed lock**

Remove the cron job, the `reserved` status, and the `reservedAt` column entirely. Instead, use Redis as a distributed lock.

**How it works:**
- When a user reserves a ticket, store a key in Redis: `ticket_id -> true` with a **TTL of 10 minutes**
- Do NOT update the database at all during reservation
- The Ticket table only has two statuses: `available` and `booked`

**Reserve flow:**
1. User clicks a seat to reserve it
2. Set `ticket_id` with TTL 10 minutes in Redis
3. Return success

**Viewing available seats:**
1. Query Postgres for all tickets with `status = 'available'`
2. For each ticket ID, check Redis to see if it's locked (reserved)
3. Filter out locked tickets from the available list
4. Return the filtered seat map

**Expired reservation:**
After exactly 10 minutes, the Redis key auto-expires. The next user who queries the seat map will not find this ticket in Redis, so it appears available. Immediate, exact, no cron job needed.

**Confirm flow:**
1. Stripe webhook confirms payment succeeded
2. Update ticket in Postgres: `status = 'booked'`, assign `userId`
3. Delete the Redis lock (or let it expire naturally)

**Why distributed?** Multiple Booking Service instances run in parallel (horizontally scaled). They all need the same consistent view of which tickets are reserved. An in-memory lock per instance wouldn't work; Redis provides a shared, external lock.

**What if Redis goes down?**
1. Bring a new instance up immediately
2. Any reservations from the last 10 minutes are lost
3. Multiple users might try to book the same ticket
4. Postgres ACID ensures only one succeeds (first write wins via transaction)
5. Others get an error, bad UX for a brief window but no data corruption

**Level expectations:**
- **Mid-level:** Cron job with reserved_timestamp (passing)
- **Senior:** Redis distributed lock with TTL (strong answer)
- **Staff:** Discusses failure scenarios, recovery, product team trade-offs

---

### Deep Dive 3: Scalability for Popular Events

#### Real-Time Seat Map Updates

**The problem:** After initial page load, the seat map grows stale. Users click on seats that appear available but were just reserved or booked by someone else. For popular events, this happens constantly.

**Solution: Server-Sent Events (SSE)**

Set up a persistent unidirectional connection (server to client). When any ticket's status changes (reserved or booked), push the update to all clients viewing that event. SSE is preferred over WebSockets because we only need server-to-client communication (unidirectional).

#### Virtual Waiting Queue (the Taylor Swift Problem)

**The problem:** Even with real-time updates, when millions of users fight for thousands of seats, the UX is terrible: seats go black instantly as everything gets booked within seconds.

**Solution: Virtual waiting queue**

- **Admin-enabled** for popular events (not all events need this)
- Instead of showing the event page, users enter a **waiting queue** (Redis sorted set, ordered by arrival time or randomized for fairness)
- **Batch-release**: as seats become available (e.g., every 100 bookings), release the next batch of users
- **Notify via SSE** when it's the user's turn
- Simple but elegant: protects backend services from surge while improving UX

#### General Scaling

- **Read replicas**: Given 100:1+ read/write ratio, add Postgres read replicas for event/venue/performer queries
- **Redis cache**: Cache event/venue/performer data aggressively (rarely changes). Only ticket queries hit the database.
- **Shard key candidates**: `event_id` (most queries use it) or `venue_id` (geographic affinity if shards are distributed geographically)
- **Horizontal auto-scaling**: Each microservice scales independently with load balancers
- **API Gateway**: AWS API Gateway (managed, auto-scaling)
- **Back-of-envelope**: Do the math to determine if sharding is needed. Calculate storage for events, venues, tickets. If it fits in a single Postgres instance, read replicas + caching may suffice.

**Level expectations:**
- **Mid-level:** Mentions scaling, maybe read replicas
- **Senior:** SSE for real-time, Redis caching, discusses shard key trade-offs
- **Staff:** Virtual waiting queue, CDN caching, nuanced trade-off analysis, back-of-envelope math driving decisions
