"""
=======================================================================
DEVELOPER = 'John Toth'
VERSION   = '1.1.4'
UPDATED   = '18th July, 2025'

NAME: Shuffle Node Manager
STATUS: 'ACTIVE'
DEPENDENCIES: ['os', 'sys', 'nuke', 'pyside2', 'pyside6']
RELATED_MODULES: ['none']
LICENSE: 'MIT License'
PANEL_ID = 'JohnToth.shuffle_manager'
=======================================================================
DESCRIPTION: 
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
import sys

# =============================================================================
# DEBUG SYSTEM
# =============================================================================

# Debug mode - change to True to enable debug output
DEBUG_MODE = False

def tprint(message):
    """Debug print - only prints if DEBUG_MODE is True"""
    if DEBUG_MODE:
        print(f"ShuffleManager: {message}")

# =============================================================================
# METADATA PARSING
# =============================================================================

def parse_metadata(docstring):
    """Parse metadata from docstring header"""
    metadata = {"VERSION": "Unknown", "DEVELOPER": "Unknown", "UPDATED": "Unknown", "PANEL_ID": "unknown"}
    # Try both formats: KEY = 'value' and KEY: 'value'
    matches = re.findall(r"^\s*(\w+)\s*[=:]\s*['\"]([^'\"]+)['\"]", docstring, re.MULTILINE)
    for key, value in matches:
        if key in metadata:
            metadata[key] = value
    return metadata

# Extract metadata from docstring
metadata = parse_metadata(__doc__ or '')
VERSION = metadata["VERSION"]
DEVELOPER = metadata["DEVELOPER"]
UPDATED = metadata["UPDATED"]
PANEL_ID = metadata["PANEL_ID"]

# =============================================================================
# PACKAGE INFORMATION
# =============================================================================

# Package metadata
__version__ = VERSION
__author__ = DEVELOPER
__description__ = 'Shuffle Node Manager for Nuke'
__license__ = 'Pipeline Tools Internal Use'

# Package information
PACKAGE_NAME = 'ShuffleManager'
PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))

def get_package_info():
    """Get comprehensive package information"""
    return {
        'name': PACKAGE_NAME,
        'version': __version__,
        'author': __author__,
        'description': __description__,
        'license': __license__,
        'panel_id': PANEL_ID,
        'root_path': PACKAGE_ROOT,
        'debug_mode': DEBUG_MODE,
        'python_version': sys.version,
        'platform': sys.platform,
        'updated': UPDATED
    }

# =============================================================================
# PREFERENCES SYSTEM
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PREFS_PATH = os.path.join(SCRIPT_DIR, "shuffle_manager_prefs.json")
DEFAULT_SHORTCUT = ""

def load_preferences():
    """Load preferences from JSON file"""
    defaults = {
        "shuffle_enabled": True,
        "shufflecopy_enabled": True,
        "shuffle2_enabled": True,
        "default_shuffle": "shuffle",
        "shortcut": DEFAULT_SHORTCUT
    }
    
    if os.path.exists(PREFS_PATH):
        try:
            with open(PREFS_PATH, "r") as f:
                prefs = json.load(f)
                # Merge with defaults for missing keys
                for key, value in defaults.items():
                    if key not in prefs:
                        prefs[key] = value
                return prefs
        except Exception as e:
            tprint(f"Error loading preferences: {e}")
            return defaults
    return defaults

def save_preferences(prefs):
    """Save preferences to JSON file"""
    try:
        with open(PREFS_PATH, "w") as f:
            json.dump(prefs, f, indent=2)
        tprint(f"Preferences saved: {prefs}")
    except Exception as e:
        print(f"Could not save preferences: {e}")

# =============================================================================
# QT DETECTION
# =============================================================================

QT_AVAILABLE = False
Qt = None
QKeyCombination = None

try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QKeySequence, QFontMetrics, QFont
    from PySide6.QtWidgets import QApplication
    try:
        from PySide6.QtCore import QKeyCombination
    except ImportError:
        QKeyCombination = None
    QT_AVAILABLE = True
    tprint("Using PySide6")
except ImportError:
    try:
        from PySide2.QtWidgets import *
        from PySide2.QtCore import Qt, QTimer
        from PySide2.QtGui import QKeySequence, QFontMetrics, QFont
        from PySide2.QtWidgets import QApplication
        QKeyCombination = None  # Not available in PySide2
        QT_AVAILABLE = True
        tprint("Using PySide2")
    except ImportError:
        print("No Qt available - using fallback")

# =============================================================================
# MENU MANAGEMENT
# =============================================================================

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
                        tprint(f"Removed '{item_name}' from Channel menu")
                except:
                    pass
    except Exception as e:
        tprint(f"Error clearing shuffle menu items: {e}")

def register_enabled_shuffle_nodes():
    """Register only the enabled shuffle nodes in the menu"""
    prefs = load_preferences()
    clear_shuffle_menu_items()
    
    # Check Nuke version compatibility
    version_compatible = nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12)
    
    tprint("=== Shuffle Node Registration ===")
    tprint(f"Shuffle enabled: {prefs.get('shuffle_enabled', True)}")
    tprint(f"ShuffleCopy enabled: {prefs.get('shufflecopy_enabled', True)}")
    tprint(f"Shuffle2 enabled: {prefs.get('shuffle2_enabled', True)}")
    tprint(f"Default shuffle: {prefs.get('default_shuffle', 'shuffle')}")
    
    default_shuffle = prefs.get("default_shuffle", "shuffle")
    
    # Add the default shuffle node as "Shuffle" (no suffix)
    if default_shuffle == "shuffle2" and prefs.get("shuffle2_enabled", True) and version_compatible:
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode("Shuffle2")', icon='Shuffle.png')
        tprint("Added Shuffle (Shuffle2 default) to menu")
    elif default_shuffle == "shuffle" and prefs.get("shuffle_enabled", True):
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode("Shuffle")', icon='Shuffle.png')
        tprint("Added Shuffle (Legacy default) to menu")
    
    # Add non-default shuffle nodes with descriptive names
    if prefs.get("shuffle_enabled", True) and default_shuffle != "shuffle":
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle (Legacy)', 'nuke.createNode("Shuffle")', icon='Shuffle.png')
        tprint("Added Shuffle (Legacy) to menu")
        
    if prefs.get("shuffle2_enabled", True) and version_compatible and default_shuffle != "shuffle2":
        nuke.toolbar('Nodes').addCommand('Channel/Shuffle2 (Modern)', 'nuke.createNode("Shuffle2")', icon='Shuffle.png')
        tprint("Added Shuffle2 (Modern) to menu")
        
    # ShuffleCopy is always added as just "ShuffleCopy"
    if prefs.get("shufflecopy_enabled", True):
        nuke.toolbar('Nodes').addCommand('Channel/ShuffleCopy', 'nuke.createNode("ShuffleCopy")', icon='ShuffleCopy.png')
        tprint("Added ShuffleCopy to menu")
    
    tprint("=== Registration Complete ===")

def update_existing_shortcut(shortcut):
    """Try to update the menu shortcut live"""
    try:
        menubar = nuke.menu("Nuke")
        jt_menu = menubar.findItem("JT Package")
        if not jt_menu:
            tprint("Could not find JT Package menu")
            return False
            
        utility_menu = jt_menu.findItem("Utilities")
        if not utility_menu:
            tprint("Could not find Utilities menu")
            return False
            
        item = utility_menu.findItem("Shuffle Node Manager")
        if not item:
            tprint("Could not find Shuffle Node Manager menu item")
            return False
        
        tprint(f"Found menu item, attempting to update shortcut to: '{shortcut}'")
        
        # Method 1: Try to recreate the menu item (most reliable)
        try:
            tprint("Attempting to recreate menu item...")
            # Remove existing item
            utility_menu.removeItem("Shuffle Node Manager")
            
            # Re-add with new shortcut
            if shortcut and shortcut.strip():
                utility_menu.addCommand("Shuffle Node Manager", show_shuffle_manager, shortcut)
                tprint(f"Successfully recreated menu item with shortcut '{shortcut}'")
            else:
                utility_menu.addCommand("Shuffle Node Manager", show_shuffle_manager)
                tprint("Successfully recreated menu item with no shortcut")
            return True
        except Exception as e:
            tprint(f"Method 1 failed: {e}")
        
        # Method 2: Try to update existing shortcut via Qt (if available)
        if QT_AVAILABLE:
            try:
                if hasattr(item, 'action') and callable(item.action):
                    qaction = item.action()
                    if qaction:
                        if shortcut and shortcut.strip():
                            qaction.setShortcut(QKeySequence(shortcut))
                            tprint(f"Method 2 success: Updated shortcut to '{shortcut}'")
                        else:
                            qaction.setShortcut(QKeySequence())
                            tprint("Method 2 success: Cleared shortcut")
                        return True
            except Exception as e:
                tprint(f"Method 2 failed: {e}")
        
        return False
            
    except Exception as e:
        tprint(f"Failed to update menu shortcut: {e}")
        return False

def register_menu():
    """Register the Shuffle Manager in the menu"""
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    menubar = nuke.menu("Nuke")
    
    # Create menu structure
    jt_menu = menubar.addMenu("JT Package")
    jt_menu.addSeparator()
    utility_menu = jt_menu.addMenu("Utilities")
    
    if shortcut and shortcut.strip():
        utility_menu.addCommand("Shuffle Node Manager", show_shuffle_manager, shortcut)
        tprint(f"Panel {PANEL_ID} registered in menu with shortcut: {shortcut}")
    else:
        utility_menu.addCommand("Shuffle Node Manager", show_shuffle_manager)
        tprint(f"Panel {PANEL_ID} registered in menu (no shortcut)")

# =============================================================================
# UI COMPONENTS
# =============================================================================

if QT_AVAILABLE:
    class KeySequenceButton(QPushButton):
        """Button for capturing keyboard shortcuts"""
        def __init__(self, shortcut, parent=None):
            super(KeySequenceButton, self).__init__(parent)
            self._recording = False
            self._keyseq = QKeySequence(shortcut)
            self.setText(self.pretty_seq(self._keyseq))
            self.setFocusPolicy(Qt.StrongFocus)
            self.clicked.connect(self.start_recording)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        def pretty_seq(self, seq):
            """Format key sequence for display"""
            s = seq.toString(QKeySequence.NativeText)
            if not s or s.lower() == 'unknown':
                return "Set Shortcut..."
            return s.replace("{", "").replace("}", "").replace("?", "")

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
            
            # Handle PySide6 vs PySide2 key combination differences
            if QKeyCombination is not None:
                # PySide6 method - need to cast key to Qt.Key enum
                try:
                    seq = QKeySequence(QKeyCombination(mods, Qt.Key(key)))
                except (ValueError, TypeError):
                    # Fallback to PySide2 method if casting fails
                    seq = QKeySequence(mods | key)
            else:
                # PySide2 method
                seq = QKeySequence(mods | key)
            
            self.setKeySequence(seq)
            self._recording = False

        def focusOutEvent(self, event):
            if self._recording:
                self.setText(self.pretty_seq(self._keyseq))
                self._recording = False
            super(KeySequenceButton, self).focusOutEvent(event)

    class ShuffleManagerPreferences(QWidget):
        """Preferences panel for shortcut configuration"""
        def __init__(self, shortcut, on_save=None, on_cancel=None, parent=None):
            super(ShuffleManagerPreferences, self).__init__(parent)
            self.setWindowTitle("Shuffle Node Manager Preferences")
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

            self.on_save = on_save
            self.on_cancel = on_cancel

            vlayout = QVBoxLayout(self)
            vlayout.setSpacing(8)
            vlayout.setContentsMargins(10, 10, 10, 10)

            # Metadata display (original layout)
            version_label = QLabel(f"<b>Version:</b> {VERSION}<br><b>Developer:</b> {DEVELOPER}<br><b>Updated:</b> {UPDATED}<br><b>Panel ID:</b> {PANEL_ID}")
            version_label.setWordWrap(True)
            vlayout.addWidget(version_label)

            # Shortcut configuration
            sh_row = QHBoxLayout()
            sh_row.setSpacing(8)
            sh_row.addWidget(QLabel("Shortcut:"))
            self.shortcut_btn = KeySequenceButton(shortcut)
            sh_row.addWidget(self.shortcut_btn, stretch=1)
            vlayout.addLayout(sh_row)
            vlayout.addSpacing(2)

            # Clear button
            self.reset_btn = QPushButton("Clear Shortcut")
            self.reset_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.reset_btn.clicked.connect(self.reset_to_default)
            vlayout.addWidget(self.reset_btn)
            vlayout.addSpacing(4)

            # Save/Cancel buttons
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

            # Demo button - positioned after layout is complete
            self.demo_btn = QPushButton("Demo", self)
            self.demo_btn.clicked.connect(self.show_demo)
            self.demo_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.demo_btn.resize(60, 30)  # Fixed size

        def showEvent(self, event):
            """Position demo button when dialog is shown"""
            super(ShuffleManagerPreferences, self).showEvent(event)
            # Position demo button in top-right corner with some margin
            self.demo_btn.move(self.width() - self.demo_btn.width() - 15, 15)

        def reset_to_default(self):
            self.shortcut_btn.setKeySequence(QKeySequence(""))

        def show_demo(self):
            """Show demo - placeholder for now"""
            QMessageBox.information(self, "Demo", "Coming Soon!\n\nOnline demo and tutorial will be available soon.")

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

    class ShuffleManagerDialog(QWidget):
        """Main Shuffle Manager dialog"""
        def __init__(self, parent=None):
            super(ShuffleManagerDialog, self).__init__(parent)
            self.setWindowTitle(f'Shuffle Node Manager v{VERSION}')
            self.setMinimumWidth(400)
            
            # Parent to Nuke main window
            self.nuke_main_window = None
            try:
                import nukescripts
                nuke_main_window = nukescripts.panels.findPanelWidget('DAG.1')
                if nuke_main_window:
                    while nuke_main_window.parent():
                        nuke_main_window = nuke_main_window.parent()
                    self.nuke_main_window = nuke_main_window
                    self.setParent(nuke_main_window)
            except:
                pass
            
            # Smart stay-on-top behavior
            self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            
            if self.nuke_main_window:
                self.nuke_main_window.installEventFilter(self)

            self.pref_widget = None
            self.main_widget = QWidget(self)
            self._build_main_ui()

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.main_widget)

        def eventFilter(self, obj, event):
            """Handle window focus events for smart stay-on-top"""
            if obj == self.nuke_main_window:
                if event.type() == event.WindowDeactivate:
                    self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                    self.show()
                elif event.type() == event.WindowActivate:
                    self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                    self.show()
            
            return super(ShuffleManagerDialog, self).eventFilter(obj, event)

        def _build_main_ui(self):
            """Build the main UI"""
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
            
            # Node selection grid
            nodes_group = QGroupBox('Available Shuffle Nodes')
            nodes_layout = QVBoxLayout()
            
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
            
            # Shuffle2 (Modern)
            version_compatible = nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12)
            
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
            
            # Connect signals
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
            self.shuffle_radio.setEnabled(self.shuffle_checkbox.isChecked())
            
            version_compatible = nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12)
            self.shuffle2_radio.setEnabled(self.shuffle2_checkbox.isChecked() and version_compatible)
            
            # Auto-select default if only one option
            enabled_shuffles = []
            if self.shuffle_checkbox.isChecked():
                enabled_shuffles.append('shuffle')
            if self.shuffle2_checkbox.isChecked() and version_compatible:
                enabled_shuffles.append('shuffle2')
                
            if len(enabled_shuffles) == 1:
                if enabled_shuffles[0] == 'shuffle':
                    self.shuffle_radio.setChecked(True)
                    self.shuffle2_radio.setChecked(False)
                else:
                    self.shuffle2_radio.setChecked(True)
                    self.shuffle_radio.setChecked(False)
            elif len(enabled_shuffles) == 0:
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
                
            self.update_radio_buttons()

        def reset_defaults(self):
            """Reset all settings to defaults"""
            self.shuffle_checkbox.setChecked(True)
            self.shufflecopy_checkbox.setChecked(True)
            self.shuffle2_checkbox.setChecked(True)
            self.shuffle_radio.setChecked(True)
            self.update_radio_buttons()

        def show_as_code(self):
            """Generate and show Python code snippet"""
            current_prefs = {
                "shuffle_enabled": self.shuffle_checkbox.isChecked(),
                "shufflecopy_enabled": self.shufflecopy_checkbox.isChecked(),
                "shuffle2_enabled": self.shuffle2_checkbox.isChecked(),
                "default_shuffle": "shuffle2" if self.shuffle2_radio.isChecked() else "shuffle",
                "shortcut": load_preferences().get("shortcut", DEFAULT_SHORTCUT)
            }
            
            shuffle_nodes_enabled = current_prefs["shuffle_enabled"] or current_prefs["shuffle2_enabled"]
            
            if not shuffle_nodes_enabled and not current_prefs["shufflecopy_enabled"]:
                QMessageBox.information(
                    self, 
                    "No Configuration", 
                    "No shuffle nodes are currently enabled.\n\nPlease enable at least one node to generate a code snippet."
                )
                return
            
            # Generate code
            code_lines = [
                "# Shuffle Node Manager Snippet",
                f"# Generated by Shuffle Node Manager v{VERSION}",
                "",
                "import nuke",
                "",
                "def setup_shuffle_nodes():",
                "    \"\"\"Configure shuffle nodes in Channel menu\"\"\"",
                "    try:",
                "        # Clear existing shuffle menu items",
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
            
            default_shuffle = current_prefs["default_shuffle"]
            
            # Add default shuffle node
            if shuffle_nodes_enabled:
                if default_shuffle == "shuffle2" and current_prefs["shuffle2_enabled"]:
                    code_lines.extend([
                        "        # Add Shuffle2 as default 'Shuffle'",
                        "        if nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12):",
                        "            nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode(\"Shuffle2\")', icon='Shuffle.png')",
                        "",
                    ])
                elif default_shuffle == "shuffle" and current_prefs["shuffle_enabled"]:
                    code_lines.extend([
                        "        # Add Shuffle (Legacy) as default 'Shuffle'", 
                        "        nuke.toolbar('Nodes').addCommand('Channel/Shuffle', 'nuke.createNode(\"Shuffle\")', icon='Shuffle.png')",
                        "",
                    ])
            
            # Add non-default nodes
            if current_prefs["shuffle_enabled"] and default_shuffle != "shuffle":
                code_lines.extend([
                    "        # Add Shuffle (Legacy)",
                    "        nuke.toolbar('Nodes').addCommand('Channel/Shuffle (Legacy)', 'nuke.createNode(\"Shuffle\")', icon='Shuffle.png')",
                    "",
                ])
                
            if current_prefs["shuffle2_enabled"] and default_shuffle != "shuffle2":
                code_lines.extend([
                    "        # Add Shuffle2 (Modern)",
                    "        if nuke.NUKE_VERSION_MAJOR >= 12 and ((nuke.NUKE_VERSION_MAJOR + nuke.NUKE_VERSION_MINOR) > 12):",
                    "            nuke.toolbar('Nodes').addCommand('Channel/Shuffle2 (Modern)', 'nuke.createNode(\"Shuffle2\")', icon='Shuffle.png')",
                    "",
                ])
            
            if current_prefs["shufflecopy_enabled"]:
                code_lines.extend([
                    "        # Add ShuffleCopy",
                    "        nuke.toolbar('Nodes').addCommand('Channel/ShuffleCopy', 'nuke.createNode(\"ShuffleCopy\")', icon='ShuffleCopy.png')",
                    "",
                ])
            
            code_lines.extend([
                "        print('Shuffle nodes configured successfully')",
                "    except Exception as e:",
                "        print(f'Error setting up shuffle nodes: {e}')",
                "",
                "# Initialize",
                "nuke.addOnScriptLoad(setup_shuffle_nodes)",
                "nuke.addOnCreate(setup_shuffle_nodes)",
                "setup_shuffle_nodes()",
            ])
            
            code_snippet = "\n".join(code_lines)
            self.show_code_dialog(current_prefs, code_snippet)

        def show_code_dialog(self, prefs, code_snippet):
            """Show code generation dialog"""
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
            
            # Summary
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
                summary_text = f"This configuration will add: {', '.join(enabled_nodes)}\nDefault 'Shuffle' menu item: {default_name}"
            else:
                summary_text = f"This configuration will add: {', '.join(enabled_nodes)}"
                
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
            
            # Divider
            line = QLabel()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #ccc; margin: 5px 0;")
            layout.addWidget(line)
            
            # Code section
            code_title = QLabel("Python Code:")
            code_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 3px;")
            layout.addWidget(code_title)
            
            code_text = QTextEdit()
            code_text.setPlainText(code_snippet)
            code_text.setFont(QFont("Courier", 9))
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
            """Copy text to clipboard with visual feedback"""
            try:
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                
                original_text = button.text()
                button.setText("✓ Copied!")
                QTimer.singleShot(2000, lambda: button.setText(original_text))
                
            except Exception as e:
                QMessageBox.warning(self, "Copy Failed", f"Could not copy to clipboard: {e}")

        def show_preferences(self):
            """Show preferences panel"""
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
            """Show main UI"""
            if self.pref_widget:
                self.layout().removeWidget(self.pref_widget)
                self.pref_widget.deleteLater()
                self.pref_widget = None
            self.main_widget.setVisible(True)
            self.layout().addWidget(self.main_widget)
            self.main_widget.raise_()

        def apply_settings(self):
            """Apply the current settings"""
            try:
                default_shuffle = "shuffle2" if self.shuffle2_radio.isChecked() else "shuffle"
                
                prefs = {
                    "shuffle_enabled": self.shuffle_checkbox.isChecked(),
                    "shufflecopy_enabled": self.shufflecopy_checkbox.isChecked(),
                    "shuffle2_enabled": self.shuffle2_checkbox.isChecked(),
                    "default_shuffle": default_shuffle,
                    "shortcut": load_preferences().get("shortcut", DEFAULT_SHORTCUT)
                }
                
                save_preferences(prefs)
                register_enabled_shuffle_nodes()
                
                # Success message
                enabled_nodes = []
                if prefs["shuffle_enabled"]:
                    enabled_nodes.append("Shuffle (Legacy)")
                if prefs["shufflecopy_enabled"]:
                    enabled_nodes.append("ShuffleCopy")
                if prefs["shuffle2_enabled"]:
                    enabled_nodes.append("Shuffle2 (Modern)")
                
                if enabled_nodes:
                    default_name = "Shuffle2" if default_shuffle == "shuffle2" else "Shuffle (Legacy)"
                    message = f"Settings applied!\n\nEnabled nodes: {', '.join(enabled_nodes)}\nDefault: {default_name}"
                else:
                    message = "Settings applied!\n\nAll shuffle nodes disabled"
                    
                self.close()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")
                tprint(f"Error applying settings: {e}")

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

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

def refresh_shuffle_menus():
    """Manually refresh shuffle menus"""
    tprint("Manually refreshing shuffle menus...")
    register_enabled_shuffle_nodes()
    tprint("Manual refresh complete")

def initialize_shuffle_menus():
    """Initialize shuffle menus based on preferences"""
    try:
        register_enabled_shuffle_nodes()
    except Exception as e:
        tprint(f"Error initializing shuffle menus: {e}")

# =============================================================================
# INITIALIZATION
# =============================================================================

# Register menu
register_menu()

# Multiple initialization points
nuke.addOnScriptLoad(initialize_shuffle_menus)
nuke.addOnScriptSave(initialize_shuffle_menus)
nuke.addOnCreate(initialize_shuffle_menus)

# Immediate initialization
try:
    import threading
    timer = threading.Timer(0.5, initialize_shuffle_menus)
    timer.start()
except:
    pass

# Status output with panel ID and shortcut info
prefs = load_preferences()
shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)

if shortcut and shortcut.strip():
    print("Shuffle Node Manager panel registered successfully with shortcut: {} [{}]".format(shortcut, PANEL_ID))
else:
    print("Shuffle Node Manager panel registered successfully [{}]".format(PANEL_ID))
