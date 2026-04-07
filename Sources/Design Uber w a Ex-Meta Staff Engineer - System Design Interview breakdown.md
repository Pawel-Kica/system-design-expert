Source: [YouTube](https://www.youtube.com/watch?v=lsKU38RKQSo)
Transcribed: 2026-04-07

---

## Introduction

This is the second system design problem breakdown from Hello Interview (the first was Ticketmaster). The problem: **Design Uber**, the hardest/most interesting of the proximity search problems. If you can do this one, you can probably do Find My Friends, Yelp, etc. It has a lot of the same common pieces and is asked a ton at top companies, notably Google and Meta.

The presenter spent five years at Meta as an interviewer and staff engineer, now co-founder of Hello Interview. He's asked this question well over 50 times and knows exactly where candidates of all levels do well and where they get tripped up.

Written breakdown also available at hellointerview.com.

---

## Interview Roadmap

The recommended roadmap for any system design interview (especially user-facing products):

1. **Requirements** (functional + non-functional)
2. **Core Entities & API** (objects exchanged/persisted, user-facing APIs)
3. **High-Level Design** (satisfy core functional requirements simply)
4. **Deep Dives** (satisfy non-functional requirements)

Each section relies on the one before it.

---

## Functional Requirements

Functional requirements are the core features of the system, often framed as "users should be able to" statements. Ideally, the interviewer picks a system you know well. For Uber:

1. **Users should be able to input a start location and destination and get an estimated fare.** This is the opening screen of the Uber app: you say where you want to go, it knows where you are, and gives you price estimates (UberX, UberXL, etc.). Multiple car types are **out of scope**, just one estimate.

2. **Users should be able to request a ride to be matched with a nearby available driver in real time.** Based on the estimate, users request the ride.

3. **Drivers should be able to accept/deny a request and navigate to pickup/drop-off.** The driver side of the matching.

**Out of scope:**
- Multiple car types
- Ratings for drivers and riders
- Schedule a ride in advance

It's important to clarify out-of-scope items. It shows product thinking and the ability to prioritize. Focus on **at most three core features**, everything else goes out of scope. Interviews move really quickly.

---

## Non-Functional Requirements

Non-functional requirements are the qualities of the system (the "ilities": scalability, availability, integrity, etc.).

**Most candidates make the mistake of:**
- A) Rushing through NFRs
- B) Just writing down buzzwords

This is both not useful and doesn't help with the design later. Particularly for senior and staff candidates, NFRs are incredibly important. They dictate your deep dives. You want to:
- A) Identify qualities unique and relevant to this system
- B) Put them in the context of this system
- C) Ideally quantify them

**For Uber:**

1. **Low latency matching** (less than one minute to match, or failure). If no match, give the user a message saying no available drivers.

2. **Consistency of matching** (CAP theorem consideration). We care about consistency specifically for matching: any given ride should only ever be matched to one driver. Ride to driver is one-to-one. No multiple drivers getting the same ride. Consistency is incredibly important here.

3. **Highly available outside of matching.** Minimize downtime, process requests 24/7. The system should be consistently available and reliable for everything except the matching (which prioritizes consistency).

4. **High throughput in surges** for peak hours or special events. A football game or Taylor Swift concert just ended, massive surges. Given stadiums/New Year's Eve, surges are probably on the order of **hundreds of thousands of requests within a given region**.

**Out of scope:**
- GDPR and user privacy
- Resilience and system failure handling
- Monitoring, logging, alerting
- Deployment, CI/CD pipelines

---

## A Note on Back-of-the-Envelope Estimations

The presenter's strong opinion: back-of-the-envelope estimations early in the design are almost always a waste of time. Candidates estimate DAU, bandwidth, storage, look at numbers and go "okay, so it's a lot" and move on. They already knew it was a scaled system. The interviewer learned nothing, and the candidate burned valuable time (the interview is usually only ~35 minutes excluding pleasantries and Q&A).

**Recommended approach:** Tell the interviewer: "I know a lot of candidates do back-of-the-envelope estimations at this point. It's my preference that I forego them for now and instead do estimations during my high-level design if the result will directly influence my design. Is that okay with you?" 99.9% of interviewers say yes.

---

## Core Entities

Why "core entities" instead of "data model"? Because at this point you don't know the full schema, all fields and columns. It's too early. You can sketch out what the core entities are (what's persisted, usually maps 1:1 with tables/collections). Document the full schema as you go through the high-level design.

**Core entities for Uber:**
- **Ride**
- **Driver**
- **Rider**
- **Location** (the current location of all drivers, so we can match them based on proximity)

---

## API Design

The API goal is simple: use core entities to satisfy functional requirements one by one. You might have one or many APIs per requirement. This is a moving model that can be updated as you go.

### 1. Get Fare Estimate (satisfies FR1)

```
POST /ride/fare-estimate
Body: { source, destination }
Returns: Partial<Ride> { id, rideId, ETA, price }
```

Creates a ride entity with ETA and price. If the user doesn't end up requesting, the excess data is great for analytics.

### 2. Request a Ride (satisfies FR2)

```
PATCH /ride/request
Body: { rideId }
Returns: 200 or 400 (asynchronous operation)
```

Takes the ride ID from the estimate. Since matching can take up to a minute, the operation is asynchronous.

### 3. Location Update (supporting endpoint for matching)

```
PUT /location/update
Body: { lat, lng }
```

Drivers call this every N seconds to keep the location DB up to date. Many candidates miss this upfront, that's fine, you add it as you design.

### 4. Driver Accept/Deny (satisfies FR3 part 1)

```
PATCH /ride/driver-accept
Body: { rideId, accept: boolean }
```

Driver accepts or denies matching for a given ride.

### 5. Driver Status Update (satisfies FR3 part 2)

```
PATCH /ride/driver-update
Body: { rideId, status: "picked_up" | "dropped_off" }
Returns: { lat, lng } | null
```

Driver updates status (picked up passenger, dropped off). Returns lat/lng of next destination, or null if ride is complete.

**Tips:**
- **Don't write data types** if you're a senior/staff candidate. The interviewer knows a latitude is a number and a rideId is a string. It's a waste of time and borderline insulting. Only spell out unique types like enums.
- **Don't put userId in request body.** Get it from the JWT/session token in the request header. Putting userId in the body would allow any user to impersonate another. Good API security.

---

## High-Level Design

The goal is to satisfy core functional requirements. Go through APIs one by one, using them as the input flow of data. Ideally you're about 15 minutes into the interview at this point (mid-level: 15-20 min, senior/staff: 15 or less).

### Flow 1: Fare Estimate

**Rider Client** (iOS/Android, no web) → **AWS Managed API Gateway** → **Ride Service** → **Third-Party Mapping** (e.g., Google Maps) → **Primary DB**

The API Gateway handles:
- Load balancing
- Routing (to correct microservice)
- Authentication, SSL termination, rate limiting

The Ride Service uses a third-party mapping service (Google Maps) to get the ETA based on current traffic from source to destination, then uses that ETA to estimate price (maybe a simple multiplication).

**Ride Schema:**

| Field | Notes |
|-------|-------|
| id | |
| riderId | FK to Rider |
| fare | estimated |
| ETA | |
| source | lat/lng |
| destination | lat/lng |
| status | starts as "fare_estimated" |

**Rider Schema:** id, metadata (location, payment info, etc.), not the most interesting thing for this design.

### Flow 2: Request a Ride (Matching)

Introduces a separate **Ride Matching Service** because:
- It does something incredibly different from the Ride Service
- It's more computationally expensive
- It's an asynchronous process
- Separate services can scale independently and be maintained by separate teams

**Flow:**
1. Rider requests ride → hits Ride Matching Service
2. Matching Service queries **Location DB** for drivers within N miles of rider's location
3. Location DB is populated by drivers calling the **Location Service** (update location every 5 seconds)
4. Matching Service checks driver status via Ride Service → Primary DB (filter out drivers who are in_ride, offline, etc.)
5. Matching Service sends push notification via **Notification Service** (using Apple Push Notifications / Firebase) to closest available drivers
6. Driver accepts → calls driver-accept endpoint → Ride Service updates Primary DB

**Driver Schema:**

| Field | Notes |
|-------|-------|
| id | |
| metadata | car, license plate, image |
| status | in_ride, offline, available |

**Ride Schema additions:**
- driverId (optional, only set once matched)
- status updates to "matched" / "in_ride"

### Flow 3: Driver Navigation

Driver calls the update endpoint to report status changes (picked_up, dropped_off). Returns lat/lng of next destination (the drop-off location after pickup), or null when ride is complete.

---

## Deep Dives

This is where senior/staff candidates earn their keep. Level expectations:

- **Mid-level:** The high-level design above is pretty close to passing. Interviewer will probe on matching algorithm, consistency, location DB speed, sharding, scaling. Answer competently.
- **Senior:** Need to go deep in at least 2 places to satisfy non-functional requirements.
- **Staff:** Higher bar, go deeper in 2-3 places. Ideally teach your interviewer something. Leverage personal experience with specific technologies (e.g., DynamoDB properties).

Deep dives are informed by going through the non-functional requirements one by one.

---

### Deep Dive 1: Location Service and Geospatial Indexing

**The core question:** How do we store driver locations and make proximity queries fast?

#### Back-of-the-Envelope (when it matters)

Uber has ~6 million drivers. Estimate ~3 million active at any given time. Updates every 5 seconds = **600,000 updates per second** (TPS). This is where estimation matters because it directly influences the design.

#### Option 1: Postgres (Bad)

Use SQL with lat/lng columns and range queries with upper/lower/left/right bounds.

**Why this sucks:**
- B-tree indexes are optimized for **one-dimensional data**, but lat/lng is inherently two-dimensional. Queries are slow and non-performant.
- Wide-region queries require scanning a large number of rows
- Postgres handles ~2-4k TPS. We need 600k. Way off.

If a candidate proposes this, the interviewer would probe deeper, even for mid-level.

#### Option 2: Postgres + PostGIS with Quad Trees (Okay)

A **geospatial index** makes querying spatial data more efficient. PostGIS is Postgres's extension for this.

**How quad trees work:**
- Take a map, recursively split it into 4 regions
- Each region is a node in a tree
- A K value (e.g., 5) determines whether to recursively split further
- If a region has fewer than K drivers, stop. If more, split into 4 again
- To query: walk down the tree to the leaf node containing the list of drivers in that cell

**Still need to handle TPS problem:** Only option is adding a **queue** to batch writes (batch 600k down to 4k).

**Downsides:**
- Queue introduces significant latency, location DB becomes mildly inaccurate
- Writing new data requires re-indexing the entire quad tree (expensive)
- Quad tree takes up a lot of memory

**Interview assessment:** Mid-level candidate landing here is passing. Senior might pass but interviewer would point out limitations. Staff candidate: not enough.

#### Option 3: Redis with Geohashing (Optimal)

**Redis** handles 100k to ~1M TPS in a cluster. Solves the TPS problem.

**Geohashing** is a different geospatial algorithm:
- Split the region into 4, recursively split into 4 again
- Unlike quad trees, it's **not density-dependent**: no K value, just split until reaching desired precision
- Results in a base-32 encoded string: longer string = more precise, shorter = less precise
- You can look at just the first 1, 2, 3 characters to understand the larger region before zooming in
- Redis supports geohashing out of the box

**Benefits of geohashing:**
- Easy to calculate (relatively cheap)
- Easy to store (just a string)
- No additional data structure needed
- No re-indexing on writes

**Quad Tree vs. Geohash decision framework:**
- **Quad tree:** Great for uneven density of locations (e.g., Yelp: dense NYC but empty Atlantic Ocean). Bad when you have high-frequency updates because re-indexing is expensive.
- **Geohash:** Indiscriminate on density (world split into evenly precise boxes). Less good for uneven distribution, but excellent for high-frequency writes.

**For Uber:** Despite uneven density of drivers, the high frequency of writes (600k TPS) makes geohashing the optimal answer.

**Note:** Uber actually uses something similar to geohashing but with hexagons instead of squares (H3). This solves the problem that the distance from the center of a square to a corner differs from center to edge. Built in-house at Uber. But knowing quad trees and geohashing is totally sufficient for interviews.

#### Dynamic Location Updates

To reduce the 600k TPS, instead of updating every 5 seconds blindly, the **client can send adaptive updates** based on:
- **Status:** Is the driver accepting rides? If not, don't send updates.
- **Speed:** Are they parked? If parked for 20 minutes, their location isn't changing.
- **Proximity to ride requests or hot areas:** If they're in the boonies, lower precision is fine.

This logic goes on the driver client. Could reduce 600k to 100k or even less.

---

### Deep Dive 2: Consistency of Matching

Two things to ensure:
1. **Can't send more than one request at a time for a given ride**
2. **Don't send any driver more than one request at a time**

#### Problem 1: One request per ride (Easy)

This is simple logic within the Ride Matching Service. A single ride is handled by a single server instance. Use a while loop:

```
while (no_match):
    driver = next driver from list
    lock driver
    send notification to driver
    wait 10 seconds
    if accepted: done
    else: continue to next driver
```

#### Problem 2: One request per driver (Hard)

This is hard because ride matching services are **horizontally scaled**. Multiple instances handling different rides could all pick the same closest driver (e.g., after a concert, 100k people all near driver #1). Driver #1 gets 100 notifications at once. Bad.

**Option A: Status field in driver table (Okay for mid-level)**

Add a "request_sent" status to the driver table. Before sending a request, check the status (atomically). If "request_sent", skip to next driver.

**Problem:** If the driver doesn't respond, the status is stuck as "request_sent" forever. Need cleanup.

**Cron job approach:** Run a cron job every N seconds/minutes to find drivers in "request_sent" status where the status update time exceeds the timeout (e.g., 5 seconds). Reset them to "available."

**Problem with cron:** There's a delta between when the driver should have become available and when the cron job runs. If cron runs every minute and the lock should last 5 seconds, it could take up to 55 seconds before unlock. In a busy area, this means suboptimal matching.

**Interview assessment:** Great for mid-level, maybe passing for senior, not good enough for staff.

**Option B: Distributed Lock with TTL (Optimal)**

Use Redis (or DynamoDB) as a distributed lock:

```
SET driver_id true TTL 5s
```

- Set the driver ID as a key with a TTL of 5 seconds
- Any service instance checking that driver sees the key exists → skip, driver is locked
- If driver doesn't respond, the entry is **automatically removed** after 5 seconds
- Next read won't see the driver ID → can send them a request

This is a distributed lock, very similar to the Ticketmaster approach. All ride matching service instances have a **consistent global view** of which drivers are available.

**Implementation alternatives:**
- Could use the same Redis instance as the location DB
- Could use DynamoDB (which supports TTLs on rows) with a separate "driver_lock" table, avoiding an additional technology

**Pseudocode for ride matching:**

```
while no_match:
    driver = next_driver(location_db_results)
    lock_driver(driver_id)  // set in distributed lock with TTL
    send_notification(driver, ride)
    wait(10 seconds)
    // driver accepts → status updates to in_ride → no_match = false
    // driver doesn't respond → lock auto-expires → continue
```

Some way to notify the user (notification, polling, etc.) once matched.

---

### Deep Dive 3: Handling High Throughput Surges

For popular events (concerts, sports games, New Year's Eve). Need to scale dynamically.

**Solution: Ride Request Queue**

Introduce a queue between the API Gateway and the Ride Matching Service:

**Rider** → API Gateway → **Ride Request Queue** → **Ride Matching Service**

When rides come in, they sit on the queue. Ride Matching Service pulls off the queue when ready. Huge surge? No problem, it all waits in the queue.

**Queue partitioning by region:** A naive FIFO queue has a problem: a request from the boonies (hard to match, no nearby drivers) could block requests from Manhattan (easy match, drivers everywhere). 

Partition the queue based on fine-grained geographic regions. This eliminates head-of-line blocking where easy matches get stuck behind hard ones.

**Additional benefit:** If a ride matching service instance goes down during the ~1 minute matching process, the request goes back on the queue (unacknowledged) and gets picked up by another instance. Built-in fault tolerance.

---

### Deep Dive 4: High Availability

Relatively traditional:
- **Horizontally scale** each service with their own load balancers
- **DynamoDB** scales largely indefinitely for the primary DB
- **Redis cluster** handles the location DB scaling
- **Split by region:** The entire setup isn't a single instance. Have separate deployments per region (Northeast, Southwest, Northwest, etc.) in different data centers
- For users who travel between regions: keep a read replica or copy of the user table in every data center

---

## Level Expectations Summary

**Mid-level candidate:**
- Get the high-level design right
- Answer probing questions about deep dives competently
- Landing on Postgres + PostGIS + queue for location: passing
- Cron job for consistency: passing

**Senior candidate:**
- Go deep in at least 2 places (location service + ride matching)
- Landing on the queue with PostGIS and quad trees is probably enough even without knowing the optimal geospatial index
- Should identify limitations of the cron approach even if not landing on distributed locks

**Staff candidate:**
- Higher bar, deeper in 2-3 places
- Expected to identify limitations and adjust
- Ideally teach the interviewer something
- Leverage personal experience with specific technologies
- Maybe go deep in places not even covered in this video
