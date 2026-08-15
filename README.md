# BB Simple Paint

Paint or place any object as instances onto any surface, without geometry nodes — a Blender 4.5 extension.

Created by Blender Bob & Claude.

## Concept

Put your source objects in a collection and pick it from the **Collection** dropdown in the panel. Each item is a top-level object in that collection — a single mesh, or an object with children parented to it. The `BB Simple Paint` panel is in `View3D > N Panel > Tool`.

Placed items are **linked duplicates**: they share mesh/data with their source (light on the file), but each one is a fully independent object you can select, move, delete, or edit on its own.

## Features

- **Paint On** — restrict painting to the currently **selected mesh object(s)** in the scene ("Selected Surface(s)" — select one or more objects before painting), or let the brush hit anything in the scene ("Any Surface").
- **Orientation and Scale**
  - **Align** — how placed items are oriented: tilt to match the **Surface** normal, always keep the item's up axis fixed to world **X**, **Y**, or **Z** regardless of surface tilt, or **Object** — point a chosen local axis of the item at a target object (pick it with the field's built-in eyedropper; choose which axis with the Axis dropdown).
  - **Random Rotation** — independent X/Y/Z toggles, each with its own Min/Max angle range, applied on top of the alignment above. **Sync** shares one range across every enabled axis (the row is labelled with the axes it actually drives), and editing it writes through to all of them.
  - **Random Scale** — independent X/Y/Z toggles, each with its own Min/Max factor, so you can scale only the axes you want (enabling only X and Y leaves Z at the source object's own scale). **Sync** applies one shared factor to every enabled axis so they stay proportional to each other, and edits write through to all of them; turn it off to give each axis its own range.
- **Spacing** — the minimum distance between items, in **world units**. This is the single density control and it is absolute, so painting a patch and flooding the whole surface land items at exactly the same density. Spacing 1.0 gives the same result on a 5 m plane and a 50 m plane.
- **Brush Size** — how large an *area* a paint stroke covers. It has **no effect on density** — a bigger brush covers more ground per stroke at the same spacing, it doesn't pack items tighter or looser.
- **Preview Spacing** — toggle a dot overlay on the selected surface(s) showing exactly where items would land at the current Spacing, so you can gauge density before committing. It switches itself off as soon as you start a stroke, so the dots never clutter what you are painting. The dots match what Flood would place one-for-one. **Dot Size** sets their on-screen size in pixels, so they stay equally readable however far you are from the surface.
- **Paint** — hold Left Mouse and drag to stamp a stream of items onto the surface under the brush. Release to stop, click again to start a new stroke, Right Mouse/Esc to exit.
  - **E** — toggle Paint/Erase without leaving the tool.
  - **F**, then move the mouse left/right, then click/Enter to confirm (or Esc/Right Mouse to cancel just the resize) — drag-resize the brush, same as Blender's sculpt/paint brushes. Mouse wheel also resizes.
  - **D** + mouse wheel — adjust Spacing, with the dot preview shown while D is held and restored to its previous state on release.
  - **Ctrl+Z / Ctrl+Shift+Z** — undo/redo without leaving the tool. Each stroke is its own undo step.
  - **Shift+F** — Flood the selected surface(s) without leaving the tool.
  - **Tab** — switch straight to Place One without exiting.
- **Erase** — same brush and hotkeys as Paint, but removes any placed items under the cursor instead (works regardless of Paint On mode — it checks the brush circle on screen, not the surface).
- **Flood** — one click covers the entire selected surface object(s) with items at the current Spacing. Only available when Paint On is "Selected Surface(s)".
- **Place One** — click and hold to drop a single item, drag while held to slide it around (snapped to whatever surface is under the cursor, respecting the same Align/Random Rotation/Random Scale settings, rolled once per item and kept while dragging), release to commit. Repeat to place more without reactivating the tool. Each drop is its own undo step, so **Ctrl+Z** removes one item at a time. **Tab** switches straight to Paint. Esc/Right Mouse exits (cancels only the item currently mid-drag, if any, keeping everything already dropped).
- Every stamp/placement picks a random item from the source collection, but never repeats one of the last 20 distinct picks (or fewer, if the collection is smaller) — no two identical items end up next to each other.

## Install

Download the release zip and install it via `Edit > Preferences > Get Extensions > Install from Disk`, or drag-and-drop the zip into Blender.
