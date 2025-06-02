"""
=======================================================================
DEVELOPER = 'John Toth'
VERSION   = '1.0.0'
UPDATED   = '31st May, 2025'

Set Label
=======================================================================
A Nuke utility for adding quick labels to selected nodes.
Allows you to type a custom label and instantly apply it to any selected
node. Includes a simple PySide-based UI with shortcut customization via 
Preferences.
=======================================================================
"""

import os
import json
import nuke
import re

try:
    from PySide2.QtWidgets import (
        QWidget, QLabel, QPushButton, QVBoxLayout, QLineEdit,
        QMessageBox, QHBoxLayout, QComboBox, QSizePolicy
    )
    from PySide2.QtGui import QKeySequence
    from PySide2.QtCore import Qt
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QLabel, QPushButton, QVBoxLayout, QLineEdit,
        QMessageBox, QHBoxLayout, QComboBox, QSizePolicy
    )
    from PySide6.QtGui import QKeySequence
    from PySide6.QtCore import Qt

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

DEFAULT_SHORTCUT = "Shift+Alt+N"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PREFS_PATH = os.path.join(SCRIPT_DIR, "set_label_prefs.json")

# Load/save prefs
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
        print("Could not save Set Label prefs:", e)

def update_existing_shortcut(shortcut):
    try:
        menubar = nuke.menu("Nuke")
        jt_menu = menubar.findItem("JT Package")
        if not jt_menu:
            return False
        item = jt_menu.findItem("Set Label")
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

# Reuse from keyframe animator
class KeySequenceButton(QPushButton):
    def __init__(self, shortcut, parent=None):
        super(KeySequenceButton, self).__init__(parent)
        self._recording = False
        self._keyseq = QKeySequence(shortcut)
        self.setText(self.pretty_seq(self._keyseq))
        self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(self.start_recording)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def pretty_seq(self, seq):
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
            return
        seq = QKeySequence(mods | key)
        self.setKeySequence(seq)
        self._recording = False

    def focusOutEvent(self, event):
        if self._recording:
            self.setText(self.pretty_seq(self._keyseq))
            self._recording = False
        super(KeySequenceButton, self).focusOutEvent(event)

class SetLabelPreferences(QWidget):
    def __init__(self, shortcut, on_save=None, on_cancel=None, parent=None):
        super(SetLabelPreferences, self).__init__(parent)
        self.setWindowTitle("Set Label Preferences")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.on_save = on_save
        self.on_cancel = on_cancel

        vlayout = QVBoxLayout(self)
        vlayout.setSpacing(8)
        vlayout.setContentsMargins(10, 10, 10, 10)

        # Metadata display
        version_label = QLabel(f"<b>Version:</b> {VERSION}<br><b>Developer:</b> {DEVELOPER}<br><b>Updated:</b> {UPDATED}")
        version_label.setWordWrap(True)
        vlayout.addWidget(version_label)

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

# Main label setter panel
class SetLabel(QWidget):
    def __init__(self, parent=None):
        super(SetLabel, self).__init__(parent)
        self.setWindowTitle("Set Label")
        self.setMinimumWidth(320)
        
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

        self.pref_widget = None
        self.main_widget = QWidget(self)
        self._build_main_ui()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.main_widget)

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
        
        return super(SetLabel, self).eventFilter(obj, event)

    def _build_main_ui(self):
        layout = QVBoxLayout(self.main_widget)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Append", "Overwrite"])
        layout.addWidget(QLabel("Mode:"))
        layout.addWidget(self.mode_combo)

        layout.addWidget(QLabel("Enter label:"))
        self.note_edit = QLineEdit()
        layout.addWidget(self.note_edit)

        btn_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.cancel_btn = QPushButton("Cancel")
        self.pref_btn = QPushButton("Preferences")
        btn_row.addWidget(self.apply_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.pref_btn)
        layout.addLayout(btn_row)

        self.apply_btn.clicked.connect(self.apply_label)
        self.cancel_btn.clicked.connect(self.close)
        self.pref_btn.clicked.connect(self.show_preferences)

    def apply_label(self):
        text = self.note_edit.text()
        if not text:
            QMessageBox.warning(self, "Warning", "Label cannot be empty.")
            return

        append = self.mode_combo.currentText() == "Append"
        count = 0
        for node in nuke.selectedNodes():
            knob = node.knob("label")
            if knob:
                existing = knob.value() if append else ""
                label = existing + ("\n" if existing and append else "") + text
                knob.setValue(label)
                count += 1

        QMessageBox.information(self, "Done", f"Label {'updated' if append else 'set'} on {count} node(s).")
        self.close()

    def show_preferences(self):
        self.layout().removeWidget(self.main_widget)
        self.main_widget.setVisible(False)
        if self.pref_widget:
            self.pref_widget.setParent(None)
            self.pref_widget.deleteLater()

        prefs = load_preferences()
        shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
        self.pref_widget = SetLabelPreferences(shortcut, on_save=self.show_main_ui, on_cancel=self.show_main_ui)
        self.layout().addWidget(self.pref_widget)
        self.pref_widget.setVisible(True)

    def show_main_ui(self):
        if self.pref_widget:
            self.layout().removeWidget(self.pref_widget)
            self.pref_widget.deleteLater()
            self.pref_widget = None
        self.main_widget.setVisible(True)
        self.layout().addWidget(self.main_widget)
        self.main_widget.raise_()

# Launcher
_set_label_window = None
def set_label_launch():
    global _set_label_window
    _set_label_window = SetLabel()
    _set_label_window.show()

# Menu registration
def register_menu():
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    menubar = nuke.menu("Nuke")
    package_menu = menubar.addMenu("JT Package")
    package_menu.addCommand("Set Label", lambda: set_label_launch(), shortcut)
    print("Set Label: registered with shortcut:", shortcut)

register_menu()