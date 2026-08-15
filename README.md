# BB Simple Paint

Paint or place any object as instances onto any surface, without geometry nodes — a Blender 4.5 extension.

Created by Blender Bob & Claude.

## Concept

Put your source objects in a collection (named `PaintItems` by default, configurable in the panel). Each item is a top-level object in that collection — a single mesh, or an object with children parented to it. `Simple Paint` panel is in `View3D > N Panel > Animation`.

Placed items are **linked duplicates**: they share mesh/data with their source (light on the file), but each one is a fully independent object you can select, move, delete, or edit on its own.

## Features

- **Paint On** — restrict painting to one chosen Base Mesh ("Selected Surface"), or let the brush hit anything in the scene ("Any Surface").
- **Orientation**
  - **Align** — how placed items are oriented: tilt to match the **Surface** normal, or always keep the item's up axis fixed to world **X**, **Y**, or **Z** regardless of surface tilt.
  - **Random Rotation** — independent X/Y/Z toggles; each enabled axis gets a random spin per item, on top of the alignment above.
  - **Random Scale** — Min/Max uniform scale factor, randomized per item.
- **Paint** — hold Left Mouse and drag to stamp a stream of items onto the surface under the brush. Release to stop, click again to start a new stroke, Right Mouse/Esc to exit.
  - **Size** — brush radius in world units.
  - **Density** — how tightly packed stamps are within the brush; also keeps a minimum spacing so items don't stack on top of each other.
  - **E** — toggle Paint/Erase without leaving the tool.
  - **F**, then move the mouse left/right, then click/Enter to confirm (or Esc/Right Mouse to cancel just the resize) — drag-resize the brush, same as Blender's sculpt/paint brushes. Mouse wheel also resizes.
  - **Tab** — switch straight to Place One without exiting.
- **Erase** — same brush and hotkeys as Paint, but removes any placed items under the cursor instead (works regardless of Paint On mode — it checks the brush circle on screen, not the surface).
- **Place One** — click and hold to drop a single item, drag while held to slide it around (snapped to whatever surface is under the cursor, respecting the same Align/Random Rotation/Random Scale settings, rolled once per item and kept while dragging), release to commit. Repeat to place more without reactivating the tool. **Tab** switches straight to Paint. Esc/Right Mouse exits (cancels only the item currently mid-drag, if any, keeping everything already dropped).
- Every stamp/placement picks a random item from the source collection, but never repeats one of the last 20 distinct picks (or fewer, if the collection is smaller) — no two identical items end up next to each other.

## Install

Download the release zip and install it via `Edit > Preferences > Get Extensions > Install from Disk`, or drag-and-drop the zip into Blender.
