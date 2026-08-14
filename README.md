# BB PeopleLib

Paint crowd characters onto any surface, without geometry nodes — a Blender 4.5 extension.

Created by Blender Bob & Claude.

## Concept

Put your character objects in a collection called `PeopleLib` (configurable in the panel). Each character is a top-level object in that collection — a single mesh, or a rig with its mesh(es) parented as children. `PeopleLib` panel is in `View3D > N Panel > Animation`.

Painted characters are **linked duplicates**: they share mesh/armature data with their source (light on the file), but each one is a fully independent object you can select, move, delete, or pose/animate on its own — e.g. with [BB AnimBank](https://github.com/riouxr/BB_AnimBank).

## Features

- **Paint On** — restrict painting to one chosen Base Mesh ("Selected Surface"), or let the brush hit anything in the scene ("Any Surface").
- **Paint** — hold Left Mouse and drag to stamp a stream of characters onto the surface under the brush. Release to stop, click again to start a new stroke, Right Mouse/Esc to exit. Scroll the mouse wheel mid-stroke to change brush size.
  - **Size** — brush radius in world units.
  - **Density** — how tightly packed stamps are within the brush; also keeps a minimum spacing so characters don't stack on top of each other.
- **Place One Character** — click and hold to drop a single character, drag while held to slide it around (snapped to whatever surface is under the cursor), release to commit, Esc/Right Mouse to cancel.
- Every stamp picks a random character from `PeopleLib`, but never repeats one of the last 20 distinct picks (or fewer, if the library is smaller) — no two identical characters end up next to each other.
- Placed characters always keep their original upright orientation (no tilting to match slopes) — only their position snaps to the surface.

## Install

Download the release zip and install it via `Edit > Preferences > Get Extensions > Install from Disk`, or drag-and-drop the zip into Blender.
