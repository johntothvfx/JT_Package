"""
=======================================================================
DEVELOPER = 'John Toth'
VERSION   = '1.2.9'
UPDATED   = '5th June, 2025'


Keyframe Animator
=======================================================================
A Nuke tool for interactive keyframing.
Lets you pick any animatable knob on the selected node, add multiple frame/value pairs,
and quickly create or edit keyframes via a user-friendly PySide panel.
Supports batch keyframe entry with add/remove row controls, scrolling UI,
and single-click Apply.
Dropdown menu, preferences, and live shortcut integration included.
Now includes dynamic color knob detection - treats collapsed color knobs as single component.
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
   def __init__(self, frame=1, values=None, remove_callback=None, parent=None, component_count=1, knob_obj=None, is_collapsed_color=False):
       super(KeyframeRow, self).__init__(parent)
       self.remove_callback = remove_callback
       self.component_count = component_count
       self.knob_obj = knob_obj
       self.knob_name = knob_obj.name() if knob_obj else ""
       self.is_collapsed_color = is_collapsed_color
       
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

       # Set actual component count properly - this is crucial for toggles
       if hasattr(self, 'actual_component_count'):
           # If it was passed from parent, keep it
           pass
       else:
           # Calculate it based on knob or values
           if knob_obj and hasattr(knob_obj, 'arraySize'):
               self.actual_component_count = knob_obj.arraySize()
           else:
               self.actual_component_count = max(len(values), component_count)

       # Build value fields
       self.build_value_fields(layout, values)

       # Add toggle button for toggleable knobs (next to remove button)
       if knob_obj and self.is_toggleable_knob(knob_obj):
           self.toggle_btn = QPushButton()
           self.toggle_btn.setFixedWidth(60)
           self.update_toggle_button_text()
           self.toggle_btn.clicked.connect(self.toggle_mode)
           layout.addWidget(self.toggle_btn)

       # Remove button
       self.remove_btn = QPushButton("-")
       self.remove_btn.setFixedWidth(28)
       self.remove_btn.clicked.connect(self._remove_self)
       layout.addWidget(self.remove_btn)
       layout.addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum))

   def is_toggleable_knob(self, knob):
       """Check if this knob supports toggle functionality"""
       if not knob:
           return False
       
       knob_class = knob.Class()
       return knob_class in ['Color_Knob', 'AColor_Knob', 'WH_Knob']

   def update_toggle_button_text(self):
       """Update toggle button text based on current mode and knob type"""
       if not hasattr(self, 'toggle_btn'):
           return
           
       knob_class = self.knob_obj.Class() if self.knob_obj else ""
       
       if self.is_collapsed_color:
           # Currently in single value mode
           if knob_class in ['Color_Knob', 'AColor_Knob']:
               self.toggle_btn.setText("→ RGBA")
               self.toggle_btn.setToolTip("Switch to individual R,G,B,A fields")
           elif knob_class == 'WH_Knob':
               self.toggle_btn.setText("→ W,H")
               self.toggle_btn.setToolTip("Switch to individual W,H fields")
       else:
           # Currently in individual component mode
           if knob_class in ['Color_Knob', 'AColor_Knob']:
               self.toggle_btn.setText("→ Single")
               self.toggle_btn.setToolTip("Switch to single value field")
           elif knob_class == 'WH_Knob':
               self.toggle_btn.setText("→ Size")
               self.toggle_btn.setToolTip("Switch to single size field")

   def build_value_fields(self, layout, values):
       """Build the value input fields based on current mode"""
       if self.is_collapsed_color:
           # Show as single value (applies to all components)
           knob_class = self.knob_obj.Class() if self.knob_obj else ""
           
           if knob_class in ['Color_Knob', 'AColor_Knob']:
               layout.addWidget(QLabel("value:"))
               tooltip_text = f"Single value - applies to all {self.actual_component_count} components"
           elif knob_class == 'WH_Knob':
               layout.addWidget(QLabel("size:"))
               tooltip_text = f"Single size - applies to both W and H"
           else:
               layout.addWidget(QLabel("value:"))
               tooltip_text = f"Single value - applies to all {self.actual_component_count} components"
           
           display_value = values[0] if values and len(values) > 0 else 0.0
           value_edit = QLineEdit(str(display_value))
           value_edit.setFixedWidth(80)
           value_edit.setToolTip(tooltip_text)
           self.value_edits.append(value_edit)
           layout.addWidget(value_edit)
       elif self.component_count == 1:
           # Single value
           layout.addWidget(QLabel("Value:"))
           value = values[0] if values and len(values) > 0 else 0.0
           value_edit = QLineEdit(str(value))
           value_edit.setFixedWidth(80)
           self.value_edits.append(value_edit)
           layout.addWidget(value_edit)
       else:
           # Multiple values with appropriate labels
           labels = self.get_component_labels(self.knob_obj, self.component_count)
           for i in range(self.component_count):
               label_widget = QLabel(f"{labels[i]}:")
               layout.addWidget(label_widget)
               value = values[i] if values and len(values) > i else 0.0
               value_edit = QLineEdit(str(value))
               value_edit.setFixedWidth(70)
               self.value_edits.append(value_edit)
               layout.addWidget(value_edit)

   def toggle_mode(self):
       """Toggle between single value and individual component modes for this row"""
       try:
           print(f"\n=== TOGGLE DEBUG ===")
           print(f"Before toggle - is_collapsed_color: {self.is_collapsed_color}")
           print(f"Before toggle - component_count: {self.component_count}")
           print(f"Before toggle - actual_component_count: {self.actual_component_count}")
           
           # Get current values before switching
           current_values = []
           if self.is_collapsed_color:
               # Currently collapsed - get the single value and apply to all components
               try:
                   single_value = float(self.value_edits[0].text())
                   current_values = [single_value] * self.actual_component_count
               except:
                   current_values = [0.0] * self.actual_component_count
           else:
               # Currently expanded - get all individual values
               for value_edit in self.value_edits:
                   try:
                       current_values.append(float(value_edit.text()))
                   except:
                       current_values.append(0.0)
               
               # Ensure we have enough values for all components
               while len(current_values) < self.actual_component_count:
                   current_values.append(current_values[0] if current_values else 0.0)
           
           print(f"Current values: {current_values}")
           
           # Toggle the mode
           self.is_collapsed_color = not self.is_collapsed_color
           
           # Update component count for display BEFORE rebuilding
           if self.is_collapsed_color:
               self.component_count = 1
           else:
               self.component_count = self.actual_component_count
           
           print(f"After toggle - is_collapsed_color: {self.is_collapsed_color}")
           print(f"After toggle - component_count: {self.component_count}")
           print(f"After toggle - actual_component_count: {self.actual_component_count}")
           
           # Update toggle button text
           self.update_toggle_button_text()
           
           # Rebuild the UI for this row
           self.rebuild_row_ui(current_values)
           
           print(f"=== TOGGLE COMPLETE ===\n")
           
       except Exception as e:
           print(f"Failed to toggle row mode: {e}")

   def rebuild_row_ui(self, values):
       """Rebuild this row's UI while preserving values"""
       layout = self.layout()
       
       # Store references to toggle and remove buttons before clearing
       toggle_btn = getattr(self, 'toggle_btn', None)
       remove_btn = getattr(self, 'remove_btn', None)
       
       # Remove only value-related widgets (labels and input fields between frame and buttons)
       items_to_remove = []
       
       # Find the positions of the toggle and remove buttons to know where to stop
       toggle_index = -1
       remove_index = -1
       spacer_index = -1
       
       for i in range(layout.count()):
           item = layout.itemAt(i)
           if item and item.widget():
               widget = item.widget()
               if widget == toggle_btn:
                   toggle_index = i
               elif widget == remove_btn:
                   remove_index = i
           elif item and item.spacerItem():
               spacer_index = i
       
       # Remove widgets between frame field (index 2) and buttons
       end_index = min([idx for idx in [toggle_index, remove_index, spacer_index] if idx > 0])
       
       for i in range(2, end_index):  # Start after frame field, stop before buttons
           item = layout.itemAt(2)  # Always remove item at index 2 as items shift down
           if item and item.widget():
               widget = item.widget()
               layout.removeWidget(widget)
               widget.setParent(None)
               widget.deleteLater()
           elif item:
               layout.removeItem(item)
       
       # Clear value edits list since we're rebuilding them
       self.value_edits = []
       
       # Build new value fields directly into the main layout at position 2
       insert_index = 2
       
       if self.is_collapsed_color:
           # Show as single value (applies to all components)
           knob_class = self.knob_obj.Class() if self.knob_obj else ""
           
           if knob_class in ['Color_Knob', 'AColor_Knob']:
               label_widget = QLabel("value:")
               tooltip_text = f"Single value - applies to all {self.actual_component_count} components"
           elif knob_class == 'WH_Knob':
               label_widget = QLabel("size:")
               tooltip_text = f"Single size - applies to both W and H"
           else:
               label_widget = QLabel("value:")
               tooltip_text = f"Single value - applies to all {self.actual_component_count} components"
           
           layout.insertWidget(insert_index, label_widget)
           insert_index += 1
           
           display_value = values[0] if values and len(values) > 0 else 0.0
           value_edit = QLineEdit(str(display_value))
           value_edit.setFixedWidth(80)
           value_edit.setToolTip(tooltip_text)
           self.value_edits.append(value_edit)
           layout.insertWidget(insert_index, value_edit)
           
       elif self.component_count == 1:
           # Single value
           label_widget = QLabel("Value:")
           layout.insertWidget(insert_index, label_widget)
           insert_index += 1
           
           value = values[0] if values and len(values) > 0 else 0.0
           value_edit = QLineEdit(str(value))
           value_edit.setFixedWidth(80)
           self.value_edits.append(value_edit)
           layout.insertWidget(insert_index, value_edit)
           
       else:
           # Multiple values with appropriate labels
           labels = self.get_component_labels(self.knob_obj, self.component_count)
           for i in range(self.component_count):
               label_widget = QLabel(f"{labels[i]}:")
               layout.insertWidget(insert_index, label_widget)
               insert_index += 1
               
               value = values[i] if values and len(values) > i else 0.0
               value_edit = QLineEdit(str(value))
               value_edit.setFixedWidth(70)
               self.value_edits.append(value_edit)
               layout.insertWidget(insert_index, value_edit)
               insert_index += 1

   def get_component_labels(self, knob, component_count):
       """Get appropriate labels based on knob class and component count"""
       if not knob:
           return [str(i) for i in range(component_count)]
       
       knob_class = knob.Class()
       knob_name_lower = knob.name().lower()
       
       # Color knobs - Always use RGBA regardless of name
       if knob_class in ['Color_Knob', 'AColor_Knob']:
           if component_count == 1:
               return ['Value']
           elif component_count == 3:
               return ['R', 'G', 'B']
           elif component_count == 4:
               return ['R', 'G', 'B', 'A']
           else:
               return [str(i) for i in range(component_count)]
       
       # Position/Transform knobs
       elif knob_class in ['XY_Knob', 'Double2_Knob']:
           return ['X', 'Y']
       
       elif knob_class in ['XYZ_Knob', 'Double3_Knob']:
           return ['X', 'Y', 'Z']
       
       elif knob_class == 'UV_Knob':
           return ['U', 'V']
       
       elif knob_class == 'WH_Knob':
           return ['W', 'H']
       
       # Single value knobs
       elif knob_class in ['Double_Knob', 'Int_Knob', 'Float_Knob', 'Range_Knob', 
                           'Log2_Knob', 'Exponential_Knob', 'Scale_Knob']:
           return ['Value']
       
       # BBox/Format knobs
       elif knob_class == 'BBox_Knob':
           if component_count == 4:
               return ['X', 'Y', 'R', 'T']  # left, bottom, right, top
           else:
               return [str(i) for i in range(component_count)]
       
       elif knob_class == 'Format_Knob':
           if component_count == 2:
               return ['W', 'H']  # width, height
           else:
               return [str(i) for i in range(component_count)]
       
       # Pattern-based detection for special cases
       elif component_count == 2:
           size_patterns = ['size', 'scale', 'translate', 'center', 'offset', 'blur']
           if any(pattern in knob_name_lower for pattern in size_patterns):
               return ['X', 'Y']
           
           uv_patterns = ['uv', 'st', 'texture']
           if any(pattern in knob_name_lower for pattern in uv_patterns):
               return ['U', 'V']
           
           wh_patterns = ['width', 'height', 'resolution']
           if any(pattern in knob_name_lower for pattern in wh_patterns):
               return ['W', 'H']
           
           return ['X', 'Y']
       
       elif component_count == 3:
           transform_3d_patterns = ['translate', 'rotate', 'scale', 'center', 'pivot']
           if any(pattern in knob_name_lower for pattern in transform_3d_patterns):
               return ['X', 'Y', 'Z']
           
           rgb_patterns = ['color', 'colour', 'rgb', 'tint', 'grade', 'lift', 'gain', 
                          'gamma', 'offset', 'multiply', 'add', 'blackpoint', 'whitepoint']
           if any(pattern in knob_name_lower for pattern in rgb_patterns):
               return ['R', 'G', 'B']
           
           return ['X', 'Y', 'Z']
       
       elif component_count == 4:
           rgba_patterns = ['color', 'colour', 'rgba', 'tint', 'grade', 'lift', 'gain',
                           'gamma', 'offset', 'multiply', 'add', 'blackpoint', 'whitepoint']
           if any(pattern in knob_name_lower for pattern in rgba_patterns):
               return ['R', 'G', 'B', 'A']
           
           transform_4d_patterns = ['matrix', 'quaternion', 'transform']
           if any(pattern in knob_name_lower for pattern in transform_4d_patterns):
               return ['X', 'Y', 'Z', 'W']
           
           return ['R', 'G', 'B', 'A']  # Default 4-component to RGBA
       
       elif component_count == 1:
           return ['Value']
       
       else:
           return [str(i) for i in range(component_count)]

   def _remove_self(self):
       if self.remove_callback:
           self.remove_callback(self)

   def get_data(self):
       try:
           frame = int(self.frame_edit.text())
       except Exception:
           frame = None

       values = []

       if self.is_collapsed_color:
           # For collapsed knobs, apply the single value to all components
           try:
               single_value = float(self.value_edits[0].text())
               values = [single_value] * self.actual_component_count
           except Exception:
               values = [0.0] * self.actual_component_count
       else:
           # Normal multi-component handling
           for value_edit in self.value_edits:
               try:
                   value = float(value_edit.text())
                   values.append(value)
               except Exception:
                   values.append(0.0)

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

       # Use Tool flag - stays on top of Nuke only, not other applications
       self.setWindowFlags(Qt.Tool)

       self.main_widget = QWidget(self)
       self._build_main_ui()

       main_layout = QVBoxLayout(self)
       main_layout.setContentsMargins(0,0,0,0)
       main_layout.addWidget(self.main_widget)
       self.setLayout(main_layout)

   def _build_main_ui(self):
       main_layout = QVBoxLayout(self.main_widget)
       main_layout.setContentsMargins(10, 10, 10, 10)

       # Knob row (no global toggle button)
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

       # Initialize the interface properly
       self.initialize_interface()

   def initialize_interface(self):
       """Initialize the interface properly on startup"""
       if self.knobs:
           self.on_knob_changed()
       else:
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
       if not knob:
           return 1

       if hasattr(knob, 'arraySize'):
           return knob.arraySize()
       return 1

   def is_toggleable_knob(self, knob):
       """Check if a knob supports toggle between single value and individual components"""
       if not knob:
           return False
       
       knob_class = knob.Class()
       return knob_class in ['Color_Knob', 'AColor_Knob', 'WH_Knob']

   def is_color_knob(self, knob):
       """Check if a knob is a color knob"""
       if not knob:
           return False
       knob_class = knob.Class()
       return knob_class in ['Color_Knob', 'AColor_Knob']

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
       for row in self.rows[:]:
           self.remove_row(row)

       # Get current knob info
       current_knob = self.knob_combo.currentText()
       current_knob_obj = self.node.knob(current_knob)
       current_values = self.get_current_knob_values(current_knob)

       # Add a new row with the current knob values as defaults
       self.add_row(frame=nuke.frame(), values=current_values)

   def add_row(self, frame=None, values=None):
       if frame is None:
           frame = nuke.frame()

       # Get the currently selected knob
       current_knob_name = self.knob_combo.currentText()
       current_knob_obj = self.node.knob(current_knob_name)

       # Determine display mode based on knob type
       actual_component_count = self.get_knob_components(current_knob_name)
       
       if self.is_color_knob(current_knob_obj) and current_knob_obj.singleValue():
           # COLLAPSED color knob -> single "value" field
           display_component_count = 1
           is_collapsed_color = True
       elif current_knob_obj and current_knob_obj.Class() == 'WH_Knob':
           # WH knobs default to individual W,H fields (can be toggled)
           display_component_count = actual_component_count
           is_collapsed_color = False
       else:
           # EXPANDED color knob or regular knob -> individual component fields
           display_component_count = actual_component_count
           is_collapsed_color = False

       # If no values provided, get current knob values or use defaults
       if values is None:
           values = self.get_current_knob_values(current_knob_name)

       # Ensure we have the right number of values for the actual knob
       if len(values) < actual_component_count:
           values.extend([0.0] * (actual_component_count - len(values)))
       elif len(values) > actual_component_count:
           values = values[:actual_component_count]

       row = KeyframeRow(
           frame=frame,
           values=values,
           remove_callback=self.remove_row,
           component_count=display_component_count,
           knob_obj=current_knob_obj,
           is_collapsed_color=is_collapsed_color
       )
       # Store the actual component count for keyframe application
       row.actual_component_count = actual_component_count
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

       # Get the actual number of components (not the display count)
       knob_obj = self.node.knob(knob_name)
       actual_components = knob_obj.arraySize() if hasattr(knob_obj, 'arraySize') else 1

       # Print animation summary to console
       print(f"\n=== KEYFRAME ANIMATOR - APPLYING ANIMATION ===")
       print(f"Node: {self.node.name()} ({self.node.Class()})")
       print(f"Knob: {knob_name} ({actual_components} component{'s' if actual_components != 1 else ''})")
       
       if self.is_color_knob(knob_obj):
           mode = "single value" if (self.rows and self.rows[0].is_collapsed_color) else "individual RGBA"
           print(f"Color knob mode: {mode}")
       
       print(f"Keyframes to apply: {len(data)}")
       
       for frame, values in data:
           try:
               if actual_components == 1:
                   # Single component knob
                   value = values[0] if values else 0.0
                   knob.setValueAt(value, frame)
                   knob.setKeyAt(frame)
                   print(f"  Frame {frame}: {value}")
               else:
                   # Multi-component knob
                   for i in range(min(actual_components, len(values))):
                       knob.setValueAt(values[i], frame, i)
                       knob.setKeyAt(frame, i)
                   # Print all component values for this frame
                   component_str = ", ".join([f"{values[i]:.3f}" for i in range(min(actual_components, len(values)))])
                   print(f"  Frame {frame}: [{component_str}]")
               count += 1
           except Exception as e:
               print(f"  Frame {frame}: FAILED - {e}")

       print(f"Successfully applied {count} keyframes")
       print(f"=== ANIMATION COMPLETE ===\n")

       # Create success message for user
       is_color_knob = self.is_color_knob(knob_obj)
       
       if is_color_knob and actual_components > 1:
           message = "Set {} keyframe(s) on color knob '{}' ({} components).".format(count, knob_name, actual_components)
       elif actual_components > 1:
           message = "Set {} keyframe(s) on all {} components of knob '{}'.".format(count, actual_components, knob_name)
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
   """Try to update the menu shortcut live. Returns True if live update works."""
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
    utilities_menu.addCommand(
        "Keyframe Animator",
        lambda: keyframe_animator_launch(),
        shortcut
    )


register_menu()
