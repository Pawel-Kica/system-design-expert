#!/usr/bin/env python3
"""
Convert Obsidian .canvas files to .excalidraw.md files.

Usage:
  python3 canvas_to_excalidraw.py <input.canvas> [output.excalidraw.md]

If output is omitted, replaces .canvas with .excalidraw.md in the same directory.
"""

import json
import sys
import re
import random
import string
import os

# Canvas color code -> (backgroundColor, strokeColor)
COLOR_MAP = {
    "0": ("#f8f9fa", "#868e96"),   # gray
    "1": ("#ffe3e3", "#c92a2a"),   # red
    "2": ("#ffe8cc", "#e8590c"),   # orange
    "3": ("#fff3bf", "#e67700"),   # yellow
    "4": ("#d3f9d8", "#2b8a3e"),   # green
    "5": ("#d0ebff", "#1971c2"),   # blue
    "6": ("#e5dbff", "#7048e8"),   # purple
}
DEFAULT_COLOR = ("#ffffff", "#1e1e1e")

_used_ids = set()


def strip_markdown(text):
    """Strip markdown formatting for Excalidraw (which renders plain text only).
    Removes heading prefixes, bold/italic markers, inline code backticks.
    Keeps list dashes, arrows, and other plain-text-friendly syntax.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        # Strip heading prefixes: ### Heading -> Heading
        line = re.sub(r"^#{1,6}\s+", "", line)
        # Strip bold: **text** -> text
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        # Strip italic: *text* -> text (but not lines starting with * as list items)
        line = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", line)
        # Strip inline code backticks: `text` -> text
        line = re.sub(r"`(.+?)`", r"\1", line)
        # Strip strikethrough: ~~text~~ -> text
        line = re.sub(r"~~(.+?)~~", r"\1", line)
        result.append(line)
    return "\n".join(result)


def make_id(length=8):
    """Generate a unique 8-char alphanumeric ID matching Excalidraw's format."""
    while True:
        chars = string.ascii_letters + string.digits
        new_id = "".join(random.choice(chars) for _ in range(length))
        if new_id not in _used_ids:
            _used_ids.add(new_id)
            return new_id


def rand_seed():
    return random.randint(100000, 999999999)


def make_rect(rect_id, x, y, w, h, bg_color, stroke_color, bound_ids):
    bound = [{"id": bid, "type": btype} for bid, btype in bound_ids]
    return {
        "type": "rectangle",
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "id": rect_id,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": x,
        "y": y,
        "strokeColor": stroke_color,
        "backgroundColor": bg_color,
        "width": w,
        "height": h,
        "seed": rand_seed(),
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "boundElements": bound,
        "updated": 1700000000000,
        "link": None,
        "locked": False,
    }


def make_text(text_id, container_id, x, y, w, h, raw_text):
    return {
        "type": "text",
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "id": text_id,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": x + 10,
        "y": y + 10,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "width": w - 20,
        "height": h - 20,
        "seed": rand_seed(),
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "boundElements": [],
        "updated": 1700000000000,
        "link": None,
        "locked": False,
        "fontSize": 16,
        "fontFamily": 1,
        "text": raw_text,
        "rawText": raw_text,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": container_id,
        "originalText": raw_text,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def get_anchor(node, side):
    x, y, w, h = node["x"], node["y"], node["width"], node["height"]
    if side == "right":
        return x + w, y + h / 2
    elif side == "left":
        return x, y + h / 2
    elif side == "top":
        return x + w / 2, y
    elif side == "bottom":
        return x + w / 2, y + h
    return x + w, y + h / 2


def make_arrow(arrow_id, from_rect_id, to_rect_id, start_x, start_y, dx, dy, bound_ids=None):
    bound = [{"id": bid, "type": btype} for bid, btype in (bound_ids or [])]
    return {
        "type": "arrow",
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "id": arrow_id,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": start_x,
        "y": start_y,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "width": abs(dx) if dx != 0 else 0.01,
        "height": abs(dy) if dy != 0 else 0.01,
        "seed": rand_seed(),
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 2},
        "boundElements": bound,
        "updated": 1700000000000,
        "link": None,
        "locked": False,
        "startBinding": {"elementId": from_rect_id, "focus": 0, "gap": 8},
        "endBinding": {"elementId": to_rect_id, "focus": 0, "gap": 8},
        "lastCommittedPoint": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "points": [[0, 0], [dx, dy]],
    }


def make_arrow_label(label_id, arrow_id, text, mid_x, mid_y):
    return {
        "type": "text",
        "version": 1,
        "versionNonce": rand_seed(),
        "isDeleted": False,
        "id": label_id,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "angle": 0,
        "x": mid_x - 50,
        "y": mid_y - 12,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "width": 100,
        "height": 24,
        "seed": rand_seed(),
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "boundElements": [],
        "updated": 1700000000000,
        "link": None,
        "locked": False,
        "fontSize": 14,
        "fontFamily": 1,
        "text": text,
        "rawText": text,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": arrow_id,
        "originalText": text,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def convert(canvas_path, output_path=None):
    global _used_ids
    _used_ids = set()

    if output_path is None:
        output_path = canvas_path.replace(".canvas", ".excalidraw.md")

    with open(canvas_path, "r", encoding="utf-8") as f:
        canvas = json.load(f)

    nodes = canvas.get("nodes", [])
    edges = canvas.get("edges", [])
    node_map = {n["id"]: n for n in nodes}

    # Pre-assign stable IDs for all elements
    rect_ids = {}   # canvas node id -> excalidraw rect id
    text_ids = {}   # canvas node id -> excalidraw text id
    arrow_ids = {}  # canvas edge id -> excalidraw arrow id
    label_ids = {}  # canvas edge id -> excalidraw label text id

    for node in nodes:
        rect_ids[node["id"]] = make_id()
        text_ids[node["id"]] = make_id()

    for edge in edges:
        arrow_ids[edge["id"]] = make_id()
        if edge.get("label"):
            label_ids[edge["id"]] = make_id()

    # Build arrow connections for each node's boundElements
    node_arrows = {}  # canvas node id -> list of (arrow_excalidraw_id, "arrow")
    for edge in edges:
        aid = arrow_ids[edge["id"]]
        node_arrows.setdefault(edge["fromNode"], []).append((aid, "arrow"))
        node_arrows.setdefault(edge["toNode"], []).append((aid, "arrow"))

    elements = []
    text_entries = []  # for the Text Elements section

    # Convert nodes -> rect + bound text
    for node in nodes:
        nid = node["id"]
        rid = rect_ids[nid]
        tid = text_ids[nid]
        raw_text = strip_markdown(node.get("text", ""))
        x, y = node["x"], node["y"]
        w, h = node["width"], node["height"]

        color_code = node.get("color")
        bg, stroke = COLOR_MAP.get(color_code, DEFAULT_COLOR) if color_code else DEFAULT_COLOR

        # boundElements: the text + any arrows
        bound = [(tid, "text")] + node_arrows.get(nid, [])

        rect = make_rect(rid, x, y, w, h, bg, stroke, bound)
        txt = make_text(tid, rid, x, y, w, h, raw_text)

        elements.append(rect)
        elements.append(txt)
        text_entries.append((raw_text, tid))

    # Convert edges -> arrows + optional labels
    for edge in edges:
        from_node = node_map.get(edge["fromNode"])
        to_node = node_map.get(edge["toNode"])
        if not from_node or not to_node:
            continue

        aid = arrow_ids[edge["id"]]
        from_side = edge.get("fromSide", "right")
        to_side = edge.get("toSide", "left")

        sx, sy = get_anchor(from_node, from_side)
        ex, ey = get_anchor(to_node, to_side)
        dx, dy = ex - sx, ey - sy

        label = edge.get("label")
        lid = label_ids.get(edge["id"])
        arrow_bound = [(lid, "text")] if lid else []

        arrow = make_arrow(aid, rect_ids[edge["fromNode"]], rect_ids[edge["toNode"]],
                           sx, sy, dx, dy, arrow_bound)
        elements.append(arrow)

        if label and lid:
            mid_x = sx + dx / 2
            mid_y = sy + dy / 2
            lbl = make_arrow_label(lid, aid, label, mid_x, mid_y)
            elements.append(lbl)
            text_entries.append((label, lid))

    # Build the Excalidraw drawing JSON
    drawing = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"},
        "files": {},
    }

    drawing_json = json.dumps(drawing, ensure_ascii=False)

    # Build Text Elements section: each entry is the text followed by ^id on the last line
    text_section_parts = []
    for raw_text, tid in text_entries:
        # The text content with ^id on the very last line
        text_section_parts.append(f"{raw_text} ^{tid}\n")

    text_section = "\n".join(text_section_parts)

    output = f"""---

excalidraw-plugin: parsed
tags: [excalidraw]

---
==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'


# Excalidraw Data

## Text Elements
{text_section}
%%
## Drawing
```json
{drawing_json}
```
%%
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    node_count = len(nodes)
    edge_count = len(edges)
    element_count = len(elements)
    print(f"Converted: {os.path.basename(canvas_path)} -> {os.path.basename(output_path)}")
    print(f"  {node_count} nodes, {edge_count} edges -> {element_count} excalidraw elements")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.canvas> [output.excalidraw.md]")
        sys.exit(1)

    canvas_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert(canvas_file, output_file)
