"""
=======================================================================
DEVELOPER = 'John Toth'
VERSION   = '1.0.0'
UPDATED   = '31st May, 2025'

Axis To Tracker
=======================================================================
Exports Tracker nodes using Camera and Axis selection.
Allows selection of multiple Cameras and Axis nodes, sets format,
frame range, and bakes 3D transforms into 2D Tracker nodes.
=======================================================================
"""
import nuke
import nukescripts
import os
import json
import math
import re

try:
    from PySide2.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox,
        QListWidget, QListWidgetItem, QFrame, QSizePolicy, QMessageBox, QLineEdit,
        QSpacerItem
    )
    from PySide2.QtCore import Qt
    from PySide2.QtGui import QKeySequence
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox,
        QListWidget, QListWidgetItem, QFrame, QSizePolicy, QMessageBox, QLineEdit,
        QSpacerItem
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence

# --- Metadata Parsing ---
def parse_metadata(docstring):
    metadata = {"VERSION": "Unknown", "DEVELOPER": "Unknown", "UPDATED": "Unknown"}
    matches = re.findall(r"^\s*(\w+)\s*=\s*['\"]([^'\"]+)['\"]", docstring, re.MULTILINE)
    for key, value in matches:
        if key in metadata:
            metadata[key] = value
    return metadata

metadata = parse_metadata(__doc__ or '')
VERSION = metadata["VERSION"]
DEVELOPER = metadata["DEVELOPER"]
UPDATED = metadata["UPDATED"]

PREFS_PATH = os.path.join(os.path.dirname(__file__), "axis_to_tracker_prefs.json")
DEFAULT_SHORTCUT = "Shift+Alt+T"

def load_preferences():
    if os.path.exists(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_preferences(prefs):
    try:
        with open(PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
    except Exception as e:
        print("Could not save preferences:", e)

def update_existing_shortcut(shortcut):
    try:
        menubar = nuke.menu("Nuke")
        jt_menu = menubar.findItem("JT Package")
        if not jt_menu:
            return False
        item = jt_menu.findItem("Axis To Tracker")
        if not item:
            return False
        qaction = getattr(item, "action", None)
        if qaction:
            qaction().setShortcut(QKeySequence(shortcut))
            return True
        if hasattr(item, "_action"):
            item._action.setShortcut(QKeySequence(shortcut))
            return True
    except Exception as e:
        print("Failed to update menu shortcut:", e)
    return False

# --- Key sequence button using ShortcutEditor technique ---
class KeySequenceButton(QPushButton):
    """Button that records and displays a Qt key sequence, using shortcuteditor technique for formatting."""
    def __init__(self, shortcut, parent=None):
        super(KeySequenceButton, self).__init__(parent)
        self._recording = False
        self._keyseq = QKeySequence(shortcut)
        self.setText(self.pretty_seq(self._keyseq))
        self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(self.start_recording)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def pretty_seq(self, seq):
        """Formats key sequence as 'Alt+Shift+J' (never {J}?)"""
        s = seq.toString(QKeySequence.NativeText)
        if not s or s.lower() == 'unknown':
            return "Set Shortcut..."
        # Remove stray braces if any
        s = s.replace("{", "").replace("}", "").replace("?", "")
        return s

    def keySequence(self):
        return self._keyseq

    def setKeySequence(self, seq):
        if isinstance(seq, QKeySequence):
            self._keyseq = seq
        else:
            self._keyseq = QKeySequence(seq)
        self.setText(self.pretty_seq(self._keyseq))

    def start_recording(self):
        self.setText("Press keys...")
        self._recording = True
        self.setFocus(Qt.ShortcutFocusReason)

    def keyPressEvent(self, event):
        if not self._recording:
            return super(KeySequenceButton, self).keyPressEvent(event)
        key = event.key()
        mods = event.modifiers()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            # Only modifier pressed: wait for key
            return
        seq = QKeySequence(mods | key)
        self.setKeySequence(seq)
        self._recording = False

    def focusOutEvent(self, event):
        if self._recording:
            self.setText(self.pretty_seq(self._keyseq))
            self._recording = False
        super(KeySequenceButton, self).focusOutEvent(event)

# --- Preferences dialog ---
class AxisToTrackerPreferences(QWidget):
    def __init__(self, shortcut, on_save=None, on_cancel=None, parent=None):
        super(AxisToTrackerPreferences, self).__init__(parent)
        self.setWindowTitle("Axis To Tracker Preferences")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(420)

        self.on_save = on_save
        self.on_cancel = on_cancel

        vlayout = QVBoxLayout(self)
        vlayout.setSpacing(8)

        # Version info
        version_label = QLabel(f"<b>Version:</b> {VERSION}<br><b>Developer:</b> {DEVELOPER}<br><b>Updated:</b> {UPDATED}")
        vlayout.addWidget(version_label)
        vlayout.addSpacing(8)

        # Shortcut row (label + button, button stretches to edge)
        sh_row = QHBoxLayout()
        sh_row.setSpacing(8)
        sh_row.addWidget(QLabel("Shortcut:"))
        self.shortcut_btn = KeySequenceButton(shortcut)
        sh_row.addWidget(self.shortcut_btn, stretch=1)
        vlayout.addLayout(sh_row)
        vlayout.addSpacing(2)

        # Reset to default, edge to edge
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_btn.clicked.connect(self.reset_to_default)
        vlayout.addWidget(self.reset_btn)
        vlayout.addSpacing(4)

        # Save/Cancel row, both buttons same width, aligned
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        vlayout.addLayout(btn_row)

        self.save_btn.clicked.connect(self.save)
        self.cancel_btn.clicked.connect(self.cancel)

    def reset_to_default(self):
        self.shortcut_btn.setKeySequence(QKeySequence(DEFAULT_SHORTCUT))

    def save(self):
        shortcut = self.shortcut_btn.keySequence().toString(QKeySequence.NativeText) or DEFAULT_SHORTCUT
        prefs = load_preferences()
        prefs["shortcut"] = shortcut
        save_preferences(prefs)
        updated = update_existing_shortcut(shortcut)
        if updated:
            QMessageBox.information(self, "Saved", f"Shortcut set to: {shortcut}")
        else:
            QMessageBox.information(self, "Saved", f"Shortcut set to: {shortcut}\nYou may need to restart Nuke to update the menu shortcut.")
        if self.on_save:
            self.on_save()
        else:
            self.close()

    def cancel(self):
        if self.on_cancel:
            self.on_cancel()
        else:
            self.close()

# --- Dockable Panel Widget for Nuke's Pane System ---
def createAxisToTrackerPanel():
    """Factory function to create the panel widget for Nuke's pane system"""
    return AxisToTrackerPanel()

def subRange(start, end, samples=0):
    """Generate frame range with subframe samples"""
    samples += 1
    step = 1.0 / samples
    rng = []
    for i in range(int(start), int(end)):
        rng.append(i)
        for j in range(1, int(samples)):
            rng.append(i + j * step)
    rng.append(end)
    return rng

class AxisToTrackerPanel(QWidget):
    def __init__(self):
        super(AxisToTrackerPanel, self).__init__()
        self.setWindowTitle("Axis To Tracker")
        self.setMinimumWidth(500)
        
        # Set parent to Nuke's main window
        self.nuke_main_window = None
        try:
            import nukescripts
            nuke_main_window = nukescripts.panels.findPanelWidget('DAG.1')
            if nuke_main_window:
                # Find the top-level window
                while nuke_main_window.parent():
                    nuke_main_window = nuke_main_window.parent()
                self.nuke_main_window = nuke_main_window
                self.setParent(nuke_main_window)
        except:
            pass
        
        # Use Tool flag with StaysOnTop - but we'll manage the behavior with events
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        
        # Install event filter on the main window to detect when Nuke loses focus
        if self.nuke_main_window:
            self.nuke_main_window.installEventFilter(self)
            
        self.pref_widget = None

        self.main_widget = QWidget(self)
        self._build_main_ui()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_widget)

    def eventFilter(self, obj, event):
        # When Nuke's main window loses focus (user switches to another app)
        if obj == self.nuke_main_window and event.type() == event.WindowDeactivate:
            # Temporarily remove stay on top behavior
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()  # Need to show after changing flags
        elif obj == self.nuke_main_window and event.type() == event.WindowActivate:
            # When Nuke regains focus, restore stay on top behavior
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()  # Need to show after changing flags
        
        return super(AxisToTrackerPanel, self).eventFilter(obj, event)

    def _build_main_ui(self):
        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.formats = [f.name() for f in nuke.formats() if f.name()]
        self.format_combo.addItems(self.formats)
        idx = self.format_combo.findText(nuke.root().format().name())
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        layout.addWidget(self.format_combo)

        fr_layout = QHBoxLayout()
        fr_layout.addWidget(QLabel("Frame Range:"))
        self.start_frame = QSpinBox(); self.start_frame.setRange(-9999, 999999); self.start_frame.setValue(nuke.root().firstFrame())
        self.end_frame = QSpinBox(); self.end_frame.setRange(-9999, 999999); self.end_frame.setValue(nuke.root().lastFrame())
        fr_layout.addWidget(self.start_frame)
        fr_layout.addWidget(QLabel("to"))
        fr_layout.addWidget(self.end_frame)
        fr_layout.addStretch()  # Add stretch to fill remaining space edge-to-edge
        layout.addLayout(fr_layout)

        sf_layout = QHBoxLayout()
        sf_layout.addWidget(QLabel("Sub-frame Samples:"))
        self.subframe_combo = QComboBox()
        self.subframe_combo.addItems(["0 (whole frames only)", "1 (0.5)", "2 (0.33, 0.66)", "3 (0.25, 0.5, 0.75)", "4 (0.2, 0.4, 0.6, 0.8)"])
        self.subframe_combo.setCurrentIndex(0)  # Default to whole frames only
        sf_layout.addWidget(self.subframe_combo)
        sf_layout.addStretch()  # Add stretch to fill remaining space edge-to-edge
        layout.addLayout(sf_layout)

        self.add_btn = QPushButton("Add Selected Camera/Axis Nodes")
        layout.addWidget(self.add_btn)

        divider = QFrame(); divider.setFrameShape(QFrame.HLine); layout.addWidget(divider)

        node_row = QHBoxLayout()
        self.camera_list = QListWidget()
        self.camera_list.setSelectionMode(QListWidget.MultiSelection)  # Enable multi-selection
        self.axis_list = QListWidget()
        self.axis_list.setSelectionMode(QListWidget.MultiSelection)  # Enable multi-selection
        node_row.addWidget(self.camera_list)
        node_row.addWidget(self.axis_list)
        layout.addLayout(node_row)

        remove_row = QHBoxLayout()
        self.remove_cam_btn = QPushButton("Remove Camera")
        self.remove_axis_btn = QPushButton("Remove Axis")
        remove_row.addWidget(self.remove_cam_btn)
        remove_row.addWidget(self.remove_axis_btn)
        layout.addLayout(remove_row)

        btn_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Tracker")
        self.cancel_btn = QPushButton("Cancel")
        self.pref_btn = QPushButton("Preferences...")
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.pref_btn)
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self.add_nodes)
        self.remove_cam_btn.clicked.connect(lambda: self.remove_selected(self.camera_list))
        self.remove_axis_btn.clicked.connect(lambda: self.remove_selected(self.axis_list))
        self.export_btn.clicked.connect(self.export_trackers)
        self.cancel_btn.clicked.connect(self.close)
        self.pref_btn.clicked.connect(self.show_preferences)

        # Auto-populate with currently selected nodes
        self.auto_populate_selected_nodes()

    def auto_populate_selected_nodes(self):
        """Automatically add any selected Camera or Axis nodes when panel opens"""
        for node in nuke.selectedNodes():
            if node.Class().startswith("Camera") and not self.in_list(node.name(), self.camera_list):
                self.camera_list.addItem(node.name())
                print(f"Auto-added Camera: {node.name()}")
            elif node.Class().startswith("Axis") and not self.in_list(node.name(), self.axis_list):
                self.axis_list.addItem(node.name())
                print(f"Auto-added Axis: {node.name()}")

    def add_nodes(self):
        for n in nuke.selectedNodes():
            if n.Class().startswith("Camera") and not self.in_list(n.name(), self.camera_list):
                self.camera_list.addItem(n.name())
            elif n.Class().startswith("Axis") and not self.in_list(n.name(), self.axis_list):
                self.axis_list.addItem(n.name())

    def in_list(self, name, list_widget):
        return any(list_widget.item(i).text() == name for i in range(list_widget.count()))

    def remove_selected(self, list_widget):
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))

    def export_trackers(self):
        format_name = self.format_combo.currentText()
        fmt = nuke.formats()[self.format_combo.currentIndex()]
        width = fmt.width()
        height = fmt.height()
        aspect = fmt.pixelAspect()
        halfW = width * 0.5
        halfH = height * 0.5

        start = self.start_frame.value()
        end = self.end_frame.value()
        subframe_samples = self.subframe_combo.currentIndex()  # Get selected subframe count
        
        # Generate frame range with subframes
        frame_range = subRange(start, end, subframe_samples)
        
        # Get selected cameras and axes, or all if none selected
        selected_cameras = [self.camera_list.item(i) for i in range(self.camera_list.count()) 
                           if self.camera_list.item(i).isSelected()]
        selected_axes = [self.axis_list.item(i) for i in range(self.axis_list.count()) 
                        if self.axis_list.item(i).isSelected()]
        
        # If nothing selected, use all items
        if not selected_cameras:
            selected_cameras = [self.camera_list.item(i) for i in range(self.camera_list.count())]
        if not selected_axes:
            selected_axes = [self.axis_list.item(i) for i in range(self.axis_list.count())]
            
        # Convert to actual node objects
        cameras = [nuke.toNode(item.text()) for item in selected_cameras]
        axes = [nuke.toNode(item.text()) for item in selected_axes]

        print("\n--- Export Debug Info ---")
        print("Format:", format_name)
        print("Frame Range:", start, "to", end)
        print("Sub-frame Samples:", subframe_samples)
        print("Total Frame Count (with subframes):", len(frame_range))
        print("Selected Cameras:", [c.name() for c in cameras])
        print("Selected Axes:", [a.name() for a in axes])

        # Create one tracker per camera
        trackers_created = 0
        
        # Calculate starting position for the trackers
        try:
            # Try to get a reference position from the first selected camera or axis
            if cameras:
                ref_node = cameras[0]
            elif axes:
                ref_node = axes[0]
            else:
                ref_node = None
                
            if ref_node:
                start_x = ref_node.xpos() + 150
                start_y = ref_node.ypos() + 100
            else:
                start_x = 0
                start_y = 0
        except:
            start_x = 0
            start_y = 0
        
        for cam_index, cam in enumerate(cameras):
            # Calculate position for this tracker (150 units apart horizontally)
            tracker_x = start_x + (cam_index * 150)
            tracker_y = start_y
            # Collect tracks for this specific camera
            camera_tracks_data = []
            
            for axis in axes:
                track_data = []
                for frame in frame_range:  # Use the subframe range instead of simple range
                    cam_matrix = nuke.math.Matrix4()
                    for i, v in enumerate(cam['world_matrix'].getValueAt(frame)):
                        cam_matrix[i] = v
                    axis_matrix = nuke.math.Matrix4()
                    for i, v in enumerate(axis['world_matrix'].getValueAt(frame)):
                        axis_matrix[i] = v
                    cam_inv = cam_matrix.inverse()
                    pos = nuke.math.Vector4(axis_matrix[3], axis_matrix[7], axis_matrix[11], 1)
                    local = cam_inv * pos
                    focal = cam['focal'].getValueAt(frame)
                    hap = cam['haperture'].getValueAt(frame)
                    roll = math.radians(cam['winroll'].getValueAt(frame))
                    scale_x = cam['win_scale'].getValueAt(frame, 0)
                    scale_y = cam['win_scale'].getValueAt(frame, 1)
                    trans_x = cam['win_translate'].getValueAt(frame, 0)
                    trans_y = cam['win_translate'].getValueAt(frame, 1)
                    d = -width * (focal / hap)
                    ratio = d / local.z
                    x = local.x * ratio
                    y = local.y * ratio
                    x = (x - trans_x * halfW) / scale_x
                    y = (y - trans_y * halfW) / scale_y
                    x_r = math.cos(roll) * x - math.sin(roll) * y
                    y_r = math.sin(roll) * x + math.cos(roll) * y
                    u = x_r + halfW
                    v = y_r * aspect + halfH
                    if frame == int(frame):  # Only print debug for whole frames to avoid spam
                        print(f"Frame {frame}: {axis.name()} -> {cam.name()} x = {u:.4f}, y = {v:.4f}")
                    track_data.append((frame, u, v))

                x_curve = ' '.join([f"x{f} {x}" for f, x, _ in track_data])
                y_curve = ' '.join([f"x{f} {y}" for f, _, y in track_data])
                
                # Store track info for this camera
                track_info = {
                    'name': axis.name(),  # Just use axis name since it's per-camera
                    'x_curve': x_curve,
                    'y_curve': y_curve
                }
                camera_tracks_data.append(track_info)

            # Build tracker script for this camera's tracks
            if camera_tracks_data:
                num_tracks = len(camera_tracks_data)
                
                # Build script string following the reference format
                scriptString = "{ 1 31 " + str(num_tracks) + " } \n"
                scriptString += "{ { 5 1 20 enable e 1 } \n"
                scriptString += "{ 3 1 75 name name 1 } \n"
                scriptString += "{ 2 1 58 track_x track_x 1 } \n"
                scriptString += "{ 2 1 58 track_y track_y 1 } \n"
                scriptString += "{ 2 1 63 offset_x offset_x 1 } \n"
                scriptString += "{ 2 1 63 offset_y offset_y 1 } \n"
                scriptString += "{ 4 1 27 T T 1 } \n"
                scriptString += "{ 4 1 27 R R 1 } \n"
                scriptString += "{ 4 1 27 S S 1 } \n"
                scriptString += "{ 2 0 45 error error 1 } \n"
                scriptString += "{ 1 1 0 error_min error_min 1 } \n"
                scriptString += "{ 1 1 0 error_max error_max 1 } \n"
                scriptString += "{ 1 1 0 pattern_x pattern_x 1 } \n"
                scriptString += "{ 1 1 0 pattern_y pattern_y 1 } \n"
                scriptString += "{ 1 1 0 pattern_r pattern_r 1 } \n"
                scriptString += "{ 1 1 0 pattern_t pattern_t 1 } \n"
                scriptString += "{ 1 1 0 search_x search_x 1 } \n"
                scriptString += "{ 1 1 0 search_y search_y 1 } \n"
                scriptString += "{ 1 1 0 search_r search_r 1 } \n"
                scriptString += "{ 1 1 0 search_t search_t 1 } \n"
                scriptString += "{ 2 1 0 key_track key_track 1 } \n"
                scriptString += "{ 2 1 0 key_search_x key_search_x 1 } \n"
                scriptString += "{ 2 1 0 key_search_y key_search_y 1 } \n"
                scriptString += "{ 2 1 0 key_search_r key_search_r 1 } \n"
                scriptString += "{ 2 1 0 key_search_t key_search_t 1 } \n"
                scriptString += "{ 2 1 0 key_track_x key_track_x 1 } \n"
                scriptString += "{ 2 1 0 key_track_y key_track_y 1 } \n"
                scriptString += "{ 2 1 0 key_track_r key_track_r 1 } \n"
                scriptString += "{ 2 1 0 key_track_t key_track_t 1 } \n"
                scriptString += "{ 2 1 0 key_centre_offset_x key_centre_offset_x 1 } \n"
                scriptString += "{ 2 1 0 key_centre_offset_y key_centre_offset_y 1 } \n"
                scriptString += "} \n{ \n"

                # Add each track for this camera
                for track in camera_tracks_data:
                    scriptString += " { {curve K x" + str(start) + " 1} \"" + track['name'] + "\" "
                    scriptString += "{curve " + track['x_curve'] + "} "
                    scriptString += "{curve " + track['y_curve'] + "} "
                    scriptString += "{}  {}  1 0 0 {}  0 0 0 0 0 0 0 0 0 0 "
                    scriptString += (11 * ("{curve 0 x" + str(start) + " 0} "))
                    scriptString += "   }\n"

                scriptString += "} \n"

                # Create tracker node for this camera
                t = nuke.createNode("Tracker4", inpanel=False)
                t['tracks'].fromScript(scriptString)
                
                # Disconnect all inputs to ensure clean tracker nodes
                t.setInput(0, None)
                if t.inputs() > 1:  # Some tracker nodes might have multiple inputs
                    for i in range(t.inputs()):
                        t.setInput(i, None)
                
                # Position the tracker node
                t.setXpos(tracker_x)
                t.setYpos(tracker_y)
                
                # Set camera-specific name and label
                if len(axes) > 1:
                    t.setName(f"Tracker_{cam.name()}_MultiAxis")
                else:
                    t.setName(f"Tracker_{cam.name()}_{axes[0].name()}")
                
                # Add camera name to label (append to existing label if any)
                existing_label = t['label'].value()
                camera_info = f"Camera: {cam.name()}"
                if existing_label:
                    t['label'].setValue(f"{existing_label}\n{camera_info}")
                else:
                    t['label'].setValue(camera_info)
                
                trackers_created += 1
                print(f"Created tracker '{t.name()}' with {num_tracks} tracks for camera '{cam.name()}' at position ({tracker_x}, {tracker_y})")

        if trackers_created > 0:
            print(f"\nSuccessfully created {trackers_created} tracker(s) - one per camera")
        else:
            print("No tracks to export!")

    def show_preferences(self):
        prefs = load_preferences()
        shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
        if self.pref_widget:
            self.layout().removeWidget(self.main_widget)
            self.main_widget.setVisible(False)
            self.layout().removeWidget(self.pref_widget)
            self.pref_widget.deleteLater()
        self.pref_widget = AxisToTrackerPreferences(
            shortcut,
            on_save=self.show_main_ui,
            on_cancel=self.show_main_ui
        )
        self.layout().addWidget(self.pref_widget)
        self.main_widget.setVisible(False)
        self.pref_widget.setVisible(True)

    def show_main_ui(self):
        if self.pref_widget:
            self.layout().removeWidget(self.pref_widget)
            self.pref_widget.deleteLater()
            self.pref_widget = None
        self.main_widget.setVisible(True)
        self.layout().addWidget(self.main_widget)
        self.main_widget.raise_()

_window_instance = None

def launch_axis_to_tracker():
    global _window_instance
    
    # Always launch as floating window
    if _window_instance is None or not _window_instance.isVisible():
        _window_instance = AxisToTrackerPanel()
        _window_instance.show()
    else:
        _window_instance.raise_()
        _window_instance.activateWindow()

def register_menu():
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    menubar = nuke.menu("Nuke")
    jt_menu = menubar.addMenu("JT Package")
    jt_menu.addCommand("Axis To Tracker", launch_axis_to_tracker, shortcut)
    
    # Register the panel widget with Nuke's pane system
    nukescripts.panels.registerWidgetAsPanel(
        'AxisToTrackerPanel',                    # Widget class name/ID
        'Axis To Tracker',                       # Display name in pane menu
        'uk.co.thefoundry.AxisToTrackerPanel',   # Unique panel ID  
        create=createAxisToTrackerPanel          # Factory function
    )

register_menu()