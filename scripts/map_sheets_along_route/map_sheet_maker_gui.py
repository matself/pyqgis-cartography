# ===============================================================
# MAP-SHEET GENERATOR FOR QGIS ATLAS  –  GUI version
# ---------------------------------------------------------------
# Purpose:
#   Generate evenly spaced, rectangular map sheets along a route.
#   Opens a dialog to configure width, height, overlap, and which
#   layer/feature to use before generating.
#
# Workflow:
#   1. Run this script in the QGIS Python Console.
#   2. Select layer and options in the dialog, then click Run.
#   3. A new memory layer "map_sheets" is created.
#   4. Use this layer as Atlas coverage layer.
#   5. In the Layout, set map rotation expression to:
#         (180 - "azi") % 360
#
# Collaboration:
#   Developed jointly through discussion between
#   Mats Elfström & ChatGPT (GPT-5), 2025.
#
# License:
#   Free to use and modify. Attribution appreciated.
# ===============================================================

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsWkbTypes
)
from qgis.PyQt.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QLabel, QCheckBox, QVBoxLayout, QGroupBox
)
from qgis.PyQt.QtCore import QVariant
import math


# ---------------------------------------------------------------
# GEOMETRY HELPER
# ---------------------------------------------------------------
def make_rect(center, azimuth_deg, width, height):
    """
    Rectangle centered on 'center', rotated by azimuth_deg
    (mathematical convention: 0° = east, CCW positive).
    """
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
# CORE GENERATOR
# ---------------------------------------------------------------
def generate_sheets(route_geom, crs_authid, width, height, overlap_pct):
    step = width * (1.0 - overlap_pct / 100.0)
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
        feat.setGeometry(make_rect(QgsPointXY(pt), azi + 90, width, height))
        prov.addFeature(feat)

        sheet_id += 1
        distance += step

    out.updateExtents()
    QgsProject.instance().addMapLayer(out)
    print(f"✅ Created {sheet_id - 1} map sheets.")
    print('Use rotation expression in layout:   (180 - "azi") % 360')


# ---------------------------------------------------------------
# GUI DIALOG
# ---------------------------------------------------------------
class MapSheetDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Map Sheet Generator")
        self.setMinimumWidth(360)

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

        self.selected_only = QCheckBox("Use selected feature only")
        self.selected_only.setChecked(True)

        layer_form.addRow("Layer:", self.layer_combo)
        layer_form.addRow("", self.selected_only)
        root.addWidget(layer_group)

        # --- Sheet parameters group ---
        param_group = QGroupBox("Sheet parameters")
        param_form  = QFormLayout(param_group)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setSuffix(" m")
        self.width_spin.setValue(280.0)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setSuffix(" m")
        self.height_spin.setValue(180.0)

        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setSuffix(" %")
        self.overlap_spin.setSingleStep(5)
        self.overlap_spin.setValue(10.0)

        param_form.addRow("Width:", self.width_spin)
        param_form.addRow("Height:", self.height_spin)
        param_form.addRow("Overlap:", self.overlap_spin)
        root.addWidget(param_group)

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

    def _run(self):
        idx = self.layer_combo.currentIndex()
        if idx < 0 or not self._line_layers:
            print("❌ No line layer found.")
            self.reject()
            return

        layer = self._line_layers[idx]

        if self.selected_only.isChecked():
            features = layer.selectedFeatures()
            if not features:
                print("❌ No feature selected. Select one polyline and try again.")
                return
            route_geom = features[0].geometry()
        else:
            features = list(layer.getFeatures())
            if not features:
                print("❌ Layer has no features.")
                return
            route_geom = QgsGeometry.collectGeometry([f.geometry() for f in features])

        generate_sheets(
            route_geom,
            layer.crs().authid(),
            self.width_spin.value(),
            self.height_spin.value(),
            self.overlap_spin.value(),
        )
        self.accept()


# ---------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------
dlg = MapSheetDialog()
dlg.show()
