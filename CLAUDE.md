# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

PyQGIS scripts for cartographic production tasks — contour label placement and atlas map sheet generation. Scripts are executed inside the **QGIS 3.44+ Python Console** (Plugins → Python Console, or `Ctrl+Alt+P`).

There is no build system, no package manager, and no test suite.

## contour_labeler

Generates slope-aligned contour labels at cartographically chosen positions. Load the script once to define the function, then call it repeatedly — one call per placement line:

```python
generate_slope_aligned_labels("5m_cont", "placelines")
```

**Layer requirements:**
- Contour layer: vector polylines with an elevation field named exactly `z` (case-sensitive).
- Placement layer: 2-vertex straight lines drawn uphill at desired label positions.

**Output:** Points are appended to a memory layer named `ContourLabelPoints` with `z` (elevation) and `rotation` attributes pre-configured for labelling. To prevent upside-down text, set "Show upside-down labels" → "when rotation defined" in the Layer Styling Panel.

`contour_labeler_v2.py` is a newer iteration of the same tool. `ContourLabelLadders.zip` contains a packaged version for distribution.

## map_sheets_along_route

Generates evenly spaced rectangular map sheets along a selected route polyline, ready for use as a QGIS Atlas coverage layer.

**Workflow:**
1. Select a single polyline (the route) in QGIS.
2. Run the script in the Python Console.
3. A memory layer named `map_sheets` is created — each feature is a 280 × 180 m rectangle (1:1000 scale) oriented perpendicular to the route, with `id` and `azi` fields.
4. Use `map_sheets` as the Atlas coverage layer in a Print Layout.
5. Set the map frame rotation expression to `(180 - "azi") % 360`. If rotation appears mirrored, use `(180 + "azi") % 360` instead.

See `map_sheets_along_route/readme.md` for the full Atlas layout setup procedure.

## Coordinate systems

Scripts assume a **metric projected CRS** (e.g. SWEREF 99 TM, EPSG:3006). Using WGS 84 degrees will produce incorrect sheet sizes and rotations.
