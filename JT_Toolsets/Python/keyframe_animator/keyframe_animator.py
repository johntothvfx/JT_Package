"""
=======================================================================
DEVELOPER = 'John Toth'
VERSION   = '1.2.5'
UPDATED   = '30th May, 2025'


Keyframe Animator
=======================================================================
A Nuke tool for interactive keyframing.
Lets you pick any animatable knob on the selected node, add multiple frame/value pairs,
and quickly create or edit keyframes via a user-friendly PySide panel.
Supports batch keyframe entry with add/remove row controls, scrolling UI,
and single-click Apply.
Dropdown menu, preferences, and live shortcut integration included.
=======================================================================
"""


import nuke
import os
import json
import re


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


# ---- Preferences helpers ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PREFS_PATH = os.path.join(SCRIPT_DIR, "keyframe_animator_prefs.json")
DEFAULT_SHORTCUT = "Shift+Alt+K"


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


# ---- PySide2/6 imports ----
try:
   from PySide2.QtWidgets import (
       QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
       QLineEdit, QPushButton, QMessageBox, QSpacerItem, QSizePolicy,
       QScrollArea, QFrame
   )
   from PySide2.QtCore import Qt
   from PySide2.QtGui import QKeySequence
except ImportError:
   from PySide6.QtWidgets import (
       QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
       QLineEdit, QPushButton, QMessageBox, QSpacerItem, QSizePolicy,
       QScrollArea, QFrame
   )
   from PySide6.QtCore import Qt
   from PySide6.QtGui import QKeySequence


_keyframe_animator_window = None  # Prevent garbage collection


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


# --- Keyframe row ---
class KeyframeRow(QWidget):
   def __init__(self, frame=1, values=None, remove_callback=None, parent=None, component_count=1, knob_name=""):
       super(KeyframeRow, self).__init__(parent)
       self.remove_callback = remove_callback
       self.component_count = component_count
       self.knob_name = knob_name
       layout = QHBoxLayout(self)
       layout.setContentsMargins(0, 0, 0, 0)
       
       # Frame field
       self.frame_edit = QLineEdit(str(frame))
       self.frame_edit.setFixedWidth(60)
       layout.addWidget(QLabel("Frame:"))
       layout.addWidget(self.frame_edit)
       
       # Value fields based on component count
       self.value_edits = []
       
       # Ensure values is a list
       if values is None:
           values = [0.0] * component_count
       elif not isinstance(values, (list, tuple)):
           values = [values] * component_count
       
       if component_count == 1:
           # Single value
           layout.addWidget(QLabel("Value:"))
           value = values[0] if values and len(values) > 0 else 0.0
           value_edit = QLineEdit(str(value))
           value_edit.setFixedWidth(80)
           self.value_edits.append(value_edit)
           layout.addWidget(value_edit)
       else:
           # Multiple values with appropriate labels
           labels = self.get_component_labels(knob_name, component_count)
           for i in range(component_count):
               layout.addWidget(QLabel(f"{labels[i]}:"))
               value = values[i] if values and len(values) > i else 0.0
               value_edit = QLineEdit(str(value))
               value_edit.setFixedWidth(70)
               self.value_edits.append(value_edit)
               layout.addWidget(value_edit)
       
       # Remove button
       self.remove_btn = QPushButton("-")
       self.remove_btn.setFixedWidth(28)
       self.remove_btn.clicked.connect(self._remove_self)
       layout.addWidget(self.remove_btn)
       layout.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))

   def get_component_labels(self, knob_name, count):
       """Get appropriate labels for components based on knob name and count"""
       knob_lower = knob_name.lower()
       
       # Debug: print what we're checking
       print(f"Getting labels for knob: '{knob_name}' (count: {count})")
       
       # Define knob types and their appropriate labels - expanded list
       xyz_knobs = ['translate', 'rotate', 'scaling', 'scale', 'center', 'pivot', 'uniform_scale']
       xy_knobs = ['win_translate', 'win_scale', 'center2d']
       rgb_knobs = ['color', 'colour']
       
       if count == 2:
           # Check for XY knobs
           if any(xy in knob_lower for xy in xy_knobs):
               print(f"  -> Detected XY knob, using X,Y labels")
               return ['X', 'Y']
           # Check for general translate/scale patterns
           elif any(pattern in knob_lower for pattern in ['translate', 'scale', 'center']):
               print(f"  -> Detected 2D transform knob, using X,Y labels")
               return ['X', 'Y']
           else:
               print(f"  -> Using generic 2D labels")
               return ['0', '1']
       elif count == 3:
           # Check for XYZ knobs
           if any(xyz in knob_lower for xyz in xyz_knobs):
               print(f"  -> Detected XYZ knob, using X,Y,Z labels")
               return ['X', 'Y', 'Z']
           elif any(rgb in knob_lower for rgb in rgb_knobs):
               print(f"  -> Detected RGB knob, using R,G,B labels")
               return ['R', 'G', 'B']
           # Check for general 3D transform patterns
           elif any(pattern in knob_lower for pattern in ['translate', 'rotate', 'scale', 'center']):
               print(f"  -> Detected 3D transform knob, using X,Y,Z labels")
               return ['X', 'Y', 'Z']
           else:
               print(f"  -> Using generic 3D labels")
               return ['0', '1', '2']
       elif count == 4:
           if any(rgb in knob_lower for rgb in rgb_knobs):
               print(f"  -> Detected RGBA knob, using R,G,B,A labels")
               return ['R', 'G', 'B', 'A']
           else:
               print(f"  -> Using generic 4D labels")
               return ['0', '1', '2', '3']
       else:
           print(f"  -> Using generic {count}D labels")
           return [str(i) for i in range(count)]

   def _remove_self(self):
       if self.remove_callback:
           self.remove_callback(self)

   def get_data(self):
       try:
           frame = int(self.frame_edit.text())
       except Exception:
           frame = None
       
       values = []
       for value_edit in self.value_edits:
           try:
               value = float(value_edit.text())
               values.append(value)
           except Exception:
               values.append(0.0)  # Default to 0 instead of None
       
       return frame, values


# --- Preferences dialog ---
class KeyframeAnimatorPreferences(QWidget):
   def __init__(self, shortcut, on_save=None, on_cancel=None, parent=None):
       super(KeyframeAnimatorPreferences, self).__init__(parent)
       self.setWindowTitle("Keyframe Animator Preferences")
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


class KeyframeAnimatorUI(QWidget):
   EXCLUDED_KNOB_TYPES = [
       "Tab_Knob", "PyScript_Knob", "Text_Knob", "Help_Knob", "Script_Knob",
       "Eyedropper_Knob", "Histogram_Knob", "LookupCurves_Knob", "MultiView_Knob",
       "ViewView_Knob", "PythonKnob", "Password_Knob", "SceneView_Knob", "FreeType_Knob",
       "SceneGraph_Knob", "PathExpression_Knob", "Python_Knob", "Enumeration_Knob",
       "ChannelMask_Knob", "Channel_Knob", "Pulldown_Knob"
   ]
   EXCLUDED_KNOB_NAMES = [
       "bookmark", "cached", "dope_sheet", "gl_color", "hide_input",
       "knobChanged", "label", "lifetimeEnd", "lifetimeStart", "name",
       "note_font_color", "note_font_size", "onCreate", "onDestroy",
       "postage_stamp", "postage_static_frame", "postage_stamp_frame",
       "tile_color", "updateUI", "useLifetime", "xpos", "ypos",
       "export_as_gizmo", "lock_connections", "group_view_position",
       "show_group_view", "disable_group_view"
   ]
   
   # Add list of excluded node types
   EXCLUDED_NODE_TYPES = [
       "Viewer", "Viewer3D", "ViewerProcess", "CurveEditor", "DopeSheet",
       "Histogram", "Vectorfield", "Waveform", "BackgroundRender"
   ]


   def __init__(self, node, parent=None):
       super(KeyframeAnimatorUI, self).__init__(parent)
       self.setWindowTitle(f"Keyframe Animator v{VERSION}")
       self.setMinimumWidth(440)
       self.setMinimumHeight(350)
       self.node = node
       self.rows = []
       self.pref_widget = None
       
       # Set parent to Nuke's main window and smart stay-on-top behavior
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

       self.main_widget = QWidget(self)
       self._build_main_ui()

       main_layout = QVBoxLayout(self)
       main_layout.setContentsMargins(0,0,0,0)
       main_layout.addWidget(self.main_widget)
       self.setLayout(main_layout)

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
       
       return super(KeyframeAnimatorUI, self).eventFilter(obj, event)


   def _build_main_ui(self):
       main_layout = QVBoxLayout(self.main_widget)
       main_layout.setContentsMargins(10, 10, 10, 10)


       # Knob row
       knob_row = QHBoxLayout()
       knob_row.addWidget(QLabel("Knob:"))
       self.knob_combo = QComboBox()
       self.knobs = self.get_animatable_knobs()
       self.knob_combo.addItems(self.knobs)
       self.knob_combo.currentTextChanged.connect(self.on_knob_changed)
       knob_row.addWidget(self.knob_combo)
       knob_row.addStretch(1)
       main_layout.addLayout(knob_row)


       # Divider after knob
       divider1 = QFrame()
       divider1.setFrameShape(QFrame.HLine)
       divider1.setFrameShadow(QFrame.Sunken)
       main_layout.addWidget(divider1)


       # SCROLL AREA SETUP
       self.scroll_area = QScrollArea()
       self.scroll_area.setWidgetResizable(True)
       self.rows_widget = QWidget()
       self.rows_layout = QVBoxLayout(self.rows_widget)
       self.rows_layout.setContentsMargins(0, 0, 0, 0)
       self.scroll_area.setWidget(self.rows_widget)
       main_layout.addWidget(self.scroll_area, stretch=1)


       # Divider before Add
       divider2 = QFrame()
       divider2.setFrameShape(QFrame.HLine)
       divider2.setFrameShadow(QFrame.Sunken)
       main_layout.addWidget(divider2)


       # Add button styled to full width
       self.add_btn = QPushButton("Add")
       self.add_btn.setMinimumHeight(32)
       self.add_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
       self.add_btn.clicked.connect(self.add_row)
       main_layout.addWidget(self.add_btn)


       btn_row = QHBoxLayout()
       self.ok_btn = QPushButton("Apply")
       self.cancel_btn = QPushButton("Cancel")
       self.pref_btn = QPushButton("Preferences...")
       btn_row.addWidget(self.ok_btn)
       btn_row.addWidget(self.cancel_btn)
       btn_row.addWidget(self.pref_btn)
       main_layout.addLayout(btn_row)


       self.ok_btn.clicked.connect(self.apply_all_keyframes)
       self.cancel_btn.clicked.connect(self.close)
       self.pref_btn.clicked.connect(self.show_preferences)

       # Start with initial row
       self.add_row()


   def get_animatable_knobs(self):
       result = []
       for k in self.node.knobs().values():
           try:
               if k.getFlag(nuke.INVISIBLE) or not k.visible():
                   continue
               if k.Class() in self.EXCLUDED_KNOB_TYPES:
                   continue
               if k.name() in self.EXCLUDED_KNOB_NAMES:
                   continue
               if not all(hasattr(k, method) for method in ("setAnimated", "setValueAt", "setKeyAt")):
                   continue
               result.append(k.name())
           except Exception:
               continue
       return result
   
   def get_knob_components(self, knob_name):
       """Return the number of components for a knob"""
       if not knob_name:
           return 1
       knob = self.node.knob(knob_name)
       if knob and hasattr(knob, 'arraySize'):
           return knob.arraySize()
       return 1
   
   def get_current_knob_values(self, knob_name):
       """Get current values from the knob to use as defaults"""
       if not knob_name:
           return [0.0]
       knob = self.node.knob(knob_name)
       if not knob:
           return [0.0]
       
       try:
           if hasattr(knob, 'arraySize') and knob.arraySize() > 1:
               # Multi-component knob
               values = []
               for i in range(knob.arraySize()):
                   values.append(knob.getValue(i))
               return values
           else:
               # Single component knob
               return [knob.getValue()]
       except:
           # Fallback
           components = self.get_knob_components(knob_name)
           return [0.0] * components

   def on_knob_changed(self):
       """Called when knob selection changes - rebuild all rows with appropriate components"""
       # Clear existing rows
       for row in self.rows[:]:  # Create a copy of the list to iterate over
           self.remove_row(row)
       
       # Get current knob info
       current_knob = self.knob_combo.currentText()
       current_values = self.get_current_knob_values(current_knob)
       
       # Add a new row with the current knob values as defaults
       self.add_row(frame=nuke.frame(), values=current_values)

   def add_row(self, frame=None, values=None):
       if frame is None:
           frame = nuke.frame()
       
       # Get the number of components for the currently selected knob
       current_knob = self.knob_combo.currentText()
       component_count = self.get_knob_components(current_knob)
       
       # If no values provided, get current knob values or use defaults
       if values is None:
           values = self.get_current_knob_values(current_knob)
       
       # Ensure we have the right number of values
       if len(values) < component_count:
           values.extend([0.0] * (component_count - len(values)))
       elif len(values) > component_count:
           values = values[:component_count]
       
       row = KeyframeRow(
           frame=frame, 
           values=values, 
           remove_callback=self.remove_row, 
           component_count=component_count,
           knob_name=current_knob
       )
       self.rows.append(row)
       self.rows_layout.addWidget(row)


   def remove_row(self, row_widget):
       self.rows.remove(row_widget)
       self.rows_layout.removeWidget(row_widget)
       row_widget.setParent(None)
       row_widget.deleteLater()


   def apply_all_keyframes(self):
       knob_name = self.knob_combo.currentText()
       knob = self.node.knob(knob_name)
       
       if knob is None:
           QMessageBox.warning(self, "Error", "Knob not found on node.")
           return
       
       knob.setAnimated()
       count = 0
       data = []
       
       for row in self.rows:
           frame, values = row.get_data()
           if frame is None or not values:
               continue
           data.append((frame, values))
       
       data.sort(key=lambda x: x[0])  # sort by frame
       
       components = self.get_knob_components(knob_name)
       
       for frame, values in data:
           try:
               if components == 1:
                   # Single component knob
                   value = values[0] if values else 0.0
                   knob.setValueAt(value, frame)
                   knob.setKeyAt(frame)
               else:
                   # Multi-component knob
                   for i in range(min(components, len(values))):
                       knob.setValueAt(values[i], frame, i)
                       knob.setKeyAt(frame, i)
               count += 1
           except Exception as e:
               print("Skipping frame {}: {}".format(frame, e))
       
       # Create appropriate success message
       if components > 1:
           message = "Set {} keyframe(s) on all {} components of knob '{}'.".format(count, components, knob_name)
       else:
           message = "Set {} keyframe(s) on knob '{}'.".format(count, knob_name)
       
       QMessageBox.information(self, "Done", message)
       self.close()


   def show_preferences(self):
       prefs = load_preferences()
       shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
       if self.pref_widget:
           self.layout().removeWidget(self.main_widget)
           self.main_widget.setVisible(False)
           self.layout().removeWidget(self.pref_widget)
           self.pref_widget.deleteLater()
       self.pref_widget = KeyframeAnimatorPreferences(
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


# ----- Node type checker function -----
def is_node_supported(node):
    """Check if the node type is supported by the Keyframe Animator."""
    if not node:
        return False
    
    node_class = node.Class()
    excluded_types = KeyframeAnimatorUI.EXCLUDED_NODE_TYPES
    
    return node_class not in excluded_types


# ----- Live shortcut updater -----
def update_existing_shortcut(shortcut):
   """Try to update the menu shortcut live (ShortcutEditor method). Returns True if live update works."""
   try:
       menubar = nuke.menu("Nuke")
       utilities_menu = menubar.findItem("Utilities")
       if not utilities_menu:
           return False
       item = utilities_menu.findItem("Keyframe Animator")
       if not item:
           return False
       # QMenu/QAction technique: get the QAction and setShortcut on it
       qaction = getattr(item, "action", None)
       if qaction:
           qaction().setShortcut(QKeySequence(shortcut))
           return True
       # Fallback: try to find _action attribute (PySide2/6 compatibility)
       if hasattr(item, "_action"):
           item._action.setShortcut(QKeySequence(shortcut))
           return True
   except Exception as e:
       print("Failed to update menu shortcut:", e)
   return False


# ----- Menu registration -----
def keyframe_animator_launch():
   global _keyframe_animator_window
   try:
       sel = nuke.selectedNode()
   except Exception:
       QMessageBox.warning(None, "No node selected", "Please select a node first.")
       return
   
   # Check if the selected node type is supported
   if not is_node_supported(sel):
       node_type = sel.Class()
       QMessageBox.warning(
           None, 
           "Unsupported Node Type", 
           f"The Keyframe Animator does not work with '{node_type}' nodes.\n\n"
           f"This tool is designed for nodes that support keyframe animation."
       )
       return
   
   _keyframe_animator_window = KeyframeAnimatorUI(sel)
   _keyframe_animator_window.show()


# ----- MENU REGISTRATION -----
def register_menu():
    menubar = nuke.menu("Nuke")
    utilities_menu = menubar.addMenu("JT Package")
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    print("Keyframe Animator: registering menu with shortcut:", shortcut)
    utilities_menu.addCommand(
        "Keyframe Animator",
        lambda: keyframe_animator_launch(),
        shortcut
    )


register_menu()