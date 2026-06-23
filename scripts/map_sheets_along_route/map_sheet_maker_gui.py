# ===============================================================
# MAP-SHEET GENERATOR FOR QGIS ATLAS  -  GUI version
# ---------------------------------------------------------------
# Purpose:
#   Generate evenly spaced, rectangular map sheets along a route.
#   Sheet size is defined by print dimensions (mm) and map scale,
#   so ground coverage is derived automatically.
#   Supports selecting one or more line features as the route;
#   segments are automatically sorted and chained into a single
#   continuous polyline so numbering and rotation are consistent.
#
# Workflow:
#   1. Run this script in the QGIS Python Console.
#   2. Configure options in the dialog, then click Run.
#   3. A new memory layer "map_sheets" is created.
#   4. Use this layer as Atlas coverage layer.
#   5. In the Layout, set map rotation expression to:
#         (180 - "azi") % 360
#
# Collaboration:
#   Developed jointly through discussion between
#   Mats Elfstrom & ChatGPT (GPT-5), 2025.
#
# License:
#   Free to use and modify. Attribution appreciated.
# ===============================================================

from qgis.core import (
    Qgis,
    QgsProject, QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsWkbTypes,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling, QgsProperty
)
from qgis.PyQt.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox,
    QDialogButtonBox, QLabel, QCheckBox, QVBoxLayout, QGroupBox
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QFont, QColor
import math


# ---------------------------------------------------------------
# GEOMETRY HELPER
# ---------------------------------------------------------------
def make_rect(center, azimuth_deg, width, height):
    ang = math.radians(azimuth_deg)
    dx = math.sin(ang)
    dy = math.cos(ang)
    px =  dy
    py = -dx
    hw = width  / 2
    hh = height / 2
    p1 = QgsPointXY(center.x() + px*hw + dx*hh, center.y() + py*hw + dy*hh)
    p2 = QgsPointXY(center.x() - px*hw + dx*hh, center.y() - py*hw + dy*hh)
    p3 = QgsPointXY(center.x() - px*hw - dx*hh, center.y() - py*hw - dy*hh)
    p4 = QgsPointXY(center.x() + px*hw - dx*hh, center.y() + py*hw - dy*hh)
    return QgsGeometry.fromPolygonXY([[p1, p2, p3, p4]])


# ---------------------------------------------------------------
# LINE CHAINING
# ---------------------------------------------------------------
def chain_lines(geoms):
    """
    Sort and merge a list of line geometries into a single continuous
    polyline. Segments are chained greedily end-to-start; any segment
    whose end is closer to the current tip than its start is flipped.
    Returns a single QgsGeometry (LineString).
    """
    lines = []
    for g in geoms:
        if g.isMultipart():
            for part in g.asMultiPolyline():
                lines.append([QgsPointXY(p) for p in part])
        else:
            lines.append([QgsPointXY(p) for p in g.asPolyline()])

    if len(lines) == 1:
        return QgsGeometry.fromPolylineXY(lines[0])

    ordered = [lines.pop(0)]

    while lines:
        tip = ordered[-1][-1]
        best_idx, best_dist, best_flip = 0, float('inf'), False
        for i, line in enumerate(lines):
            d_start = tip.distance(line[0])
            d_end   = tip.distance(line[-1])
            if d_start < best_dist:
                best_dist, best_idx, best_flip = d_start, i, False
            if d_end < best_dist:
                best_dist, best_idx, best_flip = d_end, i, True

        seg = lines.pop(best_idx)
        if best_flip:
            seg = list(reversed(seg))
        ordered.append(seg)

    all_pts = ordered[0][:]
    for seg in ordered[1:]:
        all_pts.extend(seg[1:])

    return QgsGeometry.fromPolylineXY(all_pts)


# ---------------------------------------------------------------
# LABEL SETUP
# ---------------------------------------------------------------
def apply_labels(layer):
    pal = QgsPalLayerSettings()
    pal.fieldName = '"id"'
    pal.isExpression = True
    pal.placement = Qgis.LabelPlacement.Horizontal

    # Honour the data-defined rotation — don't auto-correct "upside-down" labels
    pal.upsidedownLabels = QgsPalLayerSettings.ShowDefined

    # Rotate label to match sheet orientation
    pal.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.LabelRotation,
        QgsProperty.fromExpression('(180 - "azi") % 360')
    )

    fmt = QgsTextFormat()
    font = QFont("Arial", 10, QFont.Bold)
    fmt.setFont(font)
    fmt.setSize(10)
    fmt.setColor(QColor("black"))

    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1)
    buf.setColor(QColor("white"))
    fmt.setBuffer(buf)

    pal.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
    layer.setLabelsEnabled(True)


# ---------------------------------------------------------------
# CORE GENERATOR
# ---------------------------------------------------------------
def generate_sheets(route_geom, crs_authid, width_m, height_m, overlap_pct):
    step = width_m * (1.0 - overlap_pct / 100.0)
    route_length = route_geom.length()

    out = QgsVectorLayer(f"Polygon?crs={crs_authid}", "map_sheets", "memory")
    prov = out.dataProvider()
    prov.addAttributes([
        QgsField("id",  QVariant.Int),
        QgsField("x",   QVariant.Double),
        QgsField("y",   QVariant.Double),
        QgsField("azi", QVariant.Double),
    ])
    out.updateFields()

    distance = 0
    sheet_id = 1
    while distance < route_length:
        pt  = route_geom.interpolate(distance).asPoint()
        pt2 = route_geom.interpolate(min(distance + 1, route_length)).asPoint()
        azi = math.degrees(math.atan2(pt2.x() - pt.x(), pt2.y() - pt.y()))

        feat = QgsFeature(out.fields())
        feat["id"]  = sheet_id
        feat["x"]   = pt.x()
        feat["y"]   = pt.y()
        feat["azi"] = azi
        feat.setGeometry(make_rect(QgsPointXY(pt), azi + 90, width_m, height_m))
        prov.addFeature(feat)

        sheet_id += 1
        distance += step

    out.updateExtents()
    apply_labels(out)
    QgsProject.instance().addMapLayer(out)
    print(f"Created {sheet_id - 1} map sheets "
          f"({width_m:.1f} x {height_m:.1f} m ground, step {step:.1f} m).")
    print('Use rotation expression in layout:   (180 - "azi") % 360')


# ---------------------------------------------------------------
# GUI DIALOG
# ---------------------------------------------------------------
class MapSheetDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Map Sheet Generator")
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)

        # --- Layer group ---
        layer_group = QGroupBox("Route layer")
        layer_form  = QFormLayout(layer_group)

        self.layer_combo = QComboBox()
        self._line_layers = [
            l for l in QgsProject.instance().mapLayers().values()
            if isinstance(l, QgsVectorLayer)
            and l.geometryType() == QgsWkbTypes.LineGeometry
        ]
        for l in self._line_layers:
            self.layer_combo.addItem(l.name())

        self.selected_only = QCheckBox("Use selected features only")
        self.selected_only.setChecked(True)

        layer_form.addRow("Layer:", self.layer_combo)
        layer_form.addRow("", self.selected_only)
        root.addWidget(layer_group)

        # --- Print / scale group ---
        print_group = QGroupBox("Print sheet size")
        print_form  = QFormLayout(print_group)

        self.print_width_spin = QDoubleSpinBox()
        self.print_width_spin.setRange(1, 10000)
        self.print_width_spin.setSuffix(" mm")
        self.print_width_spin.setValue(280.0)
        self.print_width_spin.valueChanged.connect(self._update_ground_label)

        self.print_height_spin = QDoubleSpinBox()
        self.print_height_spin.setRange(1, 10000)
        self.print_height_spin.setSuffix(" mm")
        self.print_height_spin.setValue(180.0)
        self.print_height_spin.valueChanged.connect(self._update_ground_label)

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(1, 1000000)
        self.scale_spin.setPrefix("1 : ")
        self.scale_spin.setSingleStep(500)
        self.scale_spin.setValue(1000)
        self.scale_spin.valueChanged.connect(self._update_ground_label)

        self.ground_label = QLabel()
        self.ground_label.setStyleSheet("color: gray;")
        self._update_ground_label()

        print_form.addRow("Width:", self.print_width_spin)
        print_form.addRow("Height:", self.print_height_spin)
        print_form.addRow("Scale:", self.scale_spin)
        print_form.addRow("Ground coverage:", self.ground_label)
        root.addWidget(print_group)

        # --- Overlap ---
        overlap_group = QGroupBox("Sheet overlap")
        overlap_form  = QFormLayout(overlap_group)

        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setSuffix(" %")
        self.overlap_spin.setSingleStep(5)
        self.overlap_spin.setValue(10.0)

        overlap_form.addRow("Overlap:", self.overlap_spin)
        root.addWidget(overlap_group)

        # --- Hint label ---
        hint = QLabel('Layout rotation: <tt>(180 - "azi") % 360</tt>')
        hint.setWordWrap(True)
        root.addWidget(hint)

        # --- Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Run")
        buttons.accepted.connect(self._run)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _ground_size(self):
        scale = self.scale_spin.value()
        w_m = self.print_width_spin.value()  * scale / 1000.0
        h_m = self.print_height_spin.value() * scale / 1000.0
        return w_m, h_m

    def _update_ground_label(self):
        w_m, h_m = self._ground_size()
        self.ground_label.setText(f"{w_m:.1f} x {h_m:.1f} m")

    def _run(self):
        idx = self.layer_combo.currentIndex()
        if idx < 0 or not self._line_layers:
            print("No line layer found.")
            self.reject()
            return

        layer = self._line_layers[idx]

        if self.selected_only.isChecked():
            features = layer.selectedFeatures()
            if not features:
                print("No features selected. Select one or more polylines and try again.")
                return
        else:
            features = list(layer.getFeatures())
            if not features:
                print("Layer has no features.")
                return

        route_geom = chain_lines([f.geometry() for f in features])

        w_m, h_m = self._ground_size()
        generate_sheets(
            route_geom,
            layer.crs().authid(),
            w_m,
            h_m,
            self.overlap_spin.value(),
        )
        self.accept()


# ---------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------
dlg = MapSheetDialog()
dlg.show()
