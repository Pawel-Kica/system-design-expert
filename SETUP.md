# Setup

A two-minute walkthrough to go from clone to your first solved problem.

## 1. Clone and open

```bash
git clone https://github.com/Pawel-Kica/system-design-expert
cd system-design-expert
```

Open Claude Code in this directory. The `/system-design` skill lives in `.claude/skills/` and is available immediately, no install step.

## 2. See what's in the brain

```
/system-design review
```

This prints the knowledge base by category and flags thin areas. Good first look at what the tool already knows.

## 3. Solve a problem

```
/system-design solve Distributed Cache
```

You get a full written solution under `problems/Distributed Cache/` plus two diagrams:

- `Canvas/<Name> Base.canvas`: the naive design.
- `Canvas/<Name> Deep.canvas`: the scaled design, with a node summarizing what Deep adds.

The matching `.excalidraw.md` files are generated into `Excalidraw/` automatically.

## 4. Open the diagrams

Open the repo as an [Obsidian](https://obsidian.md) vault and open any `.canvas` file to see the architecture. Or open the `.excalidraw.md` files with the Excalidraw plugin.

## 5. Grow it

- `/system-design explain <concept>`: ask the brain anything.
- Drop a transcript or article into `sources/`, then `/system-design update` to fold it into the brain.

That is the whole loop: solve problems, read the diagrams, feed it new sources, ask it to explain.
