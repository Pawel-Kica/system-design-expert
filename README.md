# System Design Expert

An AI-powered system design knowledge base and interview prep tool, built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

You give it a system design problem. It produces a structured solution (requirements, APIs, schemas, deep dives) and visual architecture diagrams you can open in Obsidian or Excalidraw.

![Uber system design canvas in Obsidian](assets/preview.png)

## What's inside

- **`_Brain.md`** -- A self-contained knowledge base covering 50+ system design concepts (CAP theorem, caching, sharding, distributed locks, fan-out, geospatial indexing, etc.), compiled from multiple sources
- **`Problems/`** -- Solved system design problems (Ticketmaster, Uber, Twitter Feed, URL Shortener) with requirements, APIs, schemas, deep dives, and architecture canvases (Base vs Deep)
- **Source notes** -- Detailed transcripts from system design courses and interview breakdowns
- **`canvas_to_excalidraw.py`** -- Converts Obsidian `.canvas` files to `.excalidraw.md`

## Setup

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

```bash
git clone https://github.com/Pawel-Kica/system-design-expert
cd system-design-expert
```

The `/system-design` slash command is automatically available when you open Claude Code in this directory.

## Usage

Open Claude Code in the repo root, then use the slash command:

### Solve a new problem

```
/system-design solve Chat System
```

Generates a full solution: requirements, core entities, REST APIs, high-level design, deep dives, and two architecture canvases (Base = naive design, Deep = optimized with caching, queues, distributed locks, etc.).

### Explain a concept

```
/system-design explain consistent hashing
```

Explains the concept using the knowledge base. If the brain has enough detail, answers from it alone. If thin, pulls from the source notes.

### Review your knowledge

```
/system-design review
```

Shows a structured overview of all knowledge by category, flags thin areas, and suggests what to study next.

### Update the brain

```
/system-design update
```

Regenerates `_Brain.md` from scratch by reading all source notes and problem files. Run this after adding new source material.

## Obsidian integration

The `.canvas` files open natively in [Obsidian](https://obsidian.md). Open this repo as an Obsidian vault to browse the architecture diagrams, navigate wikilinks between concepts and sources, and use the knowledge base as a second brain.

## Adding your own sources

Drop `.md` files (notes, transcripts, articles) into the repo root, then run `/system-design update` to incorporate them into the brain.

## License

MIT
