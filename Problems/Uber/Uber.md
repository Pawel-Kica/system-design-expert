## Requirements

### Functional Requirements

- Users should be able to **request a ride** (pickup location, destination)
- Users should be able to **see nearby drivers** on the map before requesting
- Drivers should be able to **accept/decline ride requests**
- Users should be able to **track their ride in real-time** (driver location on map, ETA)

### Non-Functional Requirements

- **Strong consistency for ride matching (CP)**: A ride can only be assigned to one driver. No double-assignment. However, driver location updates can be eventually consistent (AP), a few seconds of staleness is fine.
- **Write-heavy for location updates**: Millions of drivers send GPS updates every 5 seconds. This is the inverse of Ticketmaster's read-heavy pattern. Location writes dominate everything else.
- **Low-latency geospatial queries**: "Find available drivers within 3km" must return in milliseconds. Standard SQL range queries on lat/lng are too slow at scale.
- **Real-time tracking**: Once matched, the rider needs sub-second updates of the driver's position moving on the map. This requires persistent connections, not polling.

### Out of Scope

- Payment processing internals (Stripe/Braintree)
- Surge pricing algorithm
- Driver onboarding / background checks
- Rating / review system
- Ride scheduling (future rides)
- Ride sharing (UberPool)

---

## Core Entities

- **Rider**: id, name, email
- **Driver**: id, name, vehicleInfo, status (available | en_route | busy)
- **Ride**: id, riderId, driverId, pickupLocation, dropoffLocation, status (requested | matched | in_progress | completed | cancelled), fare, createdAt

---

## APIs

### Request a Ride

```
POST /rides
Header: JWT
Body: { pickupLocation: { lat, lng }, dropoffLocation: { lat, lng } }
-> { rideId, estimatedFare, estimatedETA }
```

Creates a new ride request. The system finds nearby available drivers and sends them the request.

### Get Nearby Drivers

```
GET /drivers/nearby?lat=...&lng=...&radius=...
-> { drivers: { id, location, eta }[] }
```

Returns available drivers near a location. Used to show drivers on the map before the user requests a ride.

### Accept Ride (driver)

```
PUT /rides/{rideId}/accept
Header: JWT (driver)
-> { success, ride: Ride }
```

Driver accepts a ride request. First driver to accept wins.

### Update Driver Location

```
PUT /drivers/location
Header: JWT
Body: { lat, lng }
-> { success }
```

Driver app sends this every 5 seconds to keep their position current.

### Track Ride (real-time)

```
GET /rides/{rideId}/track
-> WebSocket stream: { driverLocation: { lat, lng }, eta, status }
```

Opens a persistent connection for the rider to receive real-time driver location updates.

---

## High-Level Design

### Architecture Overview

Microservices architecture: Ride Service, Location Service, Matching Service, each behind an API Gateway (handles routing, authentication, rate limiting).

### Request Ride Flow

1. Client sends `POST /rides` to the API Gateway
2. API Gateway routes to the **Ride Service**
3. Ride Service creates a ride record in Postgres with status `requested`
4. Ride Service calls the **Matching Service** to find nearby available drivers
5. Matching Service queries the **Location Service** for drivers within radius
6. Location Service runs a SQL query: `SELECT * FROM driver_locations WHERE lat BETWEEN ... AND lng BETWEEN ... AND status = 'available'`
7. Matching Service sends ride request to the closest N drivers via push notification
8. First driver to accept: Ride Service updates ride to `matched`, driver status → `en_route`

### Driver Location Update Flow (Naive)

1. Driver app sends `PUT /drivers/location` every 5 seconds
2. Location Service writes/updates the driver's row in Postgres
3. **Problem**: millions of drivers x updates every 5 seconds = millions of writes/second. Postgres cannot handle this write throughput.

### Accept Ride Flow (Naive)

1. Driver taps "Accept" → `PUT /rides/{rideId}/accept`
2. Ride Service checks if ride status is still `requested`
3. Updates ride: `driverId = driver_id, status = 'matched'`
4. **Problem**: If two drivers accept simultaneously, a race condition can assign the ride to both without proper locking.

### Ride Tracking (Naive)

1. Rider polls `GET /rides/{rideId}` every 5 seconds
2. Returns latest driver location from the database
3. **Problem**: Polling is wasteful (most requests return no change), adds unnecessary load, and introduces up to 5 seconds of staleness.

### Database Schema

**Rider table:**

| Column | Type      | Notes |
| ------ | --------- | ----- |
| id     | UUID PK   |       |
| name   | string    |       |
| email  | string    |       |

**Driver table:**

| Column      | Type    | Notes                          |
| ----------- | ------- | ------------------------------ |
| id          | UUID PK |                                |
| name        | string  |                                |
| vehicleInfo | JSON    | make, model, plate, color      |
| status      | enum    | available, en_route, busy      |

**Ride table:**

| Column      | Type      | Notes                                                  |
| ----------- | --------- | ------------------------------------------------------ |
| id          | UUID PK   |                                                        |
| riderId     | UUID FK   |                                                        |
| driverId    | UUID FK   | nullable, set on match                                 |
| pickupLat   | decimal   |                                                        |
| pickupLng   | decimal   |                                                        |
| dropoffLat  | decimal   |                                                        |
| dropoffLng  | decimal   |                                                        |
| status      | enum      | requested, matched, in_progress, completed, cancelled  |
| fare        | decimal   |                                                        |
| createdAt   | timestamp |                                                        |

**Driver Location table (naive):**

| Column    | Type      | Notes             |
| --------- | --------- | ----------------- |
| driverId  | UUID FK   | PK                |
| lat       | decimal   |                   |
| lng       | decimal   |                   |
| updatedAt | timestamp | last GPS ping     |

### Database Choice

**Postgres.** ACID properties are critical for ride assignment (no double-matching via transactions). Clear relational structure for riders, drivers, rides. The location storage problem will be addressed in deep dives, Postgres is not the right tool for high-frequency ephemeral location data.

---

## Deep Dives

### Deep Dive 1: Real-Time Location Tracking with Redis Geospatial

**The problem:** Millions of drivers send GPS updates every 5 seconds. Writing each update to Postgres is impossible at this scale (millions of writes/second). Additionally, querying "find drivers within 3km" via SQL with lat/lng range comparisons requires scanning many rows and is slow.

**Solution: Redis with geospatial indexes**

Use Redis's built-in geospatial data structure (GEOADD / GEOSEARCH) for all driver location operations.

**How it works:**
1. Driver sends location update → Location Service writes to Redis: `GEOADD drivers:{city} lng lat driver_id`
2. To find nearby drivers: `GEOSEARCH drivers:{city} FROMLONLAT lng lat BYRADIUS 3 km ASC COUNT 20`
3. Redis returns driver IDs sorted by distance in sub-millisecond time

**Why Redis geospatial?**
- O(log N) for both writes and spatial queries (sorted sets + geohashing internally)
- Perfect for ephemeral, high-frequency data. Driver locations are only useful when fresh.
- No persistence needed: if Redis crashes, drivers resend their location within 5 seconds. Zero data loss in practice.
- Sub-millisecond latency for both writes and reads

**Partitioning by city/region:**
- Separate Redis keys per city/region: `drivers:new_york`, `drivers:london`, `drivers:krakow`
- Reduces the working set per query (only search drivers in the same city)
- Geographic sharding maps naturally to real-world usage patterns
- Can place Redis instances in regional data centers for lower latency

**Level expectations:**
- **Mid-level:** SQL queries with lat/lng ranges, mentions it's slow
- **Senior:** Redis geospatial with GEOADD/GEOSEARCH, partitioning by city
- **Staff:** Discusses geohashing internals, multi-region deployment, fallback if Redis goes down

---

### Deep Dive 2: Ride Matching and Preventing Double-Assignment

**The problem:** When a rider requests a ride, multiple nearby drivers receive the request simultaneously. If two drivers accept at the same time, a race condition can assign the ride to both (double-match).

**Solution: Redis distributed lock on ride assignment**

Use a Redis lock per ride_id to ensure exactly one driver claims it.

**How it works:**
1. Ride created with status `requested`
2. Nearby drivers notified via push notification / WebSocket
3. Driver A taps "Accept" → Ride Service attempts: `SET lock:ride:{rideId} driver_A NX EX 30`
4. `NX` = only set if key doesn't exist. If lock acquired: proceed with assignment
5. Driver B taps "Accept" → `SET` fails (lock exists), return "ride already taken"
6. Ride Service updates Postgres: `driverId = driver_A, status = 'matched'`
7. Delete the lock (or let it expire)

**Why not just use a Postgres SELECT FOR UPDATE?**
- You could, but the lock needs to span the async notification + accept cycle (seconds, not milliseconds)
- Redis lock with NX is faster and doesn't hold a database connection open
- Postgres transactions should be short-lived; holding one open for 30 seconds is wasteful

**Ride request timeout:**
- If no driver accepts within 30 seconds (Redis TTL), the lock expires
- Ride Service expands the search radius and retries with new set of drivers
- After 3 attempts, notify the rider "no drivers available"

**What if Redis goes down?**
- Fall back to Postgres transaction-level locking (SELECT FOR UPDATE)
- Slower but functionally correct
- ACID ensures only one driver gets the ride even without Redis

**Level expectations:**
- **Mid-level:** Simple Postgres transaction (works but slower)
- **Senior:** Redis distributed lock with NX + TTL
- **Staff:** Discusses failure scenarios, fallback to Postgres, retry strategy with expanding radius

---

### Deep Dive 3: Real-Time Ride Tracking via WebSocket + Pub/Sub

**The problem:** Once matched, the rider needs to see the driver's real-time location on the map with updated ETA. Polling is wasteful and introduces staleness.

**Solution: WebSocket with Redis Pub/Sub**

**How it works:**
1. Once ride is matched, rider app opens a WebSocket to the **Tracking Service**
2. Tracking Service subscribes to a Redis Pub/Sub channel: `ride:{rideId}`
3. Driver continues sending GPS updates every 5 seconds to the Location Service
4. Location Service publishes each update to `ride:{rideId}` channel
5. Tracking Service receives the update and forwards it over WebSocket to the rider
6. Client renders the driver's movement on the map

**Why WebSocket over SSE?**
- Bidirectional: rider can send messages too (cancel ride, change destination, send message to driver)
- More natural for ongoing two-party interaction
- SSE would work for one-way tracking but limits rider actions to separate HTTP requests

**ETA calculation:**
- Use a routing API (Google Maps Directions, OSRM) for ETA based on driver's current location
- Recalculate every 30 seconds or on significant route deviation
- Cache the route polyline to avoid excessive API calls

**Scaling WebSocket connections:**
- Each Tracking Service instance holds thousands of concurrent WebSocket connections
- Redis Pub/Sub decouples publishers (Location Service) from subscribers (Tracking Service instances)
- Doesn't matter which Tracking Service instance the rider connects to: Redis routes the message
- When ride completes, close WebSocket and unsubscribe from channel

**Level expectations:**
- **Mid-level:** Polling every N seconds (works but wasteful)
- **Senior:** WebSocket with Redis Pub/Sub, explains why bidirectional
- **Staff:** Discusses scaling WebSocket connections, Pub/Sub fan-out, ETA caching strategy
