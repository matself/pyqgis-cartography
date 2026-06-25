# Map Sheets Along Route

Generates a series of rotated map sheet polygons along a line route, suitable for use as an **Atlas coverage layer** in a QGIS Print Layout.

## Scripts

| File | Purpose |
|------|---------|
| `map_sheet_maker.py` | Original console script |
| `map_sheet_maker_gui.py` | GUI version (recommended) |

## Usage

1. Open the QGIS Python Console and run `map_sheet_maker_gui.py`.
2. In the dialog, select your route layer (line geometry), set print size in mm, map scale, and overlap %.
3. Click **Run** — a memory layer called `map_sheets` is added to the canvas with fields:
   - `id` — sheet number (sequential along route)
   - `azi` — geographic bearing of the sheet (0 = North, 90 = East, clockwise)
   - `x`, `y` — centre point coordinates

## Atlas setup in Print Layout

1. **Layout Manager** → New layout.
2. **Add Map** — draw a map frame and set its size (e.g. 280 x 180 mm).
3. **Atlas panel** → tick *Generate an atlas* → Coverage layer: `map_sheets` → Sort by: `id`.
4. **Map frame -> Item Properties** → *Controlled by atlas* ON, Margin = 0 %.
5. **Map frame -> Rotation** → click the data-defined button → Edit Expression:

```
(90 - "azi" + 360) % 360
```

6. Export via **Atlas -> Export Atlas as PDF**.

## CRS requirement

The route layer must use a **projected CRS in metres** (e.g. EPSG:3006 for Sweden). The sheet dimensions are specified in metres on the ground.
