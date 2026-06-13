Source: Hello Interview, "Design WhatsApp / Messenger" problem breakdown, presented by Stefan (co-founder of Hello Interview, ex-senior manager at Meta and Amazon, 20+ interviews conducted).

The problem is to design a chat application (WhatsApp / Messenger) that lets users hold one-to-one and group conversations, send text and media, and reliably receive messages even after their device has been offline. The core challenge is real-time, bidirectional, guaranteed message delivery at the scale of billions of users, which forces the design away from stateless request/response toward stateful, persistent connections. The hard parts are routing a message to whichever server currently holds the recipient's live connection, surviving device offline windows, and keeping per-user durable state without storing messages a moment longer than needed.

The presenter walks the standard Hello Interview delivery framework: Requirements, Core Entities, API, High-Level Design (satisfy functional requirements simply, single node first), then Deep Dives (satisfy non-functional requirements, evolve to scale). Mid and senior candidates should follow it closely; staff candidates can skip the basic build.

## Requirements

### Functional

Derived by putting yourself in the end user's shoes (open the app, what do you see, what must exist for that to be true).

1. Users can create chats / group chats. Group is the general case; a group of two is a one-to-one. Chat creation must precede messaging.
2. Users can send and receive messages within a chat. Sending to a chat delivers to all members; any message to a chat you belong to reaches you.
3. Messages support media attachments (video, audio, images), confirmed in scope with the interviewer.
4. Users can access messages received while their device was offline. Turn the phone off overnight, turn it on, get everything missed.

Kept deliberately short. Below the line / out of scope unless time allows: audio and video calling, online/offline presence (treated as an extension at the end), spam and security, contact scraping prevention. Lesson: do not waste time enumerating things you will not build; ask the interviewer if they have anything in mind, then move on. Over-expanding scope creates time problems later.

### Non-Functional

Stated as system qualities, quantified where possible.

- Low latency delivery, budgeted at 500 ms. Reasoning: a chat is perceived in person; a few beats of delay feels slow, but 100 ms vs 500 ms is not noticeable. The 500 ms budget is reused later to decide whether there is room for extra hops (load balancer, Redis bounce, two-hop server routing).
- Guaranteed delivery. A sent message must reach the recipient; silently dropping is unacceptable. Achieved by writing messages to durable server-side storage, not by relying on the live connection.
- Scale: billions of users (WhatsApp is a couple billion). Implies high throughput and many messages. The exact message count is deferred until the design is concrete enough to estimate (no premature back-of-envelope math).
- Do not store messages unnecessarily. Keep a message on the server only long enough to deliver it, then delete. Privacy framing: data is "toxic sludge," a liability for a private app, so delete or encrypt beyond your own reach. WhatsApp keeps an undelivered message ~30 days, then drops it.
- Fault tolerance. A gigantic system has constant component failures; individual failures must not take down the app.

Below the line: spam/security, scraping.

### Scaling numbers cited

- Billions of users.
- 500 ms latency budget.
- WhatsApp served ~2 million connections per chat server (presenter notes modern hardware could push higher); implies hundreds to ~1,000 chat servers.
- Storage estimate: 1 billion users x 100 messages/day = 100 billion messages/day. At 1 KB cap per message = 100 billion KB = 100 trillion bytes = 100 TB/day. Worst case x 30 days, but most messages deliver and are removed immediately, so the live database needs on the order of a few hundred TB. Large but achievable.

## Core Entities

Not explicitly graded, but getting them wrong cascades into a wrong data model and API. Process and final design are what get evaluated.

- Actors: all users are peers. No privileged roles (unlike Uber's riders/drivers or YouTube's creators/viewers). Anyone can message anyone.
- Chat: the conversation container.
- Message: text or media within a chat.
- Client / Device: critical insight that a person is not offline, a device is. The phone went off but the laptop stayed on. Delivery must be tracked per device, not per user, so you know a message reached both the phone and the laptop. This entity is what makes multi-device tractable later.

## APIs

Because delivery is real-time and bidirectional, the design uses WebSockets, not REST. There is no standard for a WebSocket API, so it is framed as commands sent (client to server) and commands received (server to client).

Commands sent (client to server):
- create chat
- send message
- create attachment (shape refined during design)
- modify participants (add / remove a user from a chat)

Commands received (server to client):
- new message notification
- chat created / added to a chat
- participants changed (e.g. someone removed from the group)

The presenter explicitly tells the interviewer this is rough scaffolding to be revisited as details firm up. Lesson on communication: APIs and high-level design are iterative; flag where you are stopping short or knowingly simplifying. Do NOT make an obvious mistake silently, the interviewer assumes you missed it and notes it against you. Proactively naming a gap protects the score.

## High-Level Design

Build the simplest thing that satisfies the functional requirements first, then evolve. Start with a single-node chat server (deliberately, to create scaling problems solved later). Reasons to build up organically: it mirrors how real systems evolve, and jumping straight to optimal leaves gaps and loses track of unmet functional requirements.

Architecture (single node):
- Client opens a WebSocket connection to the chat server. (Real WhatsApp uses a plain TLS connection to avoid WebSocket overhead; same principle, a persistent connection to ferry messages both directions. REST does not fit because the server cannot push to the client.)
- Chat server talks to a database. DynamoDB is used, but any key-value store or even a relational DB works. Aside: relational databases do scale (Shopify reported MySQL doing millions of transactions/sec on Black Friday); the "relational can't scale" belief is wrong, though some interviewers hold it and you may adapt.

Connection technology choice (from the real-time updates decision tree): not latency sensitive => long polling; frequent bidirectional => not SSE; peer-to-peer / audio-video => WebRTC. WhatsApp is latency sensitive (500 ms), needs frequent bidirectional messaging, does not need A/V in scope => WebSockets.

### Create / group chats

Two tables in DynamoDB:
- Chat table: chat ID, name, metadata.
- ChatParticipant table: chat ID + participant ID.

Two query patterns drive the keys:
- Find all participants in a chat: composite primary key on chat ID, participant ID as sort key.
- Find all chats a user participates in: a Global Secondary Index (GSI) on participant ID, enabling fast reverse lookup without reorganizing the data.

### Send / receive messages (single node)

All clients hold WebSocket connections to the one chat server (e.g. ~1,000 connections). The server keeps an in-memory hash table mapping client ID to WebSocket (client A -> ws1, client B -> ws2). Flow: client sends "send message" with a chat ID; server queries ChatParticipant for recipient IDs; for each, looks up the WebSocket in the hashmap and pushes a "new message" command. In this degenerate version there is no durability; only currently connected clients can be reached. A live chat room, but nothing stored.

### Media handling (high-level)

Naive: store blobs in a DynamoDB attachments table over the existing WebSocket. Broken for two reasons: DynamoDB is not built for large blobs (videos can be hundreds of MB), and it shoves gigabyte payloads through chat servers tuned for tiny, rapid messages. That payload disparity (the video for Grandma vs an "OMW" text) signals something is wrong.

Better: blob storage (S3), which is built for multi-gigabyte payloads with the right availability and throughput. But routing blobs through the chat server is still wrong.

Solution: pre-signed URLs. Client asks the chat server for an upload target; the chat server uses its credentials to request a pre-signed URL from S3 (a URL with embedded auth, usually a TTL like one hour); the client uploads directly to S3, bypassing the chat server; the client then sends a normal message to the chat ID containing only the URL of the uploaded payload. Recipients receive the URL and fetch the payload directly from S3. This reuses the existing messaging path for tiny control messages. Extra concerns: expire media after delivery (e.g. 30 days) to reclaim space and stop users treating S3 as Google Drive.

### Offline access (durability)

Transient connections are not enough once a device can be offline. Add storage:
- Messages table: message ID, contents, sender/creator ID, timestamp. The chat server assigns the timestamp to keep ordering reasonably consistent.
- Inbox table: recipient ID + message ID. One inbox row per recipient per undelivered message.

Send flow with durability:
1. Client sends "send message" (chat ID + contents) to its chat server.
2. Server looks up participants via the ChatParticipant primary key (the GSI is not needed here).
3. Server writes a transaction: one row in Messages (contents + timestamp) plus one Inbox row per participant. DynamoDB transactions cap at 100 records, so group chats are limited to ~99 participants to fit the message-plus-recipients transaction.
4. For participants who are currently connected, look up their WebSocket and push the message immediately.

Delivery tracking: on receiving a message the client sends an ack (acknowledgement) with the message ID; the server deletes that Inbox entry so it is never resent.

Reconnect flow: when a client connects, the server reads all Inbox rows for that recipient ID, fetches the corresponding message contents, pushes them, and each is acked and removed. Guarantee: messages are eventually delivered as long as the client periodically reconnects; if already online, delivery is immediate over the live socket.

At this point all functional requirements are met, but in a single-node "degenerate" form. The presenter keeps reminding the interviewer he knows it does not yet scale, so they do not conclude he misunderstands scaling.

## Deep Dives

Deep dives exist to satisfy the non-functional requirements, absorb extra interviewer constraints, and iteratively refine. Two NFRs are already partly satisfied by the high-level design: low-latency delivery (immediate push over existing sockets) and guaranteed delivery (durable Messages + Inbox plus reconnect replay). Scale is what breaks everything.

### Scaling connections: layer 4 load balancer

Problem: billions of users and availability concerns rule out one chat server. At ~2 million connections per server you need hundreds to ~1,000 servers. Clients must know which server to hit.

Solution: a load balancer, but specifically a layer 4 (connection-oriented) one, not layer 7. A layer 7 HTTP load balancer terminates each request and forwards it to any stateless web server, which is fine for stateless backends. WebSockets are connection-oriented and stateful, so the connection must persist to a specific server. A layer 4 load balancer creates a symmetric TCP connection: when the client connects, the LB opens a matching connection to a chat server; when the client disconnects, the LB disconnects too. This makes the LB effectively invisible, as if the client connected directly to the chat server.

Balancing policy: least connections. The chat server's scarce resource is the open connection itself (capped ~2 million). When a new server is added it has near-zero connections, so the LB routes new inbound connections to it until it is roughly even with the rest. Gives horizontal scalability.

Trade-off: this alone breaks send/receive. User A on chat server 1 cannot push to user B's WebSocket because B is connected to chat server 2. Fundamentally a routing problem: chat servers must talk to each other so messages reach whichever server holds the recipient's socket.

### Cross-server message routing

Three candidate solutions, compared.

Option A, Kafka topic per user (the common candidate instinct, but wrong here):
- Idea: one Kafka topic per user; chat servers subscribe to the topics of their connected users; to send, write to each participant's topic; subscribed servers read and push to sockets.
- Problems: Kafka is not architected for billions of topics; topics are heavy (~50 to 100 KB each), so billions of users means terabytes of overhead just for partition/topic setup; Kafka does not support rapid connect/disconnect of many short-lived micro topics. Not the right tool.

Option B, consistent hash ring:
- Idea: a user is predictably owned by a specific server, so any message for that user goes to that server, which relays it.
- Mechanics: drop the load balancer; expose chat servers via DNS so clients connect directly. Add a chat registry so a client can ask which server to connect to. Store the user-to-server configuration in a coordination store (ZooKeeper or etcd) synced across all nodes.
- Send flow: client asks the registry, gets "you are on server 1," connects, writes message (also written to Messages and Inbox); to reach user B, look up B's server in ZooKeeper, server 1 sends directly to B's server (server 2), server 2 checks its internal client-to-socket hashmap and pushes if B is connected. Two hops instead of one.
- Trade-offs: scaling is an orchestration burden. Going from 4 to 5 servers keeps most users put but moves ~20% on the edge. The event is signaled into ZooKeeper/etcd; servers slowly disconnect misassigned users, who reconnect via the registry to the correct server. Must be done slowly to avoid a thundering herd of reconnects. During the scaling window a target user may be on either the old or new server, so a sender may have to send to both servers to be safe, adding overhead and orchestration complexity. The interviewer may or may not demand this depth, but you should understand what happens during a consistent-hash scaling event. Also risks hot servers / uneven load.

Option C, Redis Pub/Sub (the recommended synthesis):
- Motivation: Kafka's idea of externalizing inter-server communication was good even though Kafka is the wrong technology; Redis Pub/Sub gives that benefit lightly.
- Mechanics: a chat server subscribes to a Redis topic per connected user ID. Redis keeps an internal hashmap of which sockets listen on a topic; on publish it looks up listeners and forwards. It is a "dumb" socket relay. Send flow: when notifying recipients, the chat server publishes to the user's topic; Redis routes to the server owning that user; that server pushes over the WebSocket bound to the user ID. Messages bounce through Redis to reach the right server, then the right client.
- Trade-off accepted: Redis Pub/Sub guarantees only at-most-once delivery (may deliver or may drop). Normally fatal, but acceptable here because durability already exists: messages are written to durable storage, and on reconnect (or via periodic poll / other notification) clients retrieve anything missed. Redis provides the lightweight sub-500 ms real-time path; the Messages/Inbox layer provides the guarantee.
- Remaining problems: scaling the Redis cluster reintroduces the same orchestration of moving topics and connections. Topics are spread across cluster nodes, so each chat server must hold a connection to each Redis node, an n x m connection count. The Redis cluster does little (just echoing across sockets) so it need not be huge, but n x m connections could become a problem at trillions of accounts.

### Not storing messages unnecessarily (cleanup)

Problem: privacy liability and storage cost; WhatsApp drops undelivered messages after 30 days.
Solution: a cleanup service. Add a secondary index on the Messages timestamp to find and delete messages older than 30 days. Inbox rows are deleted on ack already; add a timestamp field to Inbox so the same time-based cleanup applies to stragglers. When deleting the last Inbox row for a message (all clients received it), also delete the message from Messages. Race conditions are possible, but the 30-day guard rail means anything missed disappears soon anyway. This cleanup is what keeps the live store at a few hundred TB rather than unbounded.

### Multi-device (extension)

Problem: tables are keyed on user ID assuming one device per user (one-to-one recipient relationship). With multiple devices that breaks.
Solution: introduce a Client entity (user ID + client ID). Everything keyed on user becomes keyed on client: Inbox uses recipient client ID; Pub/Sub topics become per client. Send flow: look up participants, then for each participant look up all their clients, then send to each client.
Trade-off: this multiplies Inbox row inserts (100 people x 5 devices each is a large fan-out) and collides with the 100-record DynamoDB transaction limit. Mitigation: cap active clients per user (e.g. 2 to 3 devices) and percolate that limit down into the allowed group size so the per-message transaction stays under 100 records.

### Presence / online status (extension)

Problem: show a green orb for online contacts, none or red for offline. Needs product clarification: which users care about which users' presence, because the fan-out is potentially immense.
Simple approach: a polling table of user ID + status. On WebSocket connect, write status = available; on disconnect, write status = unavailable; query the table when you want a user's status.
Push approach: reuse the existing Pub/Sub infrastructure. Users subscribe to the presence of users they care about; on connect/disconnect events, publish to that topic and push to interested clients.
Trade-off / hard part: fan-out. A single user disconnecting must not trigger thousands or tens of thousands of notifications. The real design problem is constraining how many watchers a given user can have at once. Left as something to explore with extra time.

### Level expectations (explicit in the transcript)

- Mid-level: relatively new to system design. Touch WebSocket management, consistent hashing, Pub/Sub, database design without going deep. Be roughly familiar; calling out challenges is a bonus. Not expected to produce a perfect design out of the gate.
- Senior: expected to be familiar with all core concepts (how load balancers work, how WebSockets work, how consistent hashing enables scaling stateful services). Mistakes are fine and universal; no specialist knowledge expected, but you must assemble a system that scales and satisfies the requirements.
- Staff: zoom in on the qualitatively interesting parts, namely that the chat servers are stateful (which is what makes this problem hard) and that the data model serves both very fast queries and very fast writes for throughput. Staff are not "better seniors"; they focus on different pieces and bring a larger toolkit of approaches and experience.
- Managers: generally held to a senior standard; a few companies hold them to staff, but that is the exception.

## Key Concepts

- WebSocket (or plain TLS) persistent bidirectional connections for real-time chat; REST cannot push server-to-client.
- Connection technology decision tree: long polling (not latency sensitive) vs SSE (server-push only, no frequent client send) vs WebSockets (frequent bidirectional) vs WebRTC (peer-to-peer / audio-video).
- Layer 4 (connection-oriented) load balancing for stateful sockets vs layer 7 for stateless HTTP; least-connections policy because the open connection is the scarce resource (~2M/server).
- In-memory client-ID-to-WebSocket hashmap on each chat server for local push.
- Durable delivery decoupled from the live connection: Messages table for content + timestamp, Inbox table (recipient/client + message ID) for per-recipient undelivered queue.
- Ack-based delivery tracking: client acks message ID, server deletes Inbox row; reconnect replays the Inbox for eventual delivery.
- Cross-server routing for stateful connections: Kafka-per-user (anti-pattern at this scale), consistent hash ring with a chat registry + ZooKeeper/etcd coordination, Redis Pub/Sub as the lightweight relay.
- Consistent hashing for stateful services and its scaling orchestration cost (~20% of users remap on a node change, slow drain-and-reconnect, dual-send during the transition window).
- Redis Pub/Sub as an at-most-once real-time relay made reliable by an underlying durable store; n x m chat-server-to-Redis-node connection cost.
- Pre-signed URLs to offload large media uploads directly to blob storage (S3), keeping control-plane messages tiny and reusing the messaging path.
- Blob storage vs key-value store for large payloads (S3 for multi-GB media, never DynamoDB blobs).
- DynamoDB single-table modeling: composite primary key plus sort key for one access pattern, GSI for the reverse access pattern; 100-record transaction limit constraining group/device size.
- Device-not-user identity modeling for multi-device delivery; capping devices per user to bound fan-out and stay under transaction limits.
- Presence via a status table (polling) or Pub/Sub (push), with watcher-count constraints to bound fan-out.
- TTL-based cleanup (30-day retention) driven by a timestamp secondary index, framed by the privacy principle that retained data is a liability.
- Quantified non-functional requirements (500 ms latency budget reused as a design constraint) and deferred estimation until the design is concrete.
- The build-simple-then-evolve interview method: single node first, then layer on scalability while continually flagging known limitations to the interviewer.
