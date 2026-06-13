## Requirements

### Functional Requirements

- Users should be able to **create chats and group chats** (a one-to-one is just a group of two; chat creation precedes any messaging)
- Users should be able to **send and receive messages within a chat** (sending to a chat delivers to all members; any message to a chat you belong to reaches you)
- Users should be able to **send media attachments** (images, audio, video) inside a chat
- Users should be able to **access messages received while their device was offline** (turn the phone off overnight, turn it back on, get everything missed)

### Non-Functional Requirements

- **Low-latency delivery, budgeted at 500 ms**: a chat is perceived like an in-person exchange. 100 ms vs 500 ms is not noticeable, but a few beats of delay feels broken. This 500 ms budget is the constraint we reuse to decide whether there is room for extra hops (load balancer, Redis bounce, two-hop server routing).
- **Guaranteed delivery (durability over the connection)**: a sent message must reach the recipient. Silently dropping is unacceptable. The guarantee comes from writing messages to durable server-side storage, not from the live socket being up.
- **Massive scale (billions of users)**: high throughput, hundreds of billions of messages a day. This is the defining challenge and it is what forces stateful, persistent connections instead of stateless request/response.
- **Do not store messages unnecessarily**: keep a message on the server only long enough to deliver it, then delete. Retained private data is a liability ("toxic sludge"). WhatsApp holds an undelivered message ~30 days, then drops it.
- **Fault tolerance**: a system this size has constant component failures. No single failure can take down the app.

### Out of Scope

- Audio and video calling
- Spam, abuse, and security hardening
- Contact scraping prevention
- End-to-end encryption internals
- Online/offline presence (covered as an extension deep dive, not a core requirement)

---

## Core Entities

- **User**: id, name. All users are peers, no privileged roles. Anyone can message anyone.
- **Chat**: id, name, metadata. The conversation container.
- **Message**: id, chatId, senderId, contents (text or media URL), timestamp. The chat server assigns the timestamp to keep ordering reasonably consistent.
- **Client / Device**: userId + clientId. The critical insight: a person is not offline, a *device* is. Your phone went dark but the laptop stayed on. Delivery must be tracked per device, not per user. This entity is what makes multi-device tractable.

---

## APIs

Delivery is real-time and bidirectional, so the transport is **WebSockets, not REST**. REST cannot push server-to-client. There is no standard for a WebSocket API, so we frame it as commands sent (client to server) and commands received (server to client).

### Commands sent (client -> server)

```
createChat    { participantIds, name? }      -> { chatId }
sendMessage   { chatId, contents }           -> { messageId, timestamp }
createAttachment { chatId, fileType, size }  -> { uploadUrl }   (pre-signed S3 URL)
modifyParticipants { chatId, add[], remove[] } -> { success }
ack           { messageId }                  -> (no response; deletes inbox row)
```

### Commands received (server -> client)

```
newMessage         { messageId, chatId, senderId, contents, timestamp }
chatCreated        { chatId, participants[] }   (you were added to a chat)
participantsChanged { chatId, add[], remove[] }
```

This is rough scaffolding, revisited as the design firms up. The lesson: flag where you are knowingly simplifying. Do not make an obvious omission silently, the interviewer assumes you missed it and scores it against you.

---

## High-Level Design

Build the simplest thing that satisfies the functional requirements first, on a **single-node chat server**, deliberately, to create the scaling problems we solve in the deep dives. Jumping straight to optimal leaves gaps and loses track of unmet functional requirements.

### Architecture Overview

The client opens a persistent **WebSocket connection** to the chat server. (Real WhatsApp uses a plain TLS connection to skip WebSocket overhead, same principle: a persistent connection to ferry messages both directions.) The chat server talks to a database. We use **DynamoDB**, but any key-value store or even a relational DB works.

Connection technology choice, from the real-time decision tree: not latency sensitive => long polling; server-push only => SSE; peer-to-peer audio/video => WebRTC. WhatsApp is latency sensitive (500 ms), needs frequent bidirectional messaging, and has no A/V in scope => **WebSockets**.

### Create Chat Flow

Two tables back chats. Two query patterns drive the keys:

- **Find all participants in a chat**: composite primary key on chatId, with participantId as the sort key.
- **Find all chats a user participates in**: a Global Secondary Index (GSI) on participantId, a fast reverse lookup without reorganizing the data.

### Send / Receive Messages Flow (single node, naive)

All clients hold WebSocket connections to the one chat server (e.g. ~1,000 connections). The server keeps an **in-memory hash table** mapping clientId to its WebSocket (client A -> ws1, client B -> ws2).

1. Client sends `sendMessage` with a chatId
2. Server queries ChatParticipant for the recipient IDs
3. For each recipient, the server looks up the WebSocket in the hashmap and pushes a `newMessage` command

**Why this is degenerate:** there is no durability. Only currently connected clients can be reached. It is a live chat room where nothing is stored. The moment a device is offline, the message is lost. We fix this below.

### Media Handling Flow

Naive: store blobs in a DynamoDB attachments table over the existing WebSocket. Broken twice over: DynamoDB is not built for large blobs (videos run hundreds of MB), and it shoves gigabyte payloads through chat servers tuned for tiny, rapid messages. The payload disparity (Grandma's video vs an "OMW" text) is the tell that something is wrong.

**Solution: pre-signed URLs.**
1. Client asks the chat server for an upload target via `createAttachment`
2. Chat server uses its credentials to request a pre-signed URL from **S3** (a URL with embedded auth and a TTL, usually ~1 hour)
3. Client uploads directly to S3, bypassing the chat server entirely
4. Client sends a normal `sendMessage` to the chatId containing only the S3 URL
5. Recipients receive the URL and fetch the payload directly from S3

This reuses the existing messaging path for tiny control messages. Expire media after delivery (~30 days) to reclaim space and stop users treating S3 like Google Drive.

### Offline Access Flow (durability)

Transient connections are not enough once a device can be offline. Add two tables:

- **Messages table**: messageId, contents, senderId, timestamp
- **Inbox table**: recipientId + messageId. One inbox row per recipient per undelivered message.

**Send with durability:**
1. Client sends `sendMessage` (chatId + contents) to its chat server
2. Server looks up participants via the ChatParticipant primary key
3. Server writes a **transaction**: one row in Messages (contents + timestamp) plus one Inbox row per participant. DynamoDB transactions cap at 100 records, so group chats are limited to ~99 participants to fit the message-plus-recipients write.
4. For participants currently connected, look up their WebSocket and push immediately

**Delivery tracking:** on receiving a message the client sends an `ack` with the messageId; the server deletes that Inbox entry so it is never resent.

**Reconnect:** when a client connects, the server reads all Inbox rows for that recipientId, fetches the corresponding message contents, pushes them, and each is acked and removed. Guarantee: messages are eventually delivered as long as the client periodically reconnects; if already online, delivery is immediate over the live socket.

All functional requirements are now met, but in a single-node degenerate form. Keep reminding the interviewer you know it does not yet scale, so they do not conclude you misunderstand scaling.

### Database Schema

**Chat table:**

| Column   | Type    | Notes                |
| -------- | ------- | -------------------- |
| chatId   | UUID PK |                      |
| name     | string  | nullable for 1:1     |
| metadata | JSON    | created, type        |

**ChatParticipant table:**

| Column        | Type   | Notes                          |
| ------------- | ------ | ------------------------------ |
| chatId        | UUID   | partition key                  |
| participantId | UUID   | sort key; GSI on this for reverse lookup |

**Messages table:**

| Column    | Type      | Notes                              |
| --------- | --------- | ---------------------------------- |
| messageId | UUID PK   |                                    |
| chatId    | UUID      |                                    |
| senderId  | UUID      |                                    |
| contents  | string    | text or S3 URL                     |
| timestamp | timestamp | server-assigned; secondary index for cleanup |

**Inbox table:**

| Column      | Type      | Notes                                  |
| ----------- | --------- | -------------------------------------- |
| recipientId | UUID      | partition key (clientId in multi-device) |
| messageId   | UUID      | sort key                               |
| timestamp   | timestamp | for time-based cleanup of stragglers   |

### Database Choice

**DynamoDB (or any key-value store).** The access patterns are simple and known up front: write a message plus a fan-out of inbox rows, read a user's inbox on reconnect, look up a chat's participants. No complex joins, no ad-hoc querying. We need very fast writes for throughput and very fast keyed reads, plus horizontal scale to hundreds of TB. The senior insight: the SQL vs NoSQL debate is a distraction. Relational databases do scale (Shopify reported MySQL doing millions of transactions/sec on Black Friday). What matters is identifying the required qualities: high write throughput, keyed lookups, single-digit-ms latency, and a transaction that can write a message and its inbox rows atomically.

---

## Deep Dives

Deep dives satisfy the non-functional requirements and evolve the design to scale. Two NFRs are already partly handled by the high-level design: low-latency delivery (immediate push over the socket) and guaranteed delivery (durable Messages + Inbox plus reconnect replay). **Scale is what breaks everything.**

### Deep Dive 1: Real-Time Delivery at Scale (Connection Scaling + Cross-Server Routing)

**The problem:** billions of users and availability concerns rule out one chat server. At ~2 million connections per server you need hundreds to ~1,000 servers. Two questions follow: which server does a client connect to, and how does a message reach the server that holds the recipient's socket.

**Scaling connections: a layer 4 load balancer.**
A layer 7 HTTP load balancer terminates each request and forwards it to any stateless web server, fine for stateless backends. WebSockets are connection-oriented and *stateful*: the connection must persist to one specific server. A **layer 4 (connection-oriented) load balancer** creates a symmetric TCP connection. When the client connects, the LB opens a matching connection to a chat server; when the client disconnects, the LB disconnects too. The LB becomes effectively invisible, as if the client connected directly to the chat server.

**Balancing policy: least connections.** The scarce resource is the open connection itself (capped ~2 million). A freshly added server has near-zero connections, so the LB routes new inbound connections to it until it evens out with the rest. This gives horizontal scalability.

**The routing problem this creates:** User A on chat server 1 cannot push to user B's socket, because B is connected to chat server 2. Chat servers must talk to each other so a message reaches whichever server holds the recipient's socket. Three candidate solutions:

**Option A, Kafka topic per user (the common instinct, wrong here).** One topic per user; chat servers subscribe to the topics of their connected users; to send, write to each participant's topic. Problems: Kafka is not built for billions of topics; topics are heavy (~50 to 100 KB each), so billions of users is terabytes of overhead just for partition setup; Kafka does not handle rapid connect/disconnect of short-lived micro topics. Wrong tool.

**Option B, consistent hash ring.** A user is predictably owned by a specific server, so any message for that user routes to that server, which relays it. Mechanics: drop the load balancer, expose chat servers via DNS, add a chat registry so a client can ask which server to connect to, and store the user-to-server mapping in a coordination store (**ZooKeeper or etcd**) synced across nodes. Send flow: client asks the registry ("you are on server 1"), connects, writes the message (also to Messages + Inbox); to reach B, look up B's server in ZooKeeper, server 1 sends directly to server 2, which checks its internal clientId-to-socket hashmap and pushes if B is connected. Two hops instead of one. Trade-off: scaling is an orchestration burden. Going 4 -> 5 servers keeps most users put but remaps ~20% on the edge. The event is signaled into ZooKeeper/etcd; servers slowly drain misassigned users, who reconnect via the registry. Drain slowly to avoid a thundering herd. During the window a target user may sit on either the old or new server, so a sender may have to send to both to be safe. Also risks hot, uneven servers.

**Option C, Redis Pub/Sub (the recommended synthesis).** Kafka's idea, externalizing inter-server communication, was good; Redis Pub/Sub delivers that benefit lightly. Mechanics: each chat server subscribes to a Redis topic per connected userId. Redis keeps an internal map of which sockets listen on a topic and on publish forwards to the listeners, a dumb socket relay. Send flow: when notifying recipients, the chat server publishes to the recipient's topic; Redis routes to the server owning that user; that server pushes over the WebSocket bound to the userId. Messages bounce through Redis to the right server, then the right client. **Trade-off accepted:** Redis Pub/Sub guarantees only at-most-once delivery (may deliver or may drop). Normally fatal, but acceptable here because durability already exists: messages are written to Messages + Inbox, and on reconnect (or via periodic poll) clients retrieve anything missed. Redis provides the lightweight sub-500 ms real-time path; the Messages/Inbox layer provides the guarantee. Remaining cost: scaling the Redis cluster reintroduces the same topic/connection orchestration, and topics spread across cluster nodes mean each chat server holds a connection to each Redis node (an n x m connection count that could bite at trillions of accounts).

**Level expectations:**
- **Mid-level:** knows WebSockets need stickiness, mentions consistent hashing or Pub/Sub without deep mechanics. Calling out the routing challenge is a bonus.
- **Senior:** explains why a layer 4 LB (not layer 7), least-connections policy, and lands on Redis Pub/Sub or consistent hashing with the routing flow.
- **Staff:** weighs all three options, articulates the at-most-once trade-off being safe *because* durability lives elsewhere, and reasons about the scaling-window dual-send and n x m connection cost.

---

### Deep Dive 2: Offline Delivery and Multi-Device Sync (Durable Messages + Inbox with Acks)

**The problem:** the live socket is transient. A device can be offline for hours, and a user can have several devices. Delivery must survive offline windows and reach every device, while never silently dropping a message.

**Solution: a durable Messages + Inbox model decoupled from the connection.** This was introduced in the high-level design and is the backbone of the guarantee. Recap of the mechanism: every send writes one Messages row (contents + server-assigned timestamp) and one Inbox row per recipient in a single transaction. Connected clients get an immediate push; disconnected clients leave their Inbox rows waiting. The client `ack`s each messageId, and the server deletes that Inbox row so it is never resent. On reconnect, the server replays the Inbox. The guarantee: as long as a client periodically reconnects, every message is eventually delivered.

**Multi-device:** the tables above are keyed on userId, which assumes one device per user. With multiple devices that breaks. Introduce the **Client entity (userId + clientId)** and re-key everything that was per-user to per-client: Inbox uses the recipient *clientId*, and Pub/Sub topics become per client. Send flow becomes: look up participants, then for each participant look up all their clients, then send to each client. Acks are now per device, so a message can be delivered-and-removed for the phone while still pending for the laptop.

**Trade-off:** this multiplies Inbox inserts (100 people x 5 devices is a large fan-out) and collides with the 100-record DynamoDB transaction limit. **Mitigation:** cap active clients per user (e.g. 2 to 3 devices), and percolate that limit down into the allowed group size so the per-message transaction stays under 100 records (e.g. ~33 members x 3 devices).

**Not storing messages unnecessarily (cleanup):** privacy is a liability and storage costs money; WhatsApp drops undelivered messages after 30 days. Add a **secondary index on the Messages timestamp** to find and delete messages older than 30 days. Inbox rows are deleted on ack already; add a timestamp field to Inbox so the same time-based cleanup sweeps stragglers. When deleting the last Inbox row for a message (all clients received it), also delete the Messages row. Race conditions are possible, but the 30-day guard rail means anything missed disappears soon. This cleanup is what keeps the live store at a few hundred TB rather than unbounded.

**Storage math (deferred until the design was concrete):** 1 billion users x 100 messages/day = 100 billion messages/day. At a 1 KB cap per message, that is 100 TB/day. Worst case x 30 days, but most messages deliver and are removed immediately, so the live database needs on the order of a few hundred TB. Large but achievable.

**Level expectations:**
- **Mid-level:** knows messages need durable storage and an inbox/queue, mentions acks loosely.
- **Senior:** designs the Messages + Inbox split, ack-driven deletion, reconnect replay, and the device-not-user insight for multi-device.
- **Staff:** reasons about the transaction-limit collision, capping devices and group size together, and the cleanup races bounded by the 30-day TTL.

---

### Deep Dive 3: Online Presence and Group Fan-Out

**The problem:** show a green orb for online contacts and nothing (or red) for offline. The hard part is not storing status, it is **fan-out**: a single user connecting or disconnecting must not trigger thousands or tens of thousands of notifications. This needs product clarification first: which users care about which users' presence.

**Simple approach (polling):** a status table of userId + status. On WebSocket connect, write status = available; on disconnect, write status = unavailable; query the table when you want a user's status. Cheap, eventually consistent, no push storm. Good enough for mid-level and for low-importance presence.

**Push approach (reuse Pub/Sub):** users subscribe to the presence of the users they care about. On connect/disconnect events, publish to that user's presence topic and push to interested clients. This reuses the exact same Redis Pub/Sub infrastructure built for message routing, so there is no new system to operate.

**Group fan-out, the real design problem:** the cost of presence and of group messaging is the fan-out factor. A celebrity or a large group multiplies one event into a flood. The mitigation is to **constrain the fan-out at the data model**: cap how many watchers a given user can have at once for presence, and cap group size (already bounded by the 100-record transaction limit and the device cap from Deep Dive 2). For group messages, the fan-out is the per-recipient Inbox write plus the per-connected-device push; bounding membership bounds both. Where fan-out is genuinely large, presence can be downgraded to lazy/polling for the long tail of watchers and push only for active conversations.

**Level expectations:**
- **Mid-level:** a polling status table, aware that fan-out is a concern.
- **Senior:** the Pub/Sub push reuse and group fan-out via the Inbox write plus connected-device push.
- **Staff:** frames the whole thing as a fan-out constraint problem, bounds watchers and group size at the model, and proposes degrading presence to polling for the long tail.
