"""
=======================================================================
DEVELOPER = 'Your Name'
VERSION   = '1.1.3'
UPDATED   = '16th July, 2025'

Shuffle Node Manager
=======================================================================
A preferences system for enabling/disabling Shuffle nodes in Nuke.
Artists can choose which shuffle nodes (Shuffle, ShuffleCopy, Shuffle2) 
appear in the Channel menu and tab completion. Provides clean workflow 
control over legacy vs modern shuffle node availability.
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
PREFS_PATH = os.path.join(SCRIPT_DIR, "shuffle_manager_prefs.json")
DEFAULT_SHORTCUT = ""  # No default shortcut

def load_preferences():
    defaults = {
        "shuffle_enabled": True,
        "shufflecopy_enabled": True,
        "shuffle2_enabled": True,
        "default_shuffle": "shuffle",  # "shuffle" or "shuffle2"
        "shortcut": DEFAULT_SHORTCUT
    }
    
    if os.path.exists(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r") as f:
                prefs = json.load(f)
                for key, value in defaults.items():
                    if key not in prefs:
                        prefs[key] = value
                return prefs
        except Exception:
            return defaults
    return defaults

def save_preferences(prefs):
    try:
        with open(PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
    except Exception as e:
        print("Could not save preferences:", e)

# ---- Qt Detection ----
QT_AVAILABLE = False
try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QKeySequence, QFontMetrics, QFont
    from PySide6.QtWidgets import QApplication
    QT_AVAILABLE = True
    #print("Using PySide6")
except ImportError:
    try:
        from PySide2.QtWidgets import *
        from PySide2.QtCore import Qt, QTimer
        from PySide2.QtGui import QKeySequence, QFontMetrics, QFont
        from PySide2.QtWidgets import QApplication
        QT_AVAILABLE = True
        #print("Using PySide2")
    except ImportError:
        print("No Qt available - using fallback")

# ---- Menu Management ----
def clear_shuffle_menu_items():
    """Remove all shuffle-related menu items"""
    try:
        channel_menu = nuke.toolbar('Nodes').findItem('Channel')
        if channel_menu:
            shuffle_items = [
                'Shuffle', 'ShuffleCopy', 'Shuffle2',
                'Shuffle (Legacy)', 'ShuffleCopy (Legacy)', 'Shuffle2 (Modern)'
            ]
            
            for item_name in shuffle_items:
                try:
                    item = channel_menu.findItem(item_name)
                    if item:
                        channel_menu.removeItem(item_name)
                        print("Removed '{0}' from Channel menu".format(item_name))
                except:
                    pass
    except Exception as e:
        print("Error clearing shuffle menu items: {0}".format(e))

def register_enabled_shuffle_nodes():
    """Register ONLY the enabled shuffle nodes in the menu"""
    prefs = load_preferences()
    clear_shuffle_menu_items()
    
    version_compatible = nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12)
    
    print("=== Shuffle Node Registration ===")
    print("Shuffle enabled: {0}".format(prefs.get('shuffle_enabled', True)))
    print("ShuffleCopy enabled: {0}".format(prefs.get('shufflecopy_enabled', True)))
    print("Shuffle2 enabled: {0}".format(prefs.get('shuffle2_enabled', True)))
    print("Default shuffle: {0}".format(prefs.get('default_shuffle', 'shuffle')))
    
    # Count enabled nodes
    enabled_nodes = []
    if prefs.get("shuffle_enabled", True):
        enabled_nodes.append("shuffle")
    if prefs.get("shufflecopy_enabled", True):
        enabled_nodes.append("shufflecopy")
    if prefs.get("shuffle2_enabled", True) and version_compatible:
        enabled_nodes.append("shuffle2")
    
    multiple_nodes = len(enabled_nodes) > 1
    default_shuffle = prefs.get("default_shuffle", "shuffle")
    
    # Add the default shuffle node as "Shuffle" (no suffix)
    if default_shuffle == "shuffle2" and prefs.get("shuffle2_enabled", True) and version_compatible:
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode("Shuffle2")', icon='Shuffle.png')
        print("Added Shuffle (Shuffle2 default) to menu")
    elif default_shuffle == "shuffle" and prefs.get("shuffle_enabled", True):
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode("Shuffle")', icon='Shuffle.png')
        print("Added Shuffle (Legacy default) to menu")
    
    # Add non-default shuffle nodes with descriptive names
    if prefs.get("shuffle_enabled", True) and not (default_shuffle == "shuffle"):
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle (Legacy)', 'nuke.createNode("Shuffle")', icon='Shuffle.png')
        print("Added Shuffle (Legacy) to menu")
        
    if prefs.get("shuffle2_enabled", True) and version_compatible and not (default_shuffle == "shuffle2"):
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle2 (Modern)', 'nuke.createNode("Shuffle2")', icon='Shuffle.png')
        print("Added Shuffle2 (Modern) to menu")
        
    # ShuffleCopy is always added as just "ShuffleCopy" (no suffix needed)
    if prefs.get("shufflecopy_enabled", True):
        nuke.toolbar('Nodes').addCommand('Channel/ShuffleCopy', 'nuke.createNode("ShuffleCopy")', icon='ShuffleCopy.png')
        print("Added ShuffleCopy to menu")
    
    print("=== Registration Complete ===")

def update_existing_shortcut(shortcut):
    """Try to update the menu shortcut live"""
    try:
        menubar = nuke.menu("Nuke")
        jt_menu = menubar.findItem("JT Package")
        if not jt_menu:
            print("Could not find JT Package menu")
            return False
            
        item = jt_menu.findItem("Shuffle Node Manager")
        if not item:
            print("Could not find Shuffle Node Manager menu item")
            return False
        
        print("Found menu item, attempting to update shortcut to: '{0}'".format(shortcut))
        
        if QT_AVAILABLE:
            # Try multiple methods to update the shortcut
            updated = False
            
            # Method 1: Try action() method
            try:
                if hasattr(item, 'action') and callable(item.action):
                    qaction = item.action()
                    if qaction:
                        if shortcut and shortcut.strip():
                            qaction.setShortcut(QKeySequence(shortcut))
                            print("Method 1 success: Updated shortcut to '{0}'".format(shortcut))
                        else:
                            qaction.setShortcut(QKeySequence())
                            print("Method 1 success: Cleared shortcut")
                        updated = True
            except Exception as e:
                print("Method 1 failed: {0}".format(e))
            
            # Method 2: Try _action attribute
            if not updated:
                try:
                    if hasattr(item, '_action'):
                        qaction = item._action
                        if qaction:
                            if shortcut and shortcut.strip():
                                qaction.setShortcut(QKeySequence(shortcut))
                                print("Method 2 success: Updated shortcut to '{0}'".format(shortcut))
                            else:
                                qaction.setShortcut(QKeySequence())
                                print("Method 2 success: Cleared shortcut")
                            updated = True
                except Exception as e:
                    print("Method 2 failed: {0}".format(e))
            
            # Method 3: Try to recreate the menu item
            if not updated:
                try:
                    print("Attempting to recreate menu item...")
                    # Remove existing item
                    jt_menu.removeItem("Shuffle Node Manager")
                    
                    # Re-add with new shortcut
                    if shortcut and shortcut.strip():
                        jt_menu.addCommand("Shuffle Node Manager", show_shuffle_manager, shortcut)
                        print("Method 3 success: Recreated menu item with shortcut '{0}'".format(shortcut))
                    else:
                        jt_menu.addCommand("Shuffle Node Manager", show_shuffle_manager)
                        print("Method 3 success: Recreated menu item with no shortcut")
                    updated = True
                except Exception as e:
                    print("Method 3 failed: {0}".format(e))
            
            return updated
        else:
            print("Qt not available, cannot update shortcut")
            return False
            
    except Exception as e:
        print("Failed to update menu shortcut: {0}".format(e))
        return False

def register_menu():
    """Register the Shuffle Manager in the menu"""
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    menubar = nuke.menu("Nuke")
    
    # Menu structure - modify these lines to change where the tool appears
    jt_menu = menubar.addMenu("JT Package")
    jt_menu.addSeparator()
    utility_menu = jt_menu.addMenu("Utilities")
    
    if shortcut and shortcut.strip():
        utility_menu.addCommand("Shuffle Node Manager", show_shuffle_manager, shortcut)
        #print("Shuffle Node Manager registered with shortcut: {0}".format(shortcut))
    else:
        utility_menu.addCommand("Shuffle Node Manager", show_shuffle_manager)
        #print("Shuffle Node Manager registered (no shortcut)")
    

# ---- KeySequenceButton (From Set Label) ----
if QT_AVAILABLE:
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

    # ---- Preferences Panel (Set Label Style) ----
    class ShuffleManagerPreferences(QWidget):
        def __init__(self, shortcut, on_save=None, on_cancel=None, parent=None):
            super(ShuffleManagerPreferences, self).__init__(parent)
            self.setWindowTitle("Shuffle Node Manager Preferences")
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
            self.reset_btn = QPushButton("Clear Shortcut")
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
            self.shortcut_btn.setKeySequence(QKeySequence(""))

        def save(self):
            shortcut = self.shortcut_btn.keySequence().toString(QKeySequence.NativeText)
            prefs = load_preferences()
            prefs["shortcut"] = shortcut
            save_preferences(prefs)
            updated = update_existing_shortcut(shortcut)
            
            if updated:
                if shortcut:
                    QMessageBox.information(self, "Saved", f"Shortcut set to: {shortcut}")
                else:
                    QMessageBox.information(self, "Saved", "Shortcut cleared")
            else:
                if shortcut:
                    QMessageBox.information(self, "Saved", f"Shortcut set to: {shortcut}\nYou may need to restart Nuke to update the menu shortcut.")
                else:
                    QMessageBox.information(self, "Saved", "Shortcut cleared\nYou may need to restart Nuke to update the menu.")
            
            if self.on_save:
                self.on_save()
            else:
                self.close()

        def cancel(self):
            if self.on_cancel:
                self.on_cancel()
            else:
                self.close()

    # ---- Main Shuffle Manager UI ----
    class ShuffleManagerDialog(QWidget):
        def __init__(self, parent=None):
            super(ShuffleManagerDialog, self).__init__(parent)
            self.setWindowTitle(f'Shuffle Node Manager v{VERSION}')
            self.setMinimumWidth(400)
            
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
            
            return super(ShuffleManagerDialog, self).eventFilter(obj, event)

        def _build_main_ui(self):
            layout = QVBoxLayout(self.main_widget)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(15)
            
            # Header
            header = QLabel('Shuffle Node Manager')
            header.setStyleSheet('font-weight: bold; font-size: 16px;')
            layout.addWidget(header)
            
            desc = QLabel('Choose which shuffle nodes are available in the Channel menu and tab completion:')
            desc.setStyleSheet('color: #888; margin-bottom: 10px;')
            desc.setWordWrap(True)
            layout.addWidget(desc)
            
            # Node checkboxes
            nodes_group = QGroupBox('Available Shuffle Nodes')
            nodes_layout = QVBoxLayout()
            
            # Create a grid layout for checkboxes and radio buttons
            grid_layout = QGridLayout()
            
            # Headers
            grid_layout.addWidget(QLabel('<b>Enable</b>'), 0, 0)
            grid_layout.addWidget(QLabel('<b>Node Type</b>'), 0, 1)
            grid_layout.addWidget(QLabel('<b>Default</b>'), 0, 2)
            
            # Shuffle (Legacy)
            self.shuffle_checkbox = QCheckBox()
            self.shuffle_checkbox.setToolTip('Traditional Shuffle node')
            grid_layout.addWidget(self.shuffle_checkbox, 1, 0)
            grid_layout.addWidget(QLabel('Shuffle (Legacy)'), 1, 1)
            
            self.shuffle_radio = QRadioButton()
            self.shuffle_radio.setToolTip('Make Shuffle the default node accessed via "Shuffle"')
            grid_layout.addWidget(self.shuffle_radio, 1, 2)
            
            # ShuffleCopy
            self.shufflecopy_checkbox = QCheckBox()
            self.shufflecopy_checkbox.setToolTip('ShuffleCopy node')
            grid_layout.addWidget(self.shufflecopy_checkbox, 2, 0)
            grid_layout.addWidget(QLabel('ShuffleCopy'), 2, 1)
            # No radio button for ShuffleCopy - it's never the default "Shuffle"
            
            # Check Nuke version
            version_compatible = nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12)
            
            # Shuffle2 (Modern)
            self.shuffle2_checkbox = QCheckBox()
            if version_compatible:
                self.shuffle2_checkbox.setToolTip('Modern Shuffle2 node')
            else:
                self.shuffle2_checkbox.setToolTip('Requires Nuke 12.1+')
                self.shuffle2_checkbox.setEnabled(False)
                
            grid_layout.addWidget(self.shuffle2_checkbox, 3, 0)
            
            shuffle2_label = QLabel('Shuffle2 (Modern)')
            if not version_compatible:
                shuffle2_label.setStyleSheet('color: #666;')
            grid_layout.addWidget(shuffle2_label, 3, 1)
            
            self.shuffle2_radio = QRadioButton()
            if version_compatible:
                self.shuffle2_radio.setToolTip('Make Shuffle2 the default node accessed via "Shuffle"')
            else:
                self.shuffle2_radio.setEnabled(False)
            grid_layout.addWidget(self.shuffle2_radio, 3, 2)
            
            nodes_layout.addLayout(grid_layout)
            
            # Connect checkbox changes to update radio button availability
            self.shuffle_checkbox.toggled.connect(self.update_radio_buttons)
            self.shuffle2_checkbox.toggled.connect(self.update_radio_buttons)
            
            # Default explanation
            default_info = QLabel('Default: The node that appears as "Shuffle" in the menu')
            default_info.setStyleSheet('color: #666; font-style: italic; font-size: 10px;')
            nodes_layout.addWidget(default_info)
            
            if not version_compatible:
                warning = QLabel('⚠ Shuffle2 requires Nuke 12.1+')
                warning.setStyleSheet('color: #ff8800; font-style: italic;')
                nodes_layout.addWidget(warning)
            
            nodes_group.setLayout(nodes_layout)
            layout.addWidget(nodes_group)
            
            # Info
            info = QLabel('Changes take effect immediately. Restart Nuke if nodes don\'t appear in tab completion.')
            info.setStyleSheet('color: #666; font-style: italic; font-size: 11px;')
            info.setWordWrap(True)
            layout.addWidget(info)
            
            layout.addStretch()
            
            # Buttons
            button_layout = QHBoxLayout()
            
            self.reset_btn = QPushButton('Reset to Defaults')
            self.reset_btn.clicked.connect(self.reset_defaults)
            button_layout.addWidget(self.reset_btn)
            
            self.code_btn = QPushButton('Copy as Code...')
            self.code_btn.setToolTip('Generate Python code snippet for sharing this configuration')
            self.code_btn.clicked.connect(self.show_as_code)
            button_layout.addWidget(self.code_btn)
            
            self.pref_btn = QPushButton('Preferences')
            self.pref_btn.clicked.connect(self.show_preferences)
            button_layout.addWidget(self.pref_btn)
            
            button_layout.addStretch()
            
            cancel_btn = QPushButton('Cancel')
            cancel_btn.clicked.connect(self.close)
            button_layout.addWidget(cancel_btn)
            
            self.apply_btn = QPushButton('Apply')
            self.apply_btn.setDefault(True)
            self.apply_btn.clicked.connect(self.apply_settings)
            button_layout.addWidget(self.apply_btn)
            
            layout.addLayout(button_layout)
            
            self.load_settings()

        def update_radio_buttons(self):
            """Update radio button availability based on checkbox states"""
            # Only enable radio buttons for checked shuffle nodes
            self.shuffle_radio.setEnabled(self.shuffle_checkbox.isChecked())
            
            version_compatible = nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12)
            self.shuffle2_radio.setEnabled(self.shuffle2_checkbox.isChecked() and version_compatible)
            
            # If only one shuffle node is enabled, make it default automatically
            enabled_shuffles = []
            if self.shuffle_checkbox.isChecked():
                enabled_shuffles.append('shuffle')
            if self.shuffle2_checkbox.isChecked() and version_compatible:
                enabled_shuffles.append('shuffle2')
                
            if len(enabled_shuffles) == 1:
                # Auto-select the only enabled option
                if enabled_shuffles[0] == 'shuffle':
                    self.shuffle_radio.setChecked(True)
                    self.shuffle2_radio.setChecked(False)
                else:
                    self.shuffle2_radio.setChecked(True)
                    self.shuffle_radio.setChecked(False)
            elif len(enabled_shuffles) == 0:
                # No shuffle nodes enabled, clear all
                self.shuffle_radio.setChecked(False)
                self.shuffle2_radio.setChecked(False)

        def load_settings(self):
            """Load current preferences"""
            prefs = load_preferences()
            
            self.shuffle_checkbox.setChecked(prefs.get("shuffle_enabled", True))
            self.shufflecopy_checkbox.setChecked(prefs.get("shufflecopy_enabled", True))
            self.shuffle2_checkbox.setChecked(prefs.get("shuffle2_enabled", True))
            
            # Load default preference
            default_shuffle = prefs.get("default_shuffle", "shuffle")
            if default_shuffle == "shuffle2":
                self.shuffle2_radio.setChecked(True)
            else:
                self.shuffle_radio.setChecked(True)
                
            # Update radio button states
            self.update_radio_buttons()

        def reset_defaults(self):
            """Reset all settings to defaults"""
            self.shuffle_checkbox.setChecked(True)
            self.shufflecopy_checkbox.setChecked(True)
            self.shuffle2_checkbox.setChecked(True)
            self.shuffle_radio.setChecked(True)  # Default to Shuffle (Legacy)
            self.update_radio_buttons()

        def show_as_code(self):
            """Generate and show Python code snippet for current configuration"""
            # Get current settings from UI (live state, not saved preferences)
            current_prefs = {
                "shuffle_enabled": self.shuffle_checkbox.isChecked(),
                "shufflecopy_enabled": self.shufflecopy_checkbox.isChecked(),
                "shuffle2_enabled": self.shuffle2_checkbox.isChecked(),
                "default_shuffle": "shuffle2" if self.shuffle2_radio.isChecked() else "shuffle",
                "shortcut": load_preferences().get("shortcut", DEFAULT_SHORTCUT)
            }
            
            # Check if any shuffle nodes are enabled
            shuffle_nodes_enabled = current_prefs["shuffle_enabled"] or current_prefs["shuffle2_enabled"]
            
            if not shuffle_nodes_enabled and not current_prefs["shufflecopy_enabled"]:
                # No nodes enabled - show simple message
                QMessageBox.information(
                    self, 
                    "No Configuration", 
                    "No shuffle nodes are currently enabled.\n\nPlease enable at least one node to generate a code snippet."
                )
                return
            
            # Generate code snippet
            code_lines = [
                "# Shuffle Node Manager Snippet",
                "# Generated by Shuffle Node Manager v{0}".format(VERSION),
                "",
                "import nuke",
                "",
                "def setup_shuffle_nodes():",
                "    \"\"\"Configure shuffle nodes in Channel menu\"\"\"",
                "    try:",
                "        # Clear any existing shuffle menu items first",
                "        channel_menu = nuke.toolbar('Nodes').findItem('Channel')",
                "        if channel_menu:",
                "            shuffle_items = ['Shuffle', 'ShuffleCopy', 'Shuffle2', 'Shuffle (Legacy)', 'Shuffle2 (Modern)']",
                "            for item_name in shuffle_items:",
                "                try:",
                "                    if channel_menu.findItem(item_name):",
                "                        channel_menu.removeItem(item_name)",
                "                except:",
                "                    pass",
                "        ",
            ]
            
            # Add the actual configuration based on current UI state
            default_shuffle = current_prefs["default_shuffle"]
            
            # Add default shuffle node first (appears as just "Shuffle")
            if shuffle_nodes_enabled:
                if default_shuffle == "shuffle2" and current_prefs["shuffle2_enabled"]:
                    code_lines.extend([
                        "        # Add Shuffle2 as the default 'Shuffle' menu item",
                        "        if nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12):",
                        "            nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode(\"Shuffle2\")', icon='Shuffle.png')",
                        "",
                    ])
                elif default_shuffle == "shuffle" and current_prefs["shuffle_enabled"]:
                    code_lines.extend([
                        "        # Add Shuffle (Legacy) as the default 'Shuffle' menu item", 
                        "        nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode(\"Shuffle\")', icon='Shuffle.png')",
                        "",
                    ])
            
            # Add non-default shuffle nodes with descriptive names
            if current_prefs["shuffle_enabled"] and default_shuffle != "shuffle":
                code_lines.extend([
                    "        # Add Shuffle (Legacy) with descriptive name",
                    "        nuke.toolbar('Nodes').addCommand('Channel/Shuffle (Legacy)', 'nuke.createNode(\"Shuffle\")', icon='Shuffle.png')",
                    "",
                ])
                
            if current_prefs["shuffle2_enabled"] and default_shuffle != "shuffle2":
                code_lines.extend([
                    "        # Add Shuffle2 (Modern) with descriptive name",
                    "        if nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12):",
                    "            nuke.toolbar('Nodes').addCommand('Channel/Shuffle2 (Modern)', 'nuke.createNode(\"Shuffle2\")', icon='Shuffle.png')",
                    "",
                ])
            
            # Add ShuffleCopy if enabled
            if current_prefs["shufflecopy_enabled"]:
                code_lines.extend([
                    "        # Add ShuffleCopy",
                    "        nuke.toolbar('Nodes').addCommand('Channel/ShuffleCopy', 'nuke.createNode(\"ShuffleCopy\")', icon='ShuffleCopy.png')",
                    "",
                ])
            
            code_lines.extend([
                "        print('Shuffle nodes configured successfully')",
                "    except Exception as e:",
                "        print('Error setting up shuffle nodes: {0}'.format(e))",
                "",
                "# Run the setup when Nuke starts and loads scripts",
                "nuke.addOnScriptLoad(setup_shuffle_nodes)",
                "nuke.addOnCreate(setup_shuffle_nodes)",
                "",
                "# Run setup immediately",
                "setup_shuffle_nodes()",
            ])
            
            code_snippet = "\n".join(code_lines)
            
            # Create the custom code dialog
            self.show_code_dialog(current_prefs, code_snippet)

        def show_code_dialog(self, prefs, code_snippet):
            """Show a custom dialog with instructions and copyable code"""
            dialog = QDialog(self)
            dialog.setWindowTitle("Shuffle Node Manager - Configuration Code")
            dialog.setMinimumSize(600, 500)
            dialog.resize(700, 550)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)
            layout.setContentsMargins(15, 15, 15, 15)
            
            # Title
            title = QLabel("Configuration Code Generated!")
            title.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(title)
            
            # Configuration summary
            enabled_nodes = []
            if prefs["shuffle_enabled"]:
                enabled_nodes.append("Shuffle (Legacy)")
            if prefs["shufflecopy_enabled"]:
                enabled_nodes.append("ShuffleCopy") 
            if prefs["shuffle2_enabled"]:
                enabled_nodes.append("Shuffle2 (Modern)")
            
            shuffle_nodes_enabled = prefs["shuffle_enabled"] or prefs["shuffle2_enabled"]
            if shuffle_nodes_enabled:
                default_name = "Shuffle2 (Modern)" if prefs["default_shuffle"] == "shuffle2" else "Shuffle (Legacy)"
                summary_text = "This configuration will add: {0}\nDefault 'Shuffle' menu item: {1}".format(
                    ", ".join(enabled_nodes), default_name
                )
            else:
                summary_text = "This configuration will add: {0}".format(", ".join(enabled_nodes))
                
            summary = QLabel(summary_text)
            summary.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 5px;")
            summary.setWordWrap(True)
            layout.addWidget(summary)
            
            # Instructions
            instructions_title = QLabel("Instructions:")
            instructions_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 5px;")
            layout.addWidget(instructions_title)
            
            instructions_text = [
                "• Copy the code below using the 'Copy to Clipboard' button",
                "• Open your Nuke menu.py or init.py file",
                "• Paste the code at the end of the file",
                "• Save the file and restart Nuke",
                "• The shuffle nodes will be configured automatically"
            ]
            
            instructions = QLabel("\n".join(instructions_text))
            instructions.setStyleSheet("color: #555; font-size: 11px; margin-left: 10px; margin-bottom: 10px;")
            instructions.setWordWrap(True)
            layout.addWidget(instructions)
            
            # Divider line
            line = QLabel()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #ccc; margin: 5px 0;")
            layout.addWidget(line)
            
            # Code section title
            code_title = QLabel("Python Code:")
            code_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 3px;")
            layout.addWidget(code_title)
            
            # Code text area
            code_text = QTextEdit()
            code_text.setPlainText(code_snippet)
            code_text.setFont(QFont("Courier", 9))  # Slightly smaller monospace font
            code_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 8px;
                    font-family: 'Courier New', monospace;
                    font-size: 10px;
                    line-height: 1.3;
                }
            """)
            code_text.setReadOnly(True)
            layout.addWidget(code_text)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(8)
            
            copy_btn = QPushButton("Copy to Clipboard")
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(code_snippet, copy_btn))
            button_layout.addWidget(copy_btn)
            
            button_layout.addStretch()
            
            ok_btn = QPushButton("OK")
            ok_btn.setDefault(True)
            ok_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(ok_btn)
            
            layout.addLayout(button_layout)
            
            dialog.exec_()

        def copy_to_clipboard(self, text, button):
            """Copy text to clipboard and provide visual feedback"""
            try:
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                
                # Visual feedback - temporarily change button text
                original_text = button.text()
                button.setText("✓ Copied!")
                
                # Reset button after 2 seconds
                QTimer.singleShot(2000, lambda: button.setText(original_text))
                
            except Exception as e:
                QMessageBox.warning(self, "Copy Failed", "Could not copy to clipboard: {0}".format(str(e)))

        def reset_copy_button(self, button, original_text):
            """Reset copy button to original state"""
            button.setText(original_text)

        def show_preferences(self):
            self.layout().removeWidget(self.main_widget)
            self.main_widget.setVisible(False)
            if self.pref_widget:
                self.pref_widget.setParent(None)
                self.pref_widget.deleteLater()

            prefs = load_preferences()
            shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
            self.pref_widget = ShuffleManagerPreferences(shortcut, on_save=self.show_main_ui, on_cancel=self.show_main_ui)
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

        def apply_settings(self):
            """Apply the settings"""
            try:
                # Determine which shuffle node should be default
                default_shuffle = "shuffle"  # Default fallback
                if self.shuffle2_radio.isChecked():
                    default_shuffle = "shuffle2"
                elif self.shuffle_radio.isChecked():
                    default_shuffle = "shuffle"
                
                # Gather settings
                prefs = {
                    "shuffle_enabled": self.shuffle_checkbox.isChecked(),
                    "shufflecopy_enabled": self.shufflecopy_checkbox.isChecked(),
                    "shuffle2_enabled": self.shuffle2_checkbox.isChecked(),
                    "default_shuffle": default_shuffle,
                    "shortcut": load_preferences().get("shortcut", DEFAULT_SHORTCUT)  # Preserve existing shortcut
                }
                
                # Save preferences
                save_preferences(prefs)
                print("Saved preferences: {0}".format(prefs))
                
                # Refresh shuffle nodes
                register_enabled_shuffle_nodes()
                
                # Show success message
                enabled_nodes = []
                if prefs["shuffle_enabled"]:
                    enabled_nodes.append("Shuffle (Legacy)")
                if prefs["shufflecopy_enabled"]:
                    enabled_nodes.append("ShuffleCopy")
                if prefs["shuffle2_enabled"]:
                    enabled_nodes.append("Shuffle2 (Modern)")
                
                if enabled_nodes:
                    default_name = "Shuffle2" if default_shuffle == "shuffle2" else "Shuffle (Legacy)"
                    message = "Settings applied!\n\nEnabled nodes: {0}\nDefault: {1}".format(', '.join(enabled_nodes), default_name)
                else:
                    message = "Settings applied!\n\nAll shuffle nodes disabled"
                    
                self.close()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", "Failed to apply settings: {0}".format(str(e)))
                print("Error applying settings: {0}".format(e))

# ---- Main UI Functions ----
_shuffle_manager_window = None

def show_shuffle_manager():
    """Show the Shuffle Node Manager"""
    global _shuffle_manager_window
    
    if not QT_AVAILABLE:
        show_fallback_manager()
        return
    
    try:
        _shuffle_manager_window = ShuffleManagerDialog()
        _shuffle_manager_window.show()
    except Exception as e:
        print(f"Error creating Qt dialog: {e}")
        show_fallback_manager()

def show_fallback_manager():
    """Fallback UI when Qt is not available"""
    prefs = load_preferences()
    
    # Show current status
    enabled = []
    if prefs.get("shuffle_enabled", True):
        enabled.append("Shuffle")
    if prefs.get("shufflecopy_enabled", True):
        enabled.append("ShuffleCopy")
    if prefs.get("shuffle2_enabled", True):
        enabled.append("Shuffle2")
    
    current_status = "Currently enabled: " + ", ".join(enabled) if enabled else "No nodes enabled"
    
    # Create options
    options = [
        "Enable all shuffle nodes (Shuffle + ShuffleCopy + Shuffle2)",
        "Enable only legacy nodes (Shuffle + ShuffleCopy)",
        "Enable only modern node (Shuffle2 only)",
        "Enable only main Shuffle",
        "Disable all shuffle nodes",
        "Cancel"
    ]
    
    choice = nuke.choice(
        f"Shuffle Node Manager\n\n{current_status}\n\nChoose configuration:",
        "What would you like to do?",
        options
    )
    
    if choice == 0:  # Enable all
        prefs = {"shuffle_enabled": True, "shufflecopy_enabled": True, "shuffle2_enabled": True, "default_shuffle": "shuffle", "shortcut": prefs.get("shortcut", "")}
        save_preferences(prefs)
        register_enabled_shuffle_nodes()
        nuke.message("All shuffle nodes enabled!")
        
    elif choice == 1:  # Legacy only
        prefs = {"shuffle_enabled": True, "shufflecopy_enabled": True, "shuffle2_enabled": False, "default_shuffle": "shuffle", "shortcut": prefs.get("shortcut", "")}
        save_preferences(prefs)
        register_enabled_shuffle_nodes()
        nuke.message("Legacy shuffle nodes enabled!")
        
    elif choice == 2:  # Modern only
        prefs = {"shuffle_enabled": False, "shufflecopy_enabled": False, "shuffle2_enabled": True, "default_shuffle": "shuffle2", "shortcut": prefs.get("shortcut", "")}
        save_preferences(prefs)
        register_enabled_shuffle_nodes()
        nuke.message("Modern shuffle node enabled!")
        
    elif choice == 3:  # Main Shuffle only
        prefs = {"shuffle_enabled": True, "shufflecopy_enabled": False, "shuffle2_enabled": False, "default_shuffle": "shuffle", "shortcut": prefs.get("shortcut", "")}
        save_preferences(prefs)
        register_enabled_shuffle_nodes()
        nuke.message("Main Shuffle enabled!")
        
    elif choice == 4:  # Disable all
        prefs = {"shuffle_enabled": False, "shufflecopy_enabled": False, "shuffle2_enabled": False, "default_shuffle": "shuffle", "shortcut": prefs.get("shortcut", "")}
        save_preferences(prefs)
        register_enabled_shuffle_nodes()
        nuke.message("All shuffle nodes disabled!")

# ---- Initialization ----
def refresh_shuffle_menus():
    """Manually refresh shuffle menus"""
    print("Manually refreshing shuffle menus...")
    register_enabled_shuffle_nodes()
    print("Manual refresh complete")

def initialize_shuffle_menus():
    """Initialize shuffle menus based on preferences"""
    try:
        register_enabled_shuffle_nodes()
    except Exception as e:
        print("Error initializing shuffle menus: {0}".format(e))

# Register menu
register_menu()

# Multiple initialization points
nuke.addOnScriptLoad(initialize_shuffle_menus)
nuke.addOnScriptSave(initialize_shuffle_menus)
nuke.addOnCreate(initialize_shuffle_menus)

# Try immediate initialization
try:
    import threading
    timer = threading.Timer(0.5, initialize_shuffle_menus)
    timer.start()
except:
    pass

# Debug output
if QT_AVAILABLE:
    try:
        import PySide6
        print(f"Shuffle Node Manager loaded - PySide6 available")
    except ImportError:
        try:
            import PySide2
            print(f"Shuffle Node Manager loaded - PySide2 available")
        except ImportError:
            pass
else:
    print("Shuffle Node Manager loaded - No Qt libraries found, fallback interface available")

print("Use JT Package > Shuffle Node Manager to configure nodes")