Source: HelloInterview, "Design Dropbox" (also asked as "Design Google Drive"), by Evan (ex-Meta interviewer and staff engineer, co-founder of Hello Interview). Asked ~50 times across Meta and Hello Interview mocks.

We are designing a file hosting and sync service like Dropbox or Google Drive: upload a file to remote storage, download it back, and automatically keep a local folder in sync with remote across all of a user's devices. The core challenge is not the simple CRUD path. It is the constraints around it: files as large as 50 GB that must upload reliably over a slow, flaky connection, deduplicating and resuming partial transfers, keeping multiple devices consistent without constant full re-downloads, and doing all of it without re-implementing blob storage. The problem is rated on the easier side, most common for mid-level (E4/L4) candidates, but it shows up for senior and staff too. The level deltas appear in how deep you drive the deep dives.

## Requirements

### Functional

1. Upload a file to remote storage.
2. Download a file from remote storage.
3. Automatically sync files across devices. A local folder on the user's machine stays in sync with remote in both directions: a file uploaded to remote is pulled down to every connected device's local folder, and a file dragged into the local folder is pushed up to remote and then synced to the other devices.

Out of scope: rolling your own blob storage. That is a separate interview question ("Design S3"). Here we assume an existing blob store. Sharing is also treated as out of scope.

### Non-functional

The non-functional requirements are the qualities of the system and they drive the deep dives. Most candidates breeze through this with generic buzzwords, which is uninformative. Put each quality in the context of this system and quantify where possible.

1. Availability over consistency (CAP). Partition tolerance is a must at this scale. We pick availability. In context: if a file is changed in Germany and someone in America reads it shortly after, seeing the old version is acceptable. Everyone should still be able to download or view a file on request.
2. Low latency uploads and downloads. Not just the buzzword "low latency" but specifically the upload and download paths. Hard to quantify since files vary, so target as low as possible.
3. Support large files, as large as 50 GB (exactly what Dropbox supports).
4. Resumable uploads. A 50 GB upload can take over an hour. If the connection drops halfway, the user must resume from where they left off, not restart.
5. High data integrity / sync accuracy. Eventual consistency is fine and can take a few seconds, but once stabilized, what is in one local folder must match remote and must match every other folder. No silent divergence.

### Scale and back-of-the-envelope

Dropbox scale is hundreds of millions of daily active users. The presenter deliberately skips upfront estimations. Storage uses near-infinitely scalable blob storage (S3), so capacity math does not change the design. Do estimations only inline in the high-level design when the result will directly influence a decision (it does for the 50 GB upload time math below). Overcommunicate this choice to the interviewer.

## Core Entities

The objects persisted and exchanged in the system. Kept deliberately as "core entities" rather than a full schema because this early you do not know all the columns yet.

- File: the raw bytes of the file. Stored in blob storage (S3), never in the database.
- File metadata: file name, ID, mime type, size, owner ID, and a link to where the bytes live in S3. This grows as the design evolves (chunks, status, timestamps).
- User: present but the least important. Often more of a distraction than a help to draw out.

## APIs

One or more endpoints per functional requirement. Use core entities as inputs and outputs to move fast (shorthand). Note: these first-pass endpoints are intentionally wrong and get corrected after the deep dives. Most candidates do not know the correct shape at this point, and that is fine.

User identity is never in the request body. The user ID comes from the header via a session token or JWT. Putting it in the body would let anyone falsify a request and upload or download on another user's behalf.

First pass:

```
POST /files
Body: { file, fileMetadata }
Returns: 200

GET /files/:fileId
Returns: { file, fileMetadata }

GET /changes?since=<timestamp>
Returns: list of changed fileIds (later: full metadata)
```

`GET /changes` is the sync primitive: the client periodically asks "what changed since this timestamp," gets the changed file IDs, then downloads each. An early optimization noted inline is to return the full metadata instead of just IDs, saving a round trip per changed file.

Corrected after deep dives (upload no longer posts bytes through our servers):

```
POST /files            -> send fileMetadata only, get back a presigned URL
PUT  <presigned-url>   -> upload file chunks directly to S3
PATCH /files/:fileId   -> update chunk status as chunks complete
```

## High-Level Design

Goal: satisfy the three functional requirements simply. Walk the APIs one at a time.

Base path for every request: Client to a Load Balancer / API Gateway (for example AWS managed API Gateway). The gateway handles authentication, rate limiting, SSL termination, and routing to the correct microservice.

### Upload (naive)

Client to File Service. Two things arrive: the file and the file metadata. They are stored in different technologies because they differ in nature:

- Raw bytes go to blob storage (S3). Blob storage is cheap and optimized for large opaque blobs. On upload completion S3 returns a link to the object.
- Metadata goes to a File Metadata DB. After the S3 upload, the File Service writes the metadata row.

Metadata schema (kept next to the DB so it can evolve as flows are added): fileId, fileName, mimeType, size, ownerId (FK to user), s3Link.

### Download

Client calls `GET /files/:fileId` to the File Service. The service looks up the metadata by ID, gets the S3 link, and the client downloads directly from S3 using that link. Critically, do not stream the bytes through the File Service twice (S3 to service, then service to client). Return the metadata, then download straight from S3.

### Sync across devices

For most systems the client is drawn as a small abstract box. Not here. Like streaming systems (Spotify, Netflix, YouTube with adaptive bitrate), the sync client holds real logic and must be drawn large. The client contains:

- Local folder: the directory being synced.
- Client app: a downloaded desktop or mobile application (Mac, Windows, iPhone) responsible for keeping the local folder and remote in sync.
- Local DB: a local database holding metadata (IDs plus extra info) for every file in the local folder. Used to cross-reference against remote so we do not re-download files we already have.

Two sync directions:

1. Remote changed: the client periodically polls for changes (`GET /changes`). Add a Sync Service that owns this endpoint. It queries the File Service / metadata for files whose update timestamp is newer than the client's last sync and returns them. Metadata therefore needs createdAt and updatedAt fields. The client then downloads the changed files directly from S3 and replaces the old versions in the local folder. (Return full metadata, not just IDs, to skip an extra round trip.)
2. Local changed: the client detects local edits using the OS-native directory watch API. Windows exposes FileSystemWatcher; macOS exposes FSEvents. On a detected change, the client uploads via the normal upload path: re-upload to S3, update the s3Link, bump the update time.

The local DB answers "do we already have this file" so a pulled change is not redundantly re-applied. Fingerprinting (hashing) is what makes that cross-reference reliable, deferred to the deep dives.

There is a noted concern about whether splitting the Sync Service from the File Service is over-modularizing. The presenter keeps them split because the Sync Service grows in the deep dives.

## Deep Dives

Deep dives satisfy the non-functional requirements. How proactively you drive them is a function of seniority. Mid-level: the high-level design above is close to a pass, the interviewer will probe with follow-ups and expect competent answers. Senior: drive, go deep in one to two places. Staff: go deep in two to three places, with more hands-on, lower-level detail.

### Deep Dive 1: Large files (50 GB) and resumable uploads

Problem. The naive design only works for files up to roughly 5 to 10 MB, for two reasons:

1. Redundant upload path: bytes go to the File Service and then again to S3. Wasted bandwidth and CPU on the server.
2. Request body size limits: browsers, servers, and API gateways cap POST body size. AWS managed API Gateway caps at 10 MB. A 50 GB file cannot pass through at all, it errors out.

Solution part A, presigned URLs (fixes the redundant path). On upload, send only the metadata to the File Service, which writes the metadata row and sets a status field (for example "started"). Instead of uploading bytes, the File Service requests a presigned URL from blob storage. A presigned URL is the authenticated service asking S3, "I want to upload a file of this mime type and this size," and S3 returns a secure link. The link is signed with metadata constraining it to that mime type, that size, and a limited time window (on the order of 10 to 30 minutes). The URL is returned to the client, and the client uploads bytes directly to S3 via that URL. No bytes touch our servers. This mirrors how download already works (direct from S3).

Solution part B, chunking (fixes size limit and enables resume). Math done inline: a 50 GB file at an average 100 Mbps takes about 1 hour 12 minutes. Losing the connection partway and restarting is unacceptable. So chunk the file on the client into smaller pieces, around 5 MB each. Upload chunks directly to S3, serially or in parallel depending on available bandwidth. Track the status of each chunk so that on failure you compare uploaded chunks against the file's chunks and only re-upload the missing ones.

Data structure. Store chunks in the metadata. SQL vs NoSQL here is treated as an outdated, uninteresting debate (modern engines converge). With SQL (Postgres) you would normalize into a separate chunks table with a foreign key to metadata. The presenter picks DynamoDB and embeds a chunks list on the metadata object. Each chunk item has: id, status, s3Link.

Resume flow: re-fetch the file metadata, compare the client's chunks to the stored chunks, upload only the missing ones.

Fingerprinting (how to identify a chunk). You need a stable, unique way to say "this client chunk equals that stored chunk." Naive approaches like maintaining indexes are error-prone. Instead, fingerprint each chunk: a hash of the chunk's bytes. Steps: chunk the file, hash each chunk to get a fingerprint, use the fingerprint as the chunk's ID. To resume, compare client fingerprints against stored fingerprints and re-upload any chunk whose fingerprint is not marked uploaded.

How does the status get updated reliably? When a chunk lands in S3, the server's metadata must learn it succeeded. The obvious approach (client tells our server "chunk done" via a PATCH) is insecure: a malicious client can lie, leaving metadata inconsistent with S3. Two better options:

- Trust but verify: client reports a chunk uploaded, then the File Metadata Service asks S3 to confirm that chunk actually exists before updating status. This is the presenter's preferred approach.
- Change data capture via S3 notifications: S3 fires a notification on object creation directly to the File Service, which updates metadata. No client trust at all. More moving parts, and a nuance: S3's own multipart upload does not fire per-chunk notifications, so this option does not compose with multipart.

Note: this chunk-upload-fingerprint-verify pattern is exactly what S3 multipart upload does for you (client chunking, upload, fingerprinting, validation). If you use multipart upload, you would not also use S3 notifications per chunk.

Level note: an interviewer would point out the 5 to 10 MB limit to a mid-level candidate as the prompt to introduce presigned URLs and chunking.

### Deep Dive 2: Low latency uploads and downloads

Problem. Make the transfer as fast as possible. Much of the work is already done by chunking.

Chunking. Bandwidth is fixed (the pipe is only so big), but sending multiple chunks in parallel, with adaptive chunk sizes based on network conditions, maximizes use of the available bandwidth. This already speeds uploads.

CDN. Candidates love adding a CDN here, and top candidates weigh whether it is even needed. A CDN caches content close to users, which speeds downloads. But in Dropbox the dominant access pattern is users downloading their own files, and they are likely already near the data center holding their data (imagine the whole setup replicated across about five data centers worldwide). So a CDN is mostly irrelevant and CDNs are expensive. It only helps for travelers, or for a single super-popular shared file (the "Declaration of Independence in everyone's Dropbox" case) under heavy sharing. The presenter opts out of a CDN, but it is a good trade-off conversation.

Compression. Transfer fewer bytes. Compress on the client (like gzip) before upload, decompress after download. But compression is not free: you pay decompression time on the other side, and some file types do not benefit. Text and DOCX compress very well. Already-compressed media (JPEG, PNG, MP4) only shrinks a few percent, not worth the CPU. So do intelligent, conditional compression based on file type and network conditions. If you compress, store a compressionAlgo field in the metadata so the other side knows how to decompress.

### Deep Dive 3: Sync (speed and consistency, high data integrity)

Two goals: make sync fast, and make sync consistent.

#### Making sync fast

Change detection: periodic polling. The client polls the database to learn what changed. Use adaptive polling: increase frequency when the app is open or when there has been recent activity in the folder, back off otherwise. WebSockets and long polling are raised by candidates but are overkill here. A persistent always-on socket per client, plus a websocket manager to maintain it, is unjustified overhead when the product only needs updates within seconds to tens of seconds, not milliseconds. Long polling fits a "expecting a response within a short window" pattern, which this is not (changes arrive unpredictably). A manual refresh button covers the impatient-user case by kicking off an immediate poll.

Delta sync (only fetch changed chunks). When a file changes, do not re-download the whole file, especially a 50 GB one. Dropbox calls this delta sync. On poll, fetch only the chunks that changed since the last sync (using an updatedAt per chunk). A brand-new file has no choice and downloads fully, then updates the local DB and folder. An edit to an existing file downloads only the changed chunks, and the client app stitches them back into the local file. This greatly reduces transfer.

#### Making sync consistent

What "polling" actually means, two options:

- Option 1, poll the database directly. For a given folderId (add a folderId to track the synced folder), query "give me any files whose chunk changed or was added since the last sync." Simple, straightforward, a great default.
- Option 2, event bus with a cursor. Closer to what Dropbox actually does. Put every change event onto an event bus (for example Kafka). Each folder has a sync cursor marking the last event read. First sync of a new folder: no cursor, so replay all events to construct local state. Each subsequent poll navigates from the cursor (think of the bus as a linked list) and applies only the new events to the local DB, then advances the cursor. Operationally you would partition by user ID or folder ID, and periodically consolidate via snapshots so clients do not replay every event from the beginning (restore from a snapshot in metadata, then read forward).

Trade-off. The event-bus-with-cursor approach is powerful precisely because it keeps history: audit trail, version control, data recovery, roll back and roll forward to a previous point. But those were not in our functional requirements. Without versioning, a DB change overwrites the old chunk and history is gone, whereas the event bus retains it. Given the stated requirements, the presenter judges the event bus overkill and opts for polling the database directly for simplicity. If versioning or audit were a requirement, the event bus becomes the right call.

Reconciliation (last-resort integrity). Despite best efforts, local and remote can diverge (developer bug, dropped connection, anything). Periodically (daily or weekly) the client app fetches all remote info for the folder and compares it, by fingerprint, against the local DB and the files actually on disk, then fixes any mismatch. Real-time-ish sync does the day-to-day work; reconciliation is the safety net that guarantees eventual integrity.

## Key Concepts

- Blob storage vs metadata DB: store opaque bytes in cheap blob storage (S3), store queryable structured metadata in a database, link the two with an S3 URL.
- Presigned URLs: time-limited, signed, constraint-bound (mime type, size) URLs that let a client upload or download directly to or from blob storage without routing bytes through your servers.
- Chunking: split a large file into fixed-size pieces (around 5 MB) on the client to bypass request-body limits, parallelize transfer, and enable resume.
- Resumable uploads: track per-chunk status so a failed transfer re-uploads only the missing chunks.
- Content-addressable storage / fingerprinting: hash a chunk's bytes to get a stable unique ID, enabling deduplication and reliable comparison of client vs server state.
- Trust but verify: do not trust a client's success report, have the server confirm with the source of truth (S3) before mutating state.
- Change data capture (CDC): blob-store notifications (S3 notifications) that push object-creation events to your service so state updates without client involvement.
- Multipart upload: S3's built-in chunking, upload, fingerprinting, and validation primitive.
- OS file-watch APIs: FileSystemWatcher (Windows) and FSEvents (macOS) for detecting local folder changes.
- Adaptive polling: vary poll frequency by activity instead of a fixed interval, and reject WebSockets/long polling when near-real-time is unnecessary.
- Delta sync: transfer only the chunks that changed, not the whole file.
- Event bus with cursor: an append-only event log plus a per-consumer cursor, enabling replay, versioning, audit trail, and recovery, at the cost of complexity.
- CDN trade-off: caching content near users only pays off for shared or geographically dispersed access, not for users fetching their own local files.
- Compression trade-off: compress only when the file type and network make the CPU cost worthwhile; record the algorithm in metadata.
- Reconciliation: a periodic full compare (by fingerprint) that repairs divergence as an integrity backstop.
- CAP in context: choosing availability over consistency means tolerating stale reads so downloads never block.
- API security: derive user identity from the JWT/session header, never from the request body.
