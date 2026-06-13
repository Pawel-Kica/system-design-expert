---
description: System design knowledge base and problem solver
argument-hint: explain <concept> | review | update | solve <problem>
---

Parse $ARGUMENTS to determine the mode. If empty or unclear, ask which mode.

# Paths

- **Knowledge base**: `Sources/` (source notes and transcripts)
- **Brain file**: `_Brain.md` (in project root)
- **Problems dir**: `Problems/`

---

# Mode: explain <concept>

1. Read `_Brain.md`
2. Find the section(s) relevant to the concept
3. Explain it clearly using the brain's content
4. If the brain has enough detail, answer from it alone
5. If the user asks for more depth or the brain is thin on the topic, THEN read the specific source file(s) referenced via `[[wikilinks]]` in the brain
6. Keep explanations practical, not academic

---

# Mode: review

1. Read `_Brain.md`
2. Present a structured overview of all knowledge by category
3. For each category, note whether it's **deep** (multiple paragraphs, examples, trade-offs) or **thin** (just definitions)
4. Suggest 2-3 topics worth studying next, based on what's thin in the brain itself
5. Do NOT compare against an external list of "common interview topics." Only assess what's already in the brain.

---

# Mode: update

1. Read ALL `.md` files in `Sources/`
2. Also read `.md` files in `Problems/*/` if any exist
3. Skip `.canvas` files
4. Regenerate `_Brain.md` from scratch by extracting and compiling all knowledge
5. Follow the existing brain structure: categories with bolded concept names and 2-5 sentence explanations
6. Cite sources as `[[wikilinks]]` inline where a concept comes from a specific file
7. Set `Last updated:` to today's date
8. Report what changed: new concepts added, sections expanded, anything removed

**Critical**: The brain must be self-contained. Each explanation should stand on its own without needing to open the source file. The brain IS the knowledge, not an index of files.

---

# Mode: solve <problem>

Act as a system design expert. Given a problem (e.g., "URL Shortener", "Instagram Feed", "Chat System"):

## Step 1: Read context

- Read `_Brain.md` for relevant concepts and patterns
- If the user provides a YouTube URL or reference material, read/transcribe that first

## Step 2: Create the solution folder

Create the folder and its two diagram subfolders:
- `Problems/<Problem Name>/`
- `Problems/<Problem Name>/Canvas/` (the `.canvas` files go here)
- `Problems/<Problem Name>/Excalidraw/` (the converter writes `.excalidraw.md` files here)

## Step 3: Write the solution file

Create `Problems/<Problem Name>/<Problem Name>.md` (at the problem root, not in a subfolder) following this structure:

```
## Requirements

### Functional Requirements
- Users should be able to...
- Users should be able to...
- Users should be able to...

### Non-Functional Requirements
- CAP trade-off: which parts need consistency vs availability, and why
- Read/write ratio and what it implies
- Specific scaling concern unique to this system
- Any other quality that makes this system interesting/challenging

### Out of Scope
- Items considered but deprioritized

## Core Entities
- Entity 1: key fields
- Entity 2: key fields
...

## APIs

REST endpoints, one per functional requirement. Include method, path, headers, body, and response type.

## High-Level Design

Walk through each API endpoint:
1. How the request flows through the system (Client -> CDN -> API Gateway -> Service -> DB)
2. Database schema with tables, columns, and relationships
3. Database choice with brief justification (focus on required qualities, not SQL vs NoSQL debate)

## Deep Dives

2-3 deep dives that address the non-functional requirements. Each should:
- State the problem clearly
- Present the solution with trade-offs
- Reference relevant concepts from the brain (caching, sharding, CDC, distributed locks, etc.)
- Mention level expectations where relevant (mid-level vs senior vs staff approach)
```

## Step 4: Create TWO canvases

Create two separate canvas files. The split mirrors the interview structure: high-level design satisfies functional requirements first, then deep dives optimize for non-functional requirements.

### Shared left column (BOTH canvases must have this)

Both canvases include the full problem context on the left side, identical in both files:
- **Title node** (top-left): system name, short description, scale
- **Roadmap steps** (top row): 1. Requirements -> 2. Core Entities -> 3. API -> 4. High-Level Design -> 5. Deep Dives, with label nodes pointing to step 4 and 5
- **Functional Requirements** node
- **Non-Functional Requirements** node
- **Out of Scope** node
- **Core Entities** node
- **APIs** node

This context is always present. The only difference between Base and Deep is the architecture diagram in the center/right.

Both canvases are saved in `Problems/<Problem Name>/Canvas/`.

### Canvas 1: `Canvas/<Problem Name> Base.canvas`

The **simple high-level design** that satisfies functional requirements. The "it works but doesn't scale" version.

**Architecture (center/right) includes:**
- Client -> API Gateway -> Services -> Database (the basic flow)
- Database schema tables (core entities with fields)
- API endpoint labels
- The naive/simple approach for each service (e.g., SQL search with LIKE, no caching, no queues)
- Booking/payment flows if applicable (e.g., Stripe, two-phase booking)
- Annotation nodes showing simple queries or logic

**Architecture does NOT include:**
- No Redis/caching layers
- No Elasticsearch or search-optimized databases
- No message queues or async processing
- No CDN
- No distributed locks (use simpler approaches like cron jobs or timestamps)
- No virtual waiting queues
- No CDC pipelines

### Canvas 2: `Canvas/<Problem Name> Deep.canvas`

The **fully optimized design** with all deep dive additions. The senior/staff answer.

**Architecture (center/right) includes everything from Base, PLUS:**
- Caching layers (Redis, CDN)
- Search-optimized databases (Elasticsearch) with CDC sync
- Message queues for async processing
- Distributed locks
- Virtual waiting queues
- Real-time updates (SSE/WebSockets)
- Read replicas, sharding annotations
- Any other optimizations from the deep dives

**PLUS a "Deep Dive Optimizations" summary node** (color 6, placed above the architecture area) listing what was added on top of Base. Format:
```
**Deep Dive Optimizations**
1. <optimization name> -- what it solves
2. <optimization name> -- what it solves
3. <optimization name> -- what it solves
```
This acts as a before/after reference so you can see at a glance what changed from Base to Deep.

### Canvas Format (applies to both)

**Canvas JSON structure:**

```json
{
  "nodes": [
    {"id": "...", "type": "text", "text": "**Node Title**\ncontent", "x": N, "y": N, "width": N, "height": N, "color": "N"}
  ],
  "edges": [
    {"id": "...", "fromNode": "...", "fromSide": "right", "toNode": "...", "toSide": "left", "label": "optional"}
  ]
}
```

**Layout rules (critical for readability):**

- **Column spacing:** 400px minimum between columns
- **Vertical spacing:** 180px minimum between nodes in the same column
- **No column-skipping edges:** Every edge should connect nodes in adjacent columns only
- **Vertical ordering minimizes crossings:** If A->C and B->D, and C is above D, then A should be above B
- **Strict left-to-right flow:** Almost all edges use `fromSide: "right"` -> `toSide: "left"`. Only use vertical edges (top/bottom) for stacked parent-child relationships.
- **Schema tables are documentation, not data flow.** No edges from Database to schema tables.
- **Minimize edges per node.** Max 4 edges per node.

**Sizing guidelines:**

- **Height formula:** count text lines, then: `height = (lines * 32) + 80`. For nodes with bullet points, add 24px extra. Always round up.
- Small labels/services: width 130-200
- Medium content nodes: width 200-300
- Large content nodes (requirements, APIs): width 300-500
- Schema tables: width 180-240

**Color codes:** 0 = gray (labels, out of scope), 1 = red (title, API gateway), 2 = orange (Redis/cache), 3 = yellow (external services like Elasticsearch, Stripe), 4 = green (services, roadmap steps), 5 = blue (requirements, core entities), 6 = purple (database/schema)

### Excalidraw generation

After creating canvas files, generate matching `.excalidraw.md` files using the converter script. It auto-detects the `Canvas/` folder and writes the output into the sibling `Excalidraw/` folder:

```bash
python3 canvas_to_excalidraw.py "Problems/<Problem Name>/Canvas/<Problem Name> Base.canvas"
python3 canvas_to_excalidraw.py "Problems/<Problem Name>/Canvas/<Problem Name> Deep.canvas"
```
