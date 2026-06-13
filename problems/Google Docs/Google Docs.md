## Requirements

### Functional Requirements

- Users should be able to **create and edit a document** (open a doc, type, see edits persisted)
- Users should be able to **collaborate in real time** (multiple users editing the same doc concurrently, edits appear on everyone's screen within ~100ms)
- Users should be able to **see other users' presence and cursors** (who else is in the doc, where their cursor and selection are)

### Non-Functional Requirements

- **Low-latency edits (~100ms)**: Collaboration feels broken above this threshold. Local edits must apply instantly (optimistic) and remote edits must propagate fast. This is the defining quality of the system.
- **Conflict-free concurrent edits**: Two users typing at the same position must not corrupt the document or drop characters. Concurrent edits must be reconciled deterministically.
- **Eventual consistency converging to one final state (AP for edits)**: Clients may briefly diverge while ops are in flight, but every client must converge to the identical document once all ops are delivered. Convergence is non-negotiable, momentary divergence is acceptable.
- **High availability**: The editor must stay writable. A user typing should never be blocked waiting on a server round-trip. Favor availability over strict global ordering at every keystroke.
- **Durability**: A confirmed edit must survive a server crash. No acknowledged keystroke is ever lost.
- **Read/write profile**: Unlike feed systems, an active doc is write-heavy per connected client (every keystroke is a write op), but the concurrent editor count per doc is small (typically 2-10, rarely 100+). The scaling axis is many docs each with a handful of live editors, not one doc with millions.

### Out of Scope

- Rich media embeds (images, drawings, tables) beyond plain styled text
- Document permissions / sharing ACLs (assume access already granted)
- Comments and suggestions mode
- Version history UI (we store the data, but the diff/restore UI is out of scope)
- Search across documents
- Spell check, grammar, export to PDF/Word

---

## Core Entities

- **Document**: id, ownerId, title, current content (or current revision pointer), createdAt, updatedAt
- **Operation (Edit)**: id, docId, authorId, revision (server sequence number), type (insert | delete | format), position, payload (chars or attributes), clientTimestamp
- **User**: id, name, color (assigned for cursor/highlight rendering)
- **Session / Cursor**: connectionId, docId, userId, cursorPosition, selectionRange, lastSeenAt. Ephemeral, lives only for the duration of a WebSocket connection.

---

## APIs

Document lifecycle is plain REST. The live editing channel is a WebSocket, because edits flow bidirectionally and continuously.

### Create Document

```
POST /docs
Header: JWT
Body: { title }
-> { docId }
```

### Get Document (initial load)

```
GET /docs/{docId}
Header: JWT
-> { doc: Document, content, revision }
```

Returns the current materialized content plus the server `revision` number. The client uses `revision` as the baseline for every op it sends next.

### List Documents

```
GET /docs
Header: JWT
-> { docs: PartialDocument[] }
```

### Collaboration Channel (WebSocket)

```
WS /docs/{docId}/connect
Header: JWT
```

Once connected, the client and server exchange framed messages:

```
// client -> server: a local edit, stamped with the revision it was made against
{ type: "op", docId, baseRevision, operation: { type: "insert", pos: 42, text: "h" } }

// server -> client: a peer's edit, already transformed and assigned a revision
{ type: "op", revision, authorId, operation }

// server -> client: acknowledgement of the client's own op
{ type: "ack", revision }

// client <-> server: cursor / selection movement (no document mutation)
{ type: "cursor", pos, selection: [start, end] }

// server -> client: presence roster changes
{ type: "presence", users: [{ userId, name, color, cursor }] }
```

The key design choice: an op is never sent raw against "the current document." It is always tagged with the `baseRevision` it was authored against, so the server knows which concurrent ops it must transform against.

---

## High-Level Design

### The Naive Approach (and why it loses edits)

The simplest thing that compiles: treat the doc like any CRUD resource.

1. Client loads the doc with `GET /docs/{docId}`.
2. On a timer (or on blur), the client sends the entire document body back: `PUT /docs/{docId}` with `{ content }`.
3. The server overwrites the row. Last write wins.

This satisfies "create and edit a doc" for a single user. It fails the moment two people edit:

- Alice and Bob both load revision 5. Alice fixes a typo in paragraph 1, Bob adds a sentence to paragraph 3. Both `PUT` the whole document. Whoever saves second overwrites the other's entire copy. Alice's typo fix vanishes, or Bob's sentence does. Concurrent work is silently destroyed.
- There is no real-time element. The other user sees nothing until they reload. Polling `GET /docs/{docId}` every few seconds is the best you can bolt on, and it still clobbers in-flight local edits when the poll response arrives.

Last-write-wins on a whole-document blob is the canonical wrong answer. It violates conflict-free concurrent edits, low latency, and convergence all at once. The rest of the design exists to fix this: send **fine-grained operations** instead of the whole document, and **reconcile concurrent operations** instead of overwriting.

### The Real High-Level Flow

1. Client opens the doc: `GET /docs/{docId}` returns content + baseline `revision`.
2. Client opens a WebSocket to a **collaboration server** for that doc.
3. User types a character. The client **applies it locally and immediately** (optimistic update, zero perceived latency), and sends the op `{ insert, pos, text, baseRevision }` over the socket.
4. The collaboration server receives the op, **transforms it** against any ops that landed since `baseRevision` (see Deep Dive 1), assigns it the next `revision`, appends it to the **op log**, and **broadcasts** the transformed op to every other connected client.
5. Each receiving client transforms the incoming op against its own unacknowledged local ops, then applies it. Cursors shift to match.
6. The author receives an `ack` with the assigned revision and advances its baseline.

Edits are tiny, ordered, and reconciled, never whole-document overwrites.

### Database Schema

**Document table:**

| Column           | Type      | Notes                                  |
| ---------------- | --------- | -------------------------------------- |
| id               | UUID PK   |                                        |
| ownerId          | UUID FK   |                                        |
| title            | string    |                                        |
| latestRevision   | bigint    | server sequence number of last op      |
| createdAt        | timestamp |                                        |
| updatedAt        | timestamp |                                        |

**Operation table (the op log):**

| Column          | Type      | Notes                                            |
| --------------- | --------- | ------------------------------------------------ |
| id              | UUID PK   |                                                  |
| docId           | UUID FK   | indexed, partition/shard key                     |
| revision        | bigint    | monotonic per doc, (docId, revision) is unique   |
| authorId        | UUID FK   |                                                  |
| type            | enum      | insert, delete, format                           |
| position        | int       | index into the document                          |
| payload         | jsonb     | chars to insert, length to delete, or attributes |
| createdAt       | timestamp |                                                  |

**Snapshot table:**

| Column      | Type      | Notes                                          |
| ----------- | --------- | ---------------------------------------------- |
| docId       | UUID FK   | indexed                                        |
| revision    | bigint    | the revision this snapshot materializes up to  |
| content     | blob      | full document body at that revision            |
| createdAt   | timestamp |                                                |

The unique constraint on `(docId, revision)` is the integrity backbone: it guarantees no two ops can claim the same slot in a document's history.

### Database Choice

**Postgres for documents and the op log; object storage (S3) for large snapshots.**

The op log is an append-only event stream keyed by `(docId, revision)`. Postgres handles this cleanly: the unique constraint enforces ordering, and writes are append-only so there is no update contention. The concurrency hot spot is "many ops for one doc arriving in a burst," but ops for a single doc are serialized through one collaboration server before they ever hit the database, so the DB never sees a true write race. Partition the op log by `docId` so one doc's history stays local to one shard.

Snapshots can grow large (a 50-page doc is hundreds of KB), so store the snapshot blob in S3 and keep only the pointer + revision in Postgres. As with most systems, the SQL vs NoSQL framing matters less than the qualities we need: append-only ordered writes, a uniqueness guarantee for revision slots, and cheap range reads of "all ops after revision N."

---

## Deep Dives

### Deep Dive 1: Conflict Resolution for Concurrent Edits (OT vs CRDT)

**The problem:** Alice and Bob both start from `"cat"` (revision 5). Alice inserts `"s"` at position 3 to make `"cats"`. Simultaneously Bob inserts `"!"` at position 3 to make `"cat!"`. Both ops say "insert at position 3." If the server naively applies both, the second op's position 3 is now wrong, because the first insert already shifted the text. Applied blindly you get garbage or, worse, the two clients end up with different strings (`"cats!"` on one, `"cat!s"` on the other) and never converge. We need a deterministic rule that makes every client land on the same final string regardless of arrival order.

Two industry approaches solve this: **Operational Transformation (OT)** and **CRDTs**.

**Operational Transformation (OT)**

Ops are expressed against positions. When two ops were authored concurrently (same baseRevision), a **transform function** rewrites one op so it composes correctly after the other.

```
transform(opA, opB):
  if opA.pos < opB.pos:        opA unchanged
  if opA.pos > opB.pos:        shift opA.pos by opB's length delta
  if opA.pos == opB.pos:       break the tie deterministically (e.g., by authorId)
```

In the example: the server receives Alice's `insert("s", 3)` first, assigns it revision 6. Bob's op arrives tagged `baseRevision 5`, so the server transforms it against revision 6: Alice inserted one char at position 3, so Bob's insert shifts to position 4, yielding `"cats!"`. The server then broadcasts the transformed op. Alice's client transforms the incoming op against its own unacked ops the same way. Everyone converges to `"cats!"`.

The transform must satisfy the **TP1 property**: `transform` of two concurrent ops produces results that, applied in either order, yield the identical document. This is what guarantees convergence.

- Strengths: ops are tiny (a position and a payload). The document representation is a plain string or array, no per-character bookkeeping. Memory footprint is small.
- Weaknesses: OT correctness is famously hard. The transform function must handle every op-type pair (insert vs insert, insert vs delete, delete vs delete, format vs anything), and real implementations have shipped subtle convergence bugs for years. Crucially, **OT relies on a central server** to assign the canonical order and run transforms. It is not designed for peer-to-peer.

**CRDTs (Conflict-free Replicated Data Types)**

Instead of transforming positions, give every character a globally unique, immutable identity and a position derived from a total order that never needs rewriting. Sequence CRDTs (RGA, LSEQ, the model behind Yjs and Automerge) assign each inserted character a fractional or dense position id between its neighbors. "Insert between A and B" produces an id that sorts between them, so concurrent inserts at the same visual spot get distinct stable ids and a tie-break by replica id. Deletes are tombstones, the character id is marked dead, never reused.

- Strengths: order-independent by construction. No central transform server is needed, peers can merge directly, which makes CRDTs the natural fit for offline-first and true P2P. Merges are commutative and idempotent.
- Weaknesses: heavy metadata. Every character carries a position id and identity, and deleted characters linger as tombstones, so the in-memory and on-the-wire representation is far larger than OT's. Garbage-collecting tombstones across distributed replicas is its own hard problem.

**Decision: OT with a central collaboration server.**

This is the classic Google Docs answer and the right one here. We already have a central server in the architecture (the per-doc collaboration server that broadcasts ops and assigns revisions), so OT's "needs a central authority" requirement is free, not a cost. The central server gives us a single source of truth for ordering, which makes the transform tractable: every client transforms only against the linear, server-assigned op sequence rather than an arbitrary peer mesh. The payloads stay tiny, which directly serves the low-latency requirement. CRDTs earn their keep when you genuinely need serverless P2P or robust offline merge, neither of which is a hard requirement here. We note CRDTs as the alternative and move on.

**Level expectations:**
- **Mid-level:** Recognizes whole-document save loses edits, proposes sending per-character operations with positions, hand-waves the conflict case.
- **Senior:** Explains OT with a concrete transform example, the baseRevision tagging, and why a central server assigns canonical order.
- **Staff:** Compares OT vs CRDT with the metadata/centralization trade-off, names TP1 convergence, and justifies the choice against the actual requirements rather than reciting both.

---

### Deep Dive 2: Real-Time Sync and Presence

**The problem:** Edits and cursor movements must reach every other editor of the same doc in ~100ms, bidirectionally, and the server must transform each incoming op before fan-out. We also need to show who is present and where their cursor sits.

**Transport: WebSockets.** Editing is genuinely bidirectional and high-frequency (every keystroke both sends a local op and may receive remote ops), so we want a persistent full-duplex connection. SSE is server-to-client only and would force a separate channel for the client's outbound ops, so it loses here. Long polling adds per-message handshake overhead that kills the latency budget. The client holds one WebSocket per open doc.

**Per-document collaboration server.** All editors of a given doc connect to the same server process, which holds the authoritative in-memory state for that doc: the current revision counter, the recent op tail (for transforming late-arriving ops), and the set of live connections. Co-locating all editors of one doc on one server is what makes OT cheap. The server transforms each op against the ops since the sender's baseRevision (a tight in-memory operation), assigns the next revision, appends to the op log, and broadcasts to the other sockets.

**Presence and cursors** ride the same socket but bypass the op log. A `cursor` message is ephemeral, the server fans it out to peers but never persists it. Presence is simply the membership of the connection set: when a socket opens, broadcast a join with the user's color; when it closes (or heartbeat times out), broadcast a leave. Cursor positions are themselves transformed against incoming edits so that when text shifts, everyone's rendered cursor shifts with it.

**Scaling across many servers.** One server can hold the editors of one doc, but we have millions of docs and far more connections than one box holds. Two complementary mechanisms:

1. **Route all editors of a doc to the same server (consistent hashing by docId).** A connection-router / load balancer hashes `docId` onto a ring of collaboration servers, so every editor of doc X lands on the same instance. This keeps OT in-memory and avoids cross-server coordination for the common case. Consistent hashing means adding or removing a server only remaps a small slice of docs, not everything.

2. **Redis Pub/Sub for cross-server fan-out (fallback / resilience).** Pinning by docId is the happy path, but during rebalancing, server failover, or a doc briefly split across two instances, ops must still reach everyone. Each collaboration server subscribes to a Redis channel `doc:{docId}`. When it commits an op it publishes to that channel; any other server holding connections for that doc receives it and forwards to its local sockets. This is the same pattern Uber uses for ride tracking: the publisher does not care which instance holds a given client's socket, Redis routes the message. Redis Pub/Sub decouples op fan-out from connection placement.

**What if the WebSocket drops?** The client reconnects, sends its last acknowledged revision, and the server replays ops since then (the op log makes this trivial, see Deep Dive 3). Local unacked ops are re-sent and re-transformed. No edits lost.

**Level expectations:**
- **Mid-level:** WebSockets for two-way real-time, broadcast edits to other clients in the room.
- **Senior:** Per-doc server holding authoritative state, presence via connection set, cursors transformed against edits, reconnect-and-replay on drop.
- **Staff:** Consistent hashing by docId to keep OT in-memory, Redis Pub/Sub for cross-server fan-out during failover/rebalance, heartbeat-based presence timeout.

---

### Deep Dive 3: Persistence and Scale

**The problem:** We need durability (no acknowledged edit lost), fast initial load for a late-joining client, and a storage model that does not grow unbounded or replay a million ops on every open.

**Store the op log (event sourcing).** Every committed op is appended to the Operation table keyed by `(docId, revision)`. The document's true state is the ordered fold of all its ops. This gives durability for free (the op is persisted before ack), it is the source material for OT transforms, and it makes reconnect-replay trivial: "give me all ops after revision N." Append-only writes mean no update contention.

**But pure replay does not scale.** A doc edited for a year has millions of ops. Replaying all of them to materialize the current state on every open would be slow and waste memory. So we periodically write **snapshots**: a background job (or a trigger every N ops, say every 1,000) folds the op log up to some revision into a full materialized document body and stores it (blob in S3, pointer in the Snapshot table at that revision).

**Late-joining client load = snapshot + replay tail.** When a user opens a doc:
1. Load the latest snapshot (revision S) from S3.
2. Replay only the ops with `revision > S` from the op log (at most ~1,000) on top of it.
3. Return the materialized content and the current `latestRevision` as the client's baseline.

This bounds load work to one snapshot read plus a tiny replay, regardless of total document age.

**Compaction.** Once a snapshot at revision S exists and is durable, ops older than S are only needed for version history. If history beyond the last snapshot is out of scope, those ops can be compacted away or moved to cold storage, keeping the hot op log small. We keep a rolling window of recent snapshots so version history still has anchor points.

**Document storage choice.** Op log and the latest-revision pointer live in Postgres (ordered, unique-constrained, partitioned by docId). Large snapshot blobs live in S3 (cheap, durable, scales independently of the relational store). Partition/shard the op log by `docId` so each doc's history is co-located, matching the collaboration server's per-doc affinity.

**Offline edit reconciliation.** A user who goes offline keeps editing locally, queuing ops against the last revision they saw (say revision 40), while the server advances to revision 70. On reconnect:
1. The client pulls ops 41-70 from the server.
2. It transforms its queued offline ops against that batch using the same OT transform function from Deep Dive 1, then submits them. The server assigns them revisions 71+ and broadcasts.

Because OT transforms are exactly "rebase my op onto ops that happened concurrently," offline reconciliation is the same machinery as live concurrency, just with a longer gap. This is also the scenario where a CRDT's merge-anywhere property would shine, and worth naming as the trade-off: we accept slightly more reconnect logic in exchange for OT's lighter steady-state payloads. If long offline windows were a hard requirement, the CRDT choice from Deep Dive 1 would get reconsidered.

**Level expectations:**
- **Mid-level:** Persist edits to a database so they survive restart, load the doc on open.
- **Senior:** Event-sourced op log plus periodic snapshots, load = snapshot + replay tail, reconnect replays ops since last seen revision.
- **Staff:** Compaction strategy and snapshot cadence, Postgres-for-log / S3-for-snapshot split, offline reconciliation as the same OT rebase, and the explicit OT-vs-CRDT reconsideration trigger for long offline use.
