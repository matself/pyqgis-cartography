# PyQGIS Cartography Scripts

A collection of PyQGIS scripts for professional cartographic workflows in QGIS. Each script is designed to be pasted into the QGIS Python Console and run interactively.

## Scripts

### [Slope-Aligned Contour Label Generator](scripts/contour_labeler/)

Generates slope-aligned elevation labels along user-drawn placement lines. Produces point features with correct rotation angles for highly readable, aesthetically pleasing contour labels — ready for direct use in QGIS label rendering.

**Key features:**
- Labels are placed at intersections of your drawn placement lines and the contour layer
- Rotation angle is calculated perpendicular to the placement line (slope direction)
- Output is a virtual point layer (`ContourLabelPoints`) with `z` and `rotation` attributes
- Designed for iterative use — run repeatedly, appending to the same output layer

**Requirements:**
- QGIS 3.10+ (works with older versions)
- A contour polyline layer with an elevation field named `z`
- A placement layer with 2-vertex lines drawn uphill

**Quick start:**
1. Load your contour layer and draw 2-vertex placement lines uphill where labels are needed
2. Select one placement line
3. Paste `contour_labeler.py` into the QGIS Python Console
4. Call `generate_slope_aligned_labels("your_contour_layer", "placelines")`
5. In Layer Styling, set *Show upside-down labels* → **"when rotation defined"**

---

### [Map Sheets Along Route](scripts/map_sheets_along_route/)

Generates evenly spaced, oriented rectangular map sheet polygons along a selected route line — for use as an Atlas coverage layer in QGIS Print Layout.

Each sheet is 280 × 180 m (matching a 1:1000 scale map at 280 × 180 mm), rotated perpendicular to the route with 10% overlap between sheets.

**Key features:**
- Sheets are auto-numbered and oriented to the route azimuth
- Outputs a `map_sheets` memory layer with `id`, `x`, `y`, and `azi` fields
- Pairs with the Atlas panel to produce a multi-page PDF, one page per sheet

**Requirements:**
- QGIS (any recent version)
- A projected CRS in metres (e.g. EPSG:3006)
- One selected polyline as the route

**Quick start:**
1. Select one polyline (the route)
2. Paste `map_sheet_maker.py` into the QGIS Python Console and run it
3. Use the resulting `map_sheets` layer as the Atlas coverage layer
4. In the Layout map frame, set rotation expression to `(180 - "azi") % 360`
5. Export Atlas → PDF

See the [step-by-step Atlas guide](scripts/map_sheets_along_route/readme.md) for full layout setup instructions.

---

## Requirements

- **QGIS** with Python console access
- Scripts are run directly in the **QGIS Python Console** — no plugin installation needed
- A projected CRS in metres is recommended for accurate geometry

## License

Free to use and modify. Attribution appreciated.

## Credits

Scripts developed through collaboration between Mats Elfström, Gemini, and ChatGPT (GPT-5).
