Source: [YouTube](https://www.youtube.com/watch?v=fhdPyoO6aXI), Transcribed: 2026-04-05

---

## Introduction

This is the first in a series of system design breakdowns. The question: **design a ticket booking service like Ticketmaster**. This is asked frequently at Meta (particularly in their "product design interview") and across other top companies.

The presenter spent five years at Meta as an interviewer and staff engineer, and is now co-founder of Hello Interview, a site that helps candidates prepare via mocks with senior FAANG engineers and managers. Between asking this question at Meta and in mocks via Hello Interview, he has asked it well over 50 times, and has seen exactly where candidates of all levels do well and where they trip up.

The walkthrough follows the same structure as a real interview, with periodic tips, frameworks, and lessons learned from those many mocks. A detailed written breakdown of this question is also available on the Hello Interview website, along with breakdowns of other common questions.

---

## Interview Roadmap

This is the suggested roadmap for any system design interview, particularly those designing user-facing products like Ticketmaster:

1. **Requirements**: functional requirements (features of the system) and non-functional requirements (qualities of the system)
2. **Core Entities**: the data that is persisted and exchanged throughout the system
3. **APIs**: the user-facing endpoints
4. **High-Level Design**: a simple design that satisfies the functional requirements
5. **Deep Dives**: a conversation with the interviewer going deeper into satisfying the non-functional requirements

The interviewer might lead the deep dives depending on your level, but this is the plan to follow section by section.

---

## Functional Requirements

Functional requirements are the features of the system. They are usually statements like "users should be able to." When you get here, hopefully you have had some experience with the system in the past. They usually choose really popular systems. If you have not used it, ask the interviewer a lot about the system: what does it do, what is the most important functionality, what are its features, how do users use it, etc. Once you have a good sense, list the **core** features, the ones most necessary to make this system work.

For Ticketmaster, the top three functional requirements are:

1. **Book tickets**: the most important core action
2. **View an event**: the event page, seat map, choosing a seat
3. **Search for events**: discovery and filtering

You can walk backwards through the user flow to derive these. A user searches for an event, sees a dropdown list of events, clicks on one of them (which takes them to an event page), and from there they book a ticket to that event. These are usually the functional requirements that most candidates land on, and the ones the interviewer pushes toward if the candidate needs help.

---

## Non-Functional Requirements

Non-functional requirements are the qualities of the system. They are not features, but properties like scalability, availability, reliability, fault tolerance, all the things you have read about in the books and resources.

**The biggest mistake candidates make** is that they just write those terms. They write "availability" and "scalability" and whatever it may be, all of these "-ilities." This is not always strictly wrong, but it defeats the purpose. All systems have those qualities. The important part of non-functional requirements is to **identify what makes this system unique, interesting, and challenging.** You should go through those "-ilities" in the context specifically of this problem.

### CAP Theorem: Consistency vs. Availability

The first question to ask yourself is about CAP theorem. Is the system going to prioritize availability or consistency?

The easy right answer, particularly for a mid-level candidate, is that we are going to prioritize consistency more than availability. The reason is that we need to make sure that **no ticket is assigned to more than one user**. No double booking. For any given ticket, only one user can sit in that seat. Consistency is really important for that.

However, a more nuanced candidate, a senior-level candidate, would realize that **these two things can coexist in different parts of your system**, in different microservices and different parts of your system architecture. The amended answer:

- **Strong consistency for booking tickets**: when a user in Germany buys a ticket that you are viewing in America, you need to know instantly that they booked it, or get an error because you cannot book it anymore
- **High availability for searching and viewing events**: it does not really matter if an event was just added and users do not immediately see it within a couple of seconds

### Read-Write Ratio

Ask yourself about the read-write ratio. Is there anything unique there? In this case, **reads are much greater than writes**, probably around 100:1 (maybe even 1,000:1), if the conversion rate for booking tickets is maybe around 1%. There are going to be a lot more people searching and viewing events than there are actually buying. This will have consequences on the design later on.

### Scalability to Handle Surges from Popular Events

Think about how the site is used, what the query access pattern is: the frequency, consistency, and irregularity with which requests hit the system. People do not book tickets to events all that much. It is kind of regular, even consistency, until you have really popular events. When Taylor Swift's tour is about to go live, or the Super Bowl, or the World Cup, all of a sudden you have tens, maybe even hundreds of millions of people at your front door trying to get the same ticket.

So in the context of scaling, this is an example where you would not just write "scalability." Instead: **scalability is important specifically to handle surges from popular events.** We need to design with that in mind.

### Out of Scope

There is a long list you can keep going down for non-functional requirements. It is important that we do not lose data, that we remain compliant with GDPR, etc. But if all of that comes to mind, note it **below the line** as out of scope: GDPR compliance, fault tolerance, etc.

Once you have done this, say to the interviewer: "These are what I am going to prioritize. Here is what I have considered out of scope. Would you like me to reprioritize any of this? Is there anything from down here you would like me to move up?" This is a nice, elegant way to check in, make sure you are on the same page with the interviewer, and it shows them that you have larger product thinking. You can think about all of these things necessary in designing a system, but you also remain focused on what really matters for this particular system.

---

## Core Entities

The next step is to define the core entities and the API. These usually come hand in hand. You usually will not spend more than about two minutes on core entities and up to five on APIs. The purpose of core entities is to get an understanding of what data is persisted in your system and exchanged by the APIs. You will use these to build your APIs and your high-level design.

The core entities of a system like Ticketmaster:

- **Event**: admins add these events (adding events is out of scope, we focus on the user flow). Events need to be hosted somewhere.
- **Venue**: like a stadium, where the event is hosted
- **Performer**: who is performing at the event
- **Ticket**: all the tickets for a given event, so we can determine whether they are available, who has purchased them, their price, etc.

You can mark down what all of their fields would be (name, description, etc.) if you know them at this point. The recommended approach is to just stick to the core entities and tell the interviewer: "I am not going to detail the key fields and columns yet because I do not quite know them yet. I am too early in my design. They are going to evolve naturally." Get a clear sense of what the core entities are, then as you move into the high-level design, be more explicit about exactly the fields that matter.

---

## APIs (REST)

These are strictly the user-facing APIs. The APIs that the client is going to make in order to satisfy the functional requirements. Look back at your functional requirements and create an API (or in some cases more than one) to satisfy each requirement. They should exchange, return, and take as input the entities or properties/fields of those entities. Use REST in these interviews. In most cases, though, you should consider other options, GraphQL being the main alternative.

### View Event

```
GET /event/{eventId}
-> Returns: Event, Venue, Performer, List<Ticket>
```

Users pass in an event ID, and they get back an event object, information about the venue, information about the performer (everything needed to render a page about this event), and a list of tickets so we can render the seat map (what tickets are available, where each seat is, etc.). Very simple.

### Search Events

```
GET /search?term=...&location=...&type=...&date=...
-> Returns: List<PartialEvent>
```

The search endpoint takes in a search term (free text), a location (could be lat/long, abstracted as "location" for now), a type or category (sporting event, music, etc.), date ranges, and other optional query params.

It returns a `List<PartialEvent>` (pseudo code inspired by TypeScript). The reason it is "partial" is that we only return a limited amount of information from the event, like the name, description, performer, just enough to show search results. You click on those search results and hit the view event API endpoint for full detail.

### Book Ticket (Two-Phase Process)

Booking is the most interesting API. It is important to notice that **booking is actually a two-phase process.** If you have ever used Ticketmaster or bought an airline ticket, you see a seat map (or airplane map), choose a seat, then go to a second phase where you actually purchase the ticket. In that second phase, you usually have a timer or countdown (maybe 10 minutes) to actually purchase the ticket. For those 10 minutes, the ticket is reserved for you. You click on a ticket, it gets reserved, you then have 10 minutes to actually book it. If you do not book it, that ticket goes back to available.

In an interview, some candidates know this because of personal experience, which is awesome to see. It is not a requirement though. If a candidate writes a single endpoint for booking a ticket, the interviewer will point out that it is a two-phase process, and they will amend accordingly.

**Reserve endpoint:**

```
POST /booking/reserve
Body: { ticketId }
```

There are variations where you might reserve multiple tickets (multiple seats), but we keep it simple: a single seat associated with a ticket, and you get the ticket ID as input to reserve it.

**Important security note:** There is no `userId` in the body. This is on purpose. Some candidates put userId in the body, which is a security concern. You would not post a userId in the request body because it could be altered. Someone could come in and post a reservation on behalf of somebody else, so long as they knew that userId. Instead, **user information is kept in the header, either via JWT or a session token.** This is nice to note in the interview, it shows technical excellence, but do not spend too much time here.

**Confirm endpoint:**

```
PUT /booking/confirm
Body: { ticketId, paymentDetails }
```

The header has the JWT. The body has the ticket ID (which one we are confirming) and payment details. We offload payment to Stripe, a third-party payment service. Stripe has things called payment intents, which use common client libraries (React, raw JavaScript, etc.) to get payment information, which is posted back to your server.

Maybe this is not a POST because we are not creating a new entry. Maybe it is a PUT or a PATCH respectively, but that is not the most important distinction.

So we have two endpoints for booking a ticket: the first to **reserve**, and the second to **confirm**.

---

## High-Level Design

At this point, you should be about 15 minutes into the interview, which leaves about 20 minutes for the high-level design and deep dives, give or take. Depending on your level, maybe it takes a little longer to get here, and that is totally fine.

The high-level design's goal is to create a **simple design that satisfies the three functional requirements.**

### Microservices Architecture and API Gateway

We opt for a microservices architecture. This is by far the most common setup in these types of interviews. If you are not sure which architecture to go with, microservices is probably the right call.

For this reason, we have an **API Gateway.** The API gateway's main responsibilities:

- **Routing**: takes incoming API requests and routes them to the correct microservice (most important)
- **Authentication**
- **Rate limiting**

We build up the high-level design by going one by one through the API requests. The API requests map back to the functional requirements.

### Satisfying "View Event"

When the client has a GET request to `/event/{eventId}` to view an event:

1. Request hits the API Gateway
2. API Gateway routes to the **Event CRUD Service** (responsible for creating, reading, updating, and deleting events, though most CRUD operations are out of scope for this problem, we are just handling the view path)
3. The service reads from the **database**

### Database Schema

The database stores the core entities:

**Event table:**
- ID
- venue_id (FK)
- performer/team
- name, description, and other metadata
- One-to-many relationship with tickets (foreign keys to ticket IDs)

**Venue table:**
- ID
- location
- seat_map

**Performer table:**
- ID
- (other fields, less important)

**Ticket table:**
- ID
- seat (the location)
- price
- event_id (FK)

### Database Choice: Postgres (SQL)

We talked about consistency being important for tickets in particular. There are some decent relationships between this data (one-to-one, one-to-many). Going with **Postgres**, a SQL database, because:

1. It is one used frequently
2. It satisfies requirements for ACID properties on tickets, allows for transactions
3. Good for SQL queries with mild relationships

**Important senior insight on SQL vs. NoSQL:** A NoSQL database would have been fine here too. You could have chosen DynamoDB. In interviews, NoSQL vs. SQL is kind of an old debate. It is not that interesting. What is more interesting is the **qualities of the database that you need.** The reality is most things a SQL database can do, a NoSQL database can do nowadays, and vice versa. You can have ACID properties on DynamoDB, for example.

It actually shows a candidate's seniority when they understand this is not a relevant debate. Many mid-level candidates go into SQL vs. NoSQL and try to break all of it down. Whereas the more senior candidates just say: "Here are the qualities of the database I need. Either would have worked. I am going to go with Postgres because it is the one I am most familiar with, and it will do just fine for the job." Then move on.

This is the appropriate time to map out the fields and columns. They typically evolve during the design.

### Satisfying "View Event" Flow

Coming back to the GET request: a user wants to view an event, so they hit the Event CRUD Service. We get the event details, the venue and the performer from a join, as well as the tickets that are available, and return that back to the client. Very simple. That satisfies the first API endpoint.

### Satisfying "Search Events"

Add a **Search Service.** For now, in the high-level design, make this as simple as humanly possible. A user searches for something based on term, type, date, etc. This can just be a SQL query:

```sql
SELECT * FROM events WHERE type IN (...) AND name LIKE '%term%'
```

This would work. **But it totally sucks and is incredibly slow.** The wildcards mean we need to scan the entire database (full table scan) to see if any names match whatever term was inputted. That is not going to cut it.

But for now, in the high-level design, leave it like this. You might even say in the interview: "This is not going to cut it. I am going to come back and optimize this once I have satisfied all of my functional requirements first."

### Satisfying "Book Ticket" (Two-Step Booking Flow)

Add a **Booking Service.** Two-step flow: reserve a ticket, then confirm the purchase.

**Reserve flow:**

1. Reserve request comes in to the Booking Service with a ticket ID
2. Update the database: look up that ticket ID row, update a new **status** column
3. Status values: `available` | `reserved` | `booked`
4. Set status to `reserved`
5. Return success (200) to the client

**Confirm flow:**

1. Confirm request comes in with ticket ID and payment details
2. Call out to **Stripe** (third-party payment processor). In almost all cases, you can abstract away the payment unless the interview is specifically for a payment team or requires designing a payment system.
3. Post payment information to Stripe
4. Stripe handles payment **asynchronously**: it calls out to credit card companies, determines whether it can be paid for (happens quickly, but is async)
5. Stripe does not respond to the single request. Instead, it calls back via a **webhook** to a registered callback URL
6. You have an endpoint in the Booking Service exposed for Stripe to call back to
7. If the response is that payment was successful: update the ticket status in the database to `booked`, also assign a `user_id` to record who booked it
8. Now the ticket is no longer available, it is assigned to that user. Maybe we send them an email (out of scope).

### The Reservation Expiry Problem

There is something wrong with this two-phase booking process. If a user clicks on a seat and goes to the payment page with the 10-minute countdown, what happens if 10 minutes is exceeded? What happens if they close their laptop and decide they do not actually want the ticket?

In the current design, the status would stay **reserved forever.** When we show users the seat map, we query the database for tickets that are available, which excludes reserved tickets. That seat would basically be infinitely reserved for that user. This is wrong and does not meet the requirement that reservations expire after 10 minutes.

**Solution 1: Reserved Timestamp (mid-level approach)**

Add a `reserved_timestamp` column to the ticket table. When reading the database to see what is available, the query becomes:

```sql
SELECT * FROM tickets WHERE status = 'available'
OR (status = 'reserved' AND reserved_timestamp < NOW() - INTERVAL '10 minutes')
```

This absolutely works. The **downside** is that the database and data model become confusing. You have a status of "reserved" while things are not actually in a reserved status. You need to keep the status and timestamp consistent with one another.

**Solution 2: Cron Job (mid-level passing approach)**

Introduce a cron job that runs every ~10 minutes. It is responsible for:

1. Querying the database for every ticket in a reserved status
2. Checking the reserved_timestamp
3. If more than 10 minutes have passed since the reserved timestamp, set the status back to available

This works and is a valid approach. **For mid-level candidates, this is a passing approach** for the interview.

For senior, staff, principal, and beyond, this is not enough. The reason: there is a **delta (N minutes)** between the time when a ticket should have been unreserved and the time when the cron job ran. If the cron job runs every 10 minutes and a ticket was supposed to be unreserved at noon, but the cron job did not run again until 12:09, then N = 9. There were 9 minutes where the ticket should have been available but was reserved. The ticket was reserved for 19 minutes, not just 10 as expected.

We need something more real-time.

**Solution 3: Distributed Lock with Redis (senior/staff answer)**

Get rid of the cron job, the reserved timestamp, and the reserved status entirely. Instead, introduce a **distributed lock** using Redis (or any in-memory cache).

How it works:

- When a ticket gets reserved, instead of updating the ticket table at all, keep track of it in Redis
- Store a key-value pair: `ticket_id -> true` with a **TTL of 10 minutes**
- After 10 minutes, the key-value pair is immediately and automatically deleted from Redis

**Reserve flow with the lock:**

1. User tries to reserve a ticket (first API request)
2. Do not write to the database at all
3. Simply put that ticket in the lock: set `ticket_id` with TTL of 10 minutes in Redis

**Viewing available seats (Event CRUD Service):**

1. Query the database for all tickets with status `available`
2. For each of those ticket IDs, look them up in Redis to see if they are reserved (locked)
3. If a ticket is in Redis, remove it from the list of available tickets
4. Send the filtered list back to the client

**Expired reservation flow:**

If the user closed their laptop before confirming payment, the Redis key expires immediately at 10 minutes. If another user at 10 minutes and 1 second (or 10 seconds, or whenever) queries for the seat map and available tickets, when they cross-reference with the ticket lock, that ticket ID is no longer there. The ticket is available and shown to the client for them to book.

This is a super easy, elegant solution using a distributed lock.

**Why distributed?** The reason we use a distributed lock as opposed to keeping this in memory in the Booking Service is because there will be **multiple instances** of the Booking Service. This is not a single machine or compute resource. It is going to horizontally scale, and all instances need to have the same consistent, singular view of the lock. That is why we separate it out as its own in-memory cache.

**Confirmed purchase flow:**

When the purchase is confirmed (payment succeeds), update the DB status to `booked` and assign the user_id.

### What If Redis Goes Down?

If the lock goes down:

1. Immediately detect it and bring a new one up
2. Any users that reserved a ticket in the last 10 minutes lose their reservation
3. For a 10-minute window, several users could go to a payment page and try to book the same ticket
4. Because this is a Postgres DB with ACID properties on the write to `available` or `booked` (one write needs to complete before another can read), whoever submits the purchase first wins
5. The other users get an error

This is a **bad user experience** for those users in that 10-minute window. This is a conversation to have with the product team: is it okay that in the unlikely event of a disaster where the lock goes down, we will have a small 10-minute period where we will not lose our consistency guarantees, but users will have a bad experience? The answer is probably yes, this is fine.

---

## High-Level Design Summary

At this point, the high-level design satisfies all functional requirements. It is not perfect. It does not scale. Search is not great. All of that is handled next in the deep dives.

---

## Deep Dives

This is where senior and staff candidates really earn their keep. If you are a mid-level candidate, what you have on the board already might be passing, especially if you got the Redis lock. Most mid-level candidates do not get that far; most land on the cron job solution. But you are close if you are a mid-level candidate. Your interviewer might ask about scaling or search being slow. Answer those questions well and you probably have it in the bag.

For senior and staff candidates, this is where you show off your chops, that you can go deep. Your goal should be to find **one to three places** where you can demonstrate depth. These are not the only places and not necessarily what the interviewer is explicitly looking for. It is up to you to decide where you lead the conversation.

The process: reference your **non-functional requirements**, look at them, and see what is missing. That should inform where you go next with your deep dive.

---

### Deep Dive 1: Low-Latency Search

We talked a lot about how search was not optimized. This was something originally missed in the non-functional requirements that was realized while designing the system. It is totally okay to go back and edit your non-functional requirements during the interview.

**The problem:** The current solution is slow because we do a full table scan on a query with wildcards. That is not going to cut it.

**The solution: Elasticsearch**

The common solution to search problems like this is to introduce a search-optimized database. A very popular one, and the recommended one for interviews, is **Elasticsearch.**

Elasticsearch builds an **inverted index** to make searching documents by terms really fast. Here is how it works:

1. An event has text for its name, description, and other fields
2. **Tokenize** that text into terms: for example, "The Philadelphia Eagles are playing in a wildcard matchup against the Broncos" becomes terms like "Philadelphia," "Eagles," "Playoff," "Wildcard," etc.
3. Map those terms in a hash map to the documents (events) they appear in. For example, the word "Playoff" shows up in Event 1, Event 2, Event 3. The word "Swift" (as in Taylor Swift) shows up in Event 5, Event 6, Event N.
4. Now you have a really quick lookup: if someone searches for "Playoff," instantly return all events mentioning Playoffs and show the relevant events based on the search term

This can be combined across name, description, and other fields. Elasticsearch also has support for **geospatial queries**, using a combination of quadtrees and geohashing. So you can search for location, terms, and dates at the same time, and it uses varying indexes (inverted indexes, geospatial indexes) to make it as quick as possible.

Delete the old SQL search approach and instead **search using Elasticsearch.**

### Keeping Elasticsearch in Sync

How do we get data into Elasticsearch? How do we make sure that data is consistent with what is in the primary database?

**Important: Do not use Elasticsearch as your primary data store.** This is due to durability concerns and no support for complex transaction management. (The presenter used Elasticsearch as a primary data store for a first startup and learned the hard way that it did not work out well, from firsthand experience.)

So we need a way to make sure that if anything changes in the primary database, that change gets propagated to Elasticsearch. Two approaches:

**Option 1: Application Code**

Anytime an event is added, write it to Postgres DB and also write it to Elasticsearch. This puts some complex logic in the application code because you need to handle: what happens if one write fails, do you retry, do you reverse the first write, etc. Depending on product requirements, this is a viable solution.

**Option 2: Change Data Capture (CDC)**

CDC is a process by which changes to a primary data store are put onto a stream, and those change events are consumed so that something can be done with them. In this case, anytime something changes in Postgres, the change event goes on a stream, a worker consumes it and updates Elasticsearch with that change.

In interviews, this is often abstracted to just a line between Postgres and Elasticsearch. Technically this is a large abstraction (there is a stream, there is a worker that does the write), but it is often good enough in the interview. You might want to clarify that it is an abstraction. CDC is a common pattern in interviews.

**Write volume to Elasticsearch:** Be aware that Elasticsearch has a limit on the number of writes per second because it is updating indexes on each write. For systems with a lot of updates to Elasticsearch, you need something smarter like a queue or batching. But in Ticketmaster's case, events, venues, and performers hardly ever change. They are hardly ever added. Maybe at most an admin adds tens, hundreds, maybe even thousands a day, but that is absolutely nothing. So we do not need the queue. We can just update Elasticsearch on each change to the primary database.

### Making Search Even Faster: Caching

The interviewer might ask: what about popular queries? What if everybody is searching for Taylor Swift? How can we make that as quick as possible?

The answer is usually **caching.** An important thing to recognize: in this system, we are not doing any ranking or personalized recommendations. If two users search for the same thing, they get the same result. This is very important for caching.

**Option 1: OpenSearch Node Query Caching**

If using AWS OpenSearch (a fully managed Elasticsearch cluster), it supports **node query caching.** This is a cache on each instance of the Elasticsearch cluster (each shard) that caches the top 10K queries to that shard in a **least recently used (LRU) cache.** You can enable it via the config. Quick, dirty, easy, and works great.

**Option 2: Redis / Memcache**

Add a Redis or Memcache layer. Cache the search term (or some normalization of it) along with the search results. You need to make sure you invalidate appropriately when updates are made.

**Option 3: CDN Caching**

Your system probably already has a CDN for static images (out of scope for this problem, but most systems have it). The CDN can **cache API calls** and their results. Usually when you cache an API endpoint in a CDN, it is for a short period of time, 30 seconds to a minute. If a lot of people are searching for the same exact search term, return results immediately by hitting the CDN, which is geographically located close to them. Super fast.

**Pros:**
- Wicked fast
- Great for super popular events in particular

**Cons:**
- Becomes less useful the more permutations you have of the search query. We already have type, date, location. If location is lat/long, that has too much precision and two users would never hit the same cache. But if it is something like "San Francisco," maybe small enough for cache hits. The more query params, the less likely you get cache hits and the more you waste space in the CDN.
- If the system evolved to give **personalized recommendations,** CDN caching would not work, because everyone searching with the same API call would get the same results, which would not be true anymore.

All of these are the sorts of things you can mention in the interview. It is impressive to throw some of these out if they are contextually relevant.

---

### Deep Dive 2: Scalability for Popular Events (Real-Time Seat Maps and Virtual Waiting Queue)

Looking back at the non-functional requirements: scalability to handle surges from popular events.

**The stale seat map problem:**

Taking a step back and focusing on the user experience. When a user comes to the website and clicks on an event, they see event details and a seat map showing available and booked seats. In the current system:

1. Query the Event CRUD Service for event, venue, and performer data
2. Query for tickets with their available or booked status
3. Cross-reference with the Redis lock: anything in the lock moves from available to reserved/booked so the client knows it cannot book it
4. Return all of that to the client

The issue: the API call loads an accurate representation on the client. But **after 1 second, 2 seconds, 5 seconds, 5 minutes, 10 minutes, it grows stale.** Users can click on seats that appear available but are no longer available. We have to immediately give the user an error, which is a really bad experience. For popular events, this happens a lot because many people are buying tickets, so it goes stale really quickly.

### Real-Time Seat Map Updates

Make the map real-time: any time a ticket becomes reserved or moves to booked, update the client to mark that seat in real time as no longer available.

**Option 1: Long Polling (simplest)**

The client opens/sends an HTTP request, and that request is kept open for usually 30 seconds to a minute for the server to respond. This happens in a while loop: keep long polling so the server can keep sending things back, keeping the seats updated.

- Super cheap, easy to implement, requires no additional infrastructure
- **Best for:** users who are on the page for a short time (1 to 5 minutes)
- If analytics show users sit on these pages for a long time (5, 10, 20, 30 minutes, hours), a more sophisticated approach is needed

**Option 2: Server-Sent Events / SSE (more sophisticated)**

A persistent connection between the client and the server such that the server can send information to the client whenever it wants, as long as the connection is open.

Your mind might go to **WebSockets**, and that would be an option. WebSockets are a bidirectional persistent connection. But instead, **SSE (Server-Sent Events)** is a better fit here. The key difference between WebSockets and SSE: WebSockets are fully bidirectional, SSE is **unidirectional** (server to client only). That is all we need. We only need the server to tell the client that new seats have been taken.

Set up SSE persistent connections between the API Gateway, the Event CRUD Service, and the client. Every single time there is a change to the status (available, booked, or reserved), push that change to the client. The implementation is a bit more complex and probably out of scope for the interview, but that is the degree you would probably go into.

### The Taylor Swift Problem: Virtual Waiting Queue

The interviewer might point out (or you would notice proactively) that real-time updates are great, but when Taylor Swift, the Super Bowl, or the World Cup comes around, the user experience is: they get to the page and **it immediately goes black.** They see all the available seats and then within milliseconds everything gets booked, because there are a hundred thousand or a million people fighting for the same ten thousand to a hundred thousand seats. Terrible UX.

**The solution: a virtual waiting queue.**

We need to introduce a choke point to protect backend services and improve the user experience.

How the virtual waiting queue works:

- **Admin-enabled** for really popular events. There is a config and an admin determines which events should have a virtual waiting queue.
- A million people try to buy Taylor Swift tickets. Instead of seeing the event detail page, they enter a **waiting queue** and get a message: "Thanks for your interest, you are in the queue, we will let you know when you are out."
- The queue implementation uses **Redis** (cheap, lightweight). Use a **Redis sorted set** so it is a priority queue based on arrival time. Other implementations make this random for fairness (so it is not just users closest to company servers who get in first).
- **Event-driven batching logic:** once 100 seats are booked, let the first 100 people in. Once the next 100 seats are booked, let the next 100 (or 1,000, whatever it may be).
- Pull those users off the virtual waiting queue. Assign them a token, put their user ID or session info into the system.
- **Notify users** via the same SSE connection that they are ready to go, then that user can be let in and book.

This is a really nice example where **the solution is simple but sophisticated.** It shows that the best answer is not always the most technically complex, but instead solves the problem in a simple and maybe creative way. The virtual waiting queue is great.

---

### Deep Dive 3: General Scaling

Looking back at the non-functional requirements:

- **Strong consistency for booking tickets**: already covered in the functional requirements section when dealing with booking (introduced the Redis lock), so that is handled
- **High availability for searching and viewing** and **read-to-write ratio** heavily favoring reads: this is where you might get standard scaling questions, or you proactively talk about it

As an interviewer, these general scaling discussions are usually the **least interesting.** Here is what you would typically say:

**API Gateway scaling:**
- Use AWS API Gateway, which is managed
- It has its own load balancers and auto-scales

**Service scaling:**
- Each microservice has its own load balancers
- Dynamically scale horizontally based on memory consumption or CPU consumption

**Database scaling and sharding:**
- This would be an appropriate time to do some math (see below on back-of-envelope philosophy)
- Do math to see what the storage is in the Postgres DB, to determine whether we need to shard or not, or if it fits into a single Postgres instance
- If you conclude that sharding is needed, discuss **shard key candidates:**
  - **event_id**: the majority of queries use event_id
  - **venue_id**: if sharding and distributing shards geographically, and there is high correlation between people searching for events in venues close to them, this could make sense
- No right or wrong answer; weigh the pros and cons, discuss with the interviewer

**Redis caching for read-heavy data:**

Given that reads are so much higher than writes, and event, venue, and performer data never changes (or very infrequently changes), they are great candidates to cache aggressively. Add a **Redis cache:**

- Cache events, venues, and performers in Redis
- If updates are made to the database, invalidate or update the cache
- There does not need to be an eviction policy (LFU or LRU) because we will probably fit them all in Redis, or just cache events that are upcoming (within the last four months and the next two years, whatever bounds make sense)
- Cache a key-value pair of `event_id -> { event, venue, performer }`
- Only ticket data is dynamic, so we do not cache tickets, only the static event/venue/performer data needs to hit the DB for tickets

This makes the view API call (`GET /event/{eventId}`) **extremely fast** because we can serve event/venue/performer from cache and only need to query the database for tickets.

---

## A Note on Back-of-Envelope Math

Astute watchers might notice that no back-of-the-envelope estimations were done after the non-functional requirements. This is on purpose.

Most candidates do back-of-the-envelope estimations at that point: QPS, daily active users, storage. At the end, they go "Wow, okay, it is a lot, so it is going to be a big system," and then keep going. **This is useless.** The interviewer did not learn anything about the candidate. The candidate did not learn anything that would inform their design. They were just checking a box. This is **math without a purpose.**

Math is good, but the recommendation is: **only do calculations if the result of the calculations will have a direct influence on your design.** The right time to do that is either in the high-level design or in the deep dives.

For example:
- "Do I need to shard?" Do the math on storage, make a determination based on the result.
- "Will this fit in a single Postgres instance?" Do the math, then act on it.

Math should **drive design decisions**, not check a box.

---

## Conclusion

When you conclude, you should be able to look at your design concretely and answer:

1. **Does this satisfy all of my functional requirements?** (search, view, book)
2. **Does it satisfy all of my non-functional requirements?** (strong consistency, high availability, low-latency search, scalability for surges)

If you can say yes to both, you should feel confident about the interview.

---

## Level Expectations

- **Mid-level**: the high-level design plus the cron job solution for reservation expiry is likely passing. If you got the Redis lock, that is overkill for mid-level by far.
- **Senior**: need the Redis lock, Elasticsearch, and at least one solid deep dive. This design definitely passes a senior interview.
- **Staff / Principal**: all of the above plus the virtual waiting queue, real-time seat map updates (SSE), nuanced scaling discussion, and strong trade-off analysis. Depending on execution and how well you answer questions and show depth in other places, this design passes a staff interview as well. Principal is usually evaluated at the same level as staff.
