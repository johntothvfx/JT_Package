"""
=======================================================================
DEVELOPER = 'John Toth'
VERSION   = '1.0.0'
UPDATED   = '7th June, 2025'

Marker Connect UI
=======================================================================
A unified interface for creating and managing Marker and Connect nodes in Nuke.
Provides quick creation of reference markers and connect nodes for organizing
complex node graphs. Features searchable marker selection, color presets,
tags, and keyboard shortcut integration.
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
PREFS_PATH = os.path.join(SCRIPT_DIR, "marker_connect_prefs.json")
DEFAULT_SHORTCUT = "Ctrl+Shift+M"

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

def register_marker_connect_shortcut():
    """
    Register the keyboard shortcut for the Marker/Connect UI
    Add this to your menu.py or init.py:
    
    import marker_connect_shortcut
    marker_connect_shortcut.register_marker_connect_shortcut()
    """
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    nuke.menu('Nuke').findItem('JT Package').addCommand('Marker Connect UI', show_marker_connect_ui, shortcut)

# ---- PySide2/6 imports ----
try:
    from PySide2.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QLineEdit, QPushButton, QMessageBox, QSpacerItem, QSizePolicy,
        QScrollArea, QFrame, QDialog, QDialogButtonBox, QListWidget,
        QListWidgetItem, QStackedWidget, QButtonGroup, QRadioButton,
        QGroupBox, QCheckBox
    )
    from PySide2.QtCore import Qt
    from PySide2.QtGui import QKeySequence
except ImportError:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
        QLineEdit, QPushButton, QMessageBox, QSpacerItem, QSizePolicy,
        QScrollArea, QFrame, QDialog, QDialogButtonBox, QListWidget,
        QListWidgetItem, QStackedWidget, QButtonGroup, QRadioButton,
        QGroupBox, QCheckBox
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence

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
class MarkerConnectPreferences(QWidget):
    def __init__(self, shortcut, on_save=None, on_cancel=None, parent=None):
        super(MarkerConnectPreferences, self).__init__(parent)
        self.setWindowTitle("Marker Connect Preferences")
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

        # Auto-create Connect preference (above shortcut)
        self.auto_connect_checkbox = QCheckBox("Enable 'Also create Connect node' by default")
        prefs = load_preferences()
        default_create_connect = prefs.get("default_create_connect", False)
        self.auto_connect_checkbox.setChecked(default_create_connect)
        self.auto_connect_checkbox.setToolTip("When enabled, the 'Also create Connect node' checkbox will be checked by default when creating new markers")
        vlayout.addWidget(self.auto_connect_checkbox)
        vlayout.addSpacing(4)

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
        auto_create_connect = self.auto_connect_checkbox.isChecked()
        
        prefs = load_preferences()
        prefs["shortcut"] = shortcut
        prefs["default_create_connect"] = auto_create_connect
        save_preferences(prefs)
        
        updated = update_existing_shortcut(shortcut)
        
        message = f"Preferences saved!\n\nAuto-enable Connect option: {'Enabled' if auto_create_connect else 'Disabled'}\nShortcut: {shortcut}"
        if not updated:
            message += "\n\nNote: You may need to restart Nuke to update the menu shortcut."
            
        QMessageBox.information(self, "Saved", message)
        
        if self.on_save:
            self.on_save()
        else:
            self.close()

    def cancel(self):
        if self.on_cancel:
            self.on_cancel()
        else:
            self.close()

# ----- Live shortcut updater -----
def update_existing_shortcut(shortcut):
    """Try to update the menu shortcut live. Returns True if live update works."""
    try:
        menubar = nuke.menu("Nuke")
        jt_menu = menubar.findItem("JT Package")
        if not jt_menu:
            return False
        item = jt_menu.findItem("Marker Connect UI")
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

def show_marker_connect_ui():
    """Main function to show the unified Marker/Connect UI"""
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        from PySide2.QtCore import Qt
    except ImportError:
        try:
            from PySide import QtGui as QtWidgets
            from PySide import QtCore
            from PySide.QtCore import Qt
        except ImportError:
            nuke.message('Qt not available - using fallback interface')
            show_fallback_ui()
            return

    class MarkerConnectUI(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(MarkerConnectUI, self).__init__(parent)
            self.setWindowTitle(f'Marker & Connect Manager v{VERSION}')
            self.setModal(True)
            self.setMinimumSize(500, 400)
            self.selected_marker = None
            self.all_markers = []
            self.mode = 'connect'  # 'connect' or 'marker'
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
            
            self.main_widget = QtWidgets.QWidget(self)
            self._build_main_ui()
            
            main_layout = QtWidgets.QVBoxLayout(self)
            main_layout.setContentsMargins(0,0,0,0)
            main_layout.addWidget(self.main_widget)
            self.setLayout(main_layout)
            
            self.populateMarkers()
            self.setFocus()
            
        def _build_main_ui(self):
            layout = QtWidgets.QVBoxLayout(self.main_widget)
            layout.setContentsMargins(10, 10, 10, 10)
            
            # Header with mode selection
            header_layout = QtWidgets.QHBoxLayout()
            
            # Mode selection buttons
            mode_group = QtWidgets.QButtonGroup()
            self.connect_mode_btn = QtWidgets.QRadioButton('Create Connect Node')
            self.marker_mode_btn = QtWidgets.QRadioButton('Create New Marker')
            
            self.connect_mode_btn.setChecked(True)  # Default to connect mode
            self.connect_mode_btn.toggled.connect(self.on_mode_changed)
            self.marker_mode_btn.toggled.connect(self.on_mode_changed)
            
            mode_group.addButton(self.connect_mode_btn)
            mode_group.addButton(self.marker_mode_btn)
            
            header_layout.addWidget(self.connect_mode_btn)
            header_layout.addWidget(self.marker_mode_btn)
            header_layout.addStretch()
            
            layout.addLayout(header_layout)
            
            # Separator
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Sunken)
            layout.addWidget(line)
            
            # Stacked widget for different modes
            self.stacked_widget = QtWidgets.QStackedWidget()
            
            # Connect mode widget
            self.connect_widget = self.create_connect_widget()
            self.stacked_widget.addWidget(self.connect_widget)
            
            # Marker mode widget  
            self.marker_widget = self.create_marker_widget()
            self.stacked_widget.addWidget(self.marker_widget)
            
            layout.addWidget(self.stacked_widget)
            
            # Buttons
            button_layout = QtWidgets.QHBoxLayout()
            
            self.action_btn = QtWidgets.QPushButton('Create Connect')
            self.action_btn.setDefault(True)
            cancel_btn = QtWidgets.QPushButton('Cancel')
            self.pref_btn = QtWidgets.QPushButton('Preferences...')
            
            self.action_btn.clicked.connect(self.execute_action)
            cancel_btn.clicked.connect(self.reject)
            self.pref_btn.clicked.connect(self.show_preferences)
            
            button_layout.addWidget(self.pref_btn)
            button_layout.addStretch()
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(self.action_btn)
            
            layout.addLayout(button_layout)
            
        def create_connect_widget(self):
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()
            
            # Instructions
            instructions = QtWidgets.QLabel('Select a marker to create a Connect node:')
            instructions.setStyleSheet('font-weight: bold; margin-bottom: 5px;')
            layout.addWidget(instructions)
            
            # Search box
            search_layout = QtWidgets.QHBoxLayout()
            search_label = QtWidgets.QLabel('Search:')
            self.search_box = QtWidgets.QLineEdit()
            self.search_box.setPlaceholderText('Type to filter markers...')
            self.search_box.textChanged.connect(self.filter_markers)
            search_layout.addWidget(search_label)
            search_layout.addWidget(self.search_box)
            layout.addLayout(search_layout)
            
            # Marker list
            self.marker_list = QtWidgets.QListWidget()
            self.marker_list.setMinimumHeight(250)
            self.marker_list.itemDoubleClicked.connect(self.execute_action)
            self.marker_list.itemSelectionChanged.connect(self.update_action_button)
            layout.addWidget(self.marker_list)
            
            # Status label
            self.status_label = QtWidgets.QLabel('')
            self.status_label.setStyleSheet('color: #666; font-size: 11px;')
            layout.addWidget(self.status_label)
            
            widget.setLayout(layout)
            return widget
            
        def create_marker_widget(self):
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()
            
            # Instructions
            instructions = QtWidgets.QLabel('Create a new marker:')
            instructions.setStyleSheet('font-weight: bold; margin-bottom: 5px;')
            layout.addWidget(instructions)
            
            # Marker name input
            name_layout = QtWidgets.QHBoxLayout()
            name_label = QtWidgets.QLabel('Marker Name:')
            self.marker_name_input = QtWidgets.QLineEdit()
            self.marker_name_input.setPlaceholderText('Enter marker name...')
            self.marker_name_input.textChanged.connect(self.update_action_button)
            name_layout.addWidget(name_label)
            name_layout.addWidget(self.marker_name_input)
            layout.addLayout(name_layout)
            
            # Tags input
            tags_layout = QtWidgets.QHBoxLayout()
            tags_label = QtWidgets.QLabel('Tags (optional):')
            self.tags_input = QtWidgets.QLineEdit()
            self.tags_input.setPlaceholderText('Comma-separated tags...')
            tags_layout.addWidget(tags_label)
            tags_layout.addWidget(self.tags_input)
            layout.addLayout(tags_layout)
            
            # Color preset selection
            color_layout = QtWidgets.QHBoxLayout()
            color_label = QtWidgets.QLabel('Color Preset:')
            self.color_combo = QtWidgets.QComboBox()
            
            # Add color presets matching your original exactly
            color_presets = [
                ('Marker', '2004318207'),
                ('Read', '0'),
                ('Deep', '24576'),
                ('Roto/Paint', '1908830719'),
                ('Channel', '2654757887'),
                ('3D / Scanline', '2617245696'),
                ('keyer', '16711935'),
                ('Time', '2963561983'),
                ('Write', '3165597183'),
                ('STMap', '1993542655'),
                ('Dev', '3241845759'),
                ('Custom 001', '3448063'),
                ('Custom 002', '782318079')
            ]
            
            for name, value in color_presets:
                self.color_combo.addItem(name, value)
            
            color_layout.addWidget(color_label)
            color_layout.addWidget(self.color_combo)
            color_layout.addStretch()
            layout.addLayout(color_layout)
            
            # Options
            options_group = QtWidgets.QGroupBox('Options')
            options_layout = QtWidgets.QVBoxLayout()
            
            self.create_connect_checkbox = QtWidgets.QCheckBox('Also create Connect node')
            # Load preference for default state
            prefs = load_preferences()
            default_create_connect = prefs.get("default_create_connect", False)  # False by default
            self.create_connect_checkbox.setChecked(default_create_connect)
            options_layout.addWidget(self.create_connect_checkbox)
            
            options_group.setLayout(options_layout)
            layout.addWidget(options_group)
            
            layout.addStretch()
            
            widget.setLayout(layout)
            return widget
            
        def on_mode_changed(self):
            if self.connect_mode_btn.isChecked():
                self.mode = 'connect'
                self.stacked_widget.setCurrentIndex(0)
                self.action_btn.setText('Create Connect')
                self.search_box.setFocus()
            else:
                self.mode = 'marker'
                self.stacked_widget.setCurrentIndex(1)
                self.action_btn.setText('Create Marker')
                self.marker_name_input.setFocus()
            
            self.update_action_button()
            
        def populateMarkers(self):
            self.all_markers = []
            
            # Get all marker nodes
            for n in nuke.allNodes():
                if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and 
                    n['CLASSIFICATION'].value() == 'Marker'):
                    
                    # Get tags if available
                    tags = ''
                    if n.knob('tags') and n['tags'].value():
                        tags = n['tags'].value()
                    
                    self.all_markers.append({
                        'node_name': n.name(),
                        'search_text': (n.name() + ' ' + tags).lower(),
                        'tags': tags
                    })
            
            self.all_markers.sort(key=lambda x: x['node_name'].lower())
            self.filter_markers('')
            
        def filter_markers(self, search_text=''):
            if not hasattr(self, 'search_box'):
                return
                
            search_text = self.search_box.text().lower().strip()
            self.marker_list.clear()
            
            if not self.all_markers:
                no_markers = QtWidgets.QListWidgetItem('No markers found')
                no_markers.setFlags(no_markers.flags() & ~Qt.ItemIsSelectable)
                self.marker_list.addItem(no_markers)
                self.status_label.setText('No markers available')
                return
            
            if search_text:
                filtered_markers = [
                    marker for marker in self.all_markers 
                    if search_text in marker['search_text']
                ]
            else:
                filtered_markers = self.all_markers
            
            for marker in filtered_markers:
                display_text = marker['node_name']
                if marker['tags']:
                    display_text += f" ({marker['tags']})"
                    
                item = QtWidgets.QListWidgetItem(display_text)
                item.setData(Qt.UserRole, marker['node_name'])
                self.marker_list.addItem(item)
            
            total_count = len(self.all_markers)
            filtered_count = len(filtered_markers)
            
            if search_text:
                if filtered_count == 0:
                    self.status_label.setText(f'No matches found (0 of {total_count} markers)')
                else:
                    self.status_label.setText(f'Showing {filtered_count} of {total_count} markers')
            else:
                self.status_label.setText(f'{total_count} markers available')
            
            if self.marker_list.count() > 0 and filtered_markers:
                self.marker_list.setCurrentRow(0)
                
        def update_action_button(self):
            if self.mode == 'connect':
                current_item = self.marker_list.currentItem()
                has_valid_selection = (current_item and 
                                     current_item.data(Qt.UserRole) is not None)
                self.action_btn.setEnabled(has_valid_selection)
            else:  # marker mode
                marker_name = self.marker_name_input.text().strip()
                self.action_btn.setEnabled(bool(marker_name))
                
        def execute_action(self):
            if self.mode == 'connect':
                self.create_connect_node()
            else:
                self.create_marker_node()
                
        def create_connect_node(self):
            current_item = self.marker_list.currentItem()
            if not current_item or not current_item.data(Qt.UserRole):
                return
                
            marker_name = current_item.data(Qt.UserRole)
            
            try:
                # Get the marker node
                marker_node = nuke.toNode(marker_name)
                if not marker_node:
                    nuke.message(f'Marker "{marker_name}" not found')
                    return
                
                # Create Connect node using exact copy of your original - let Nuke position it
                connect = self.create_connect_group_node(marker_name)
                
                # Select the new node
                for n in nuke.allNodes():
                    n.setSelected(False)
                connect.setSelected(True)
                
                print(f"Successfully created Connect node: {connect.name()}")
                print("About to accept dialog")
                self.accept()
                print("Dialog accepted")
                return  # Ensure we exit after success
                
            except Exception as e:
                nuke.message(f'Error creating Connect node: {str(e)}')
                return  # Exit on error, don't continue
                
        def create_marker_node(self):
            marker_name = self.marker_name_input.text().strip()
            if not marker_name:
                return
                
            try:
                # Clean the name
                clean_name = marker_name.replace(' ', '_').replace('-', '_')
                
                # Make unique
                if nuke.exists(clean_name):
                    i = 1
                    while nuke.exists(f'{clean_name}_{i}'):
                        i += 1
                    clean_name = f'{clean_name}_{i}'
                
                # Get the preset index from the UI combo box
                preset_index = self.color_combo.currentIndex()
                
                # Create marker node using exact copy - let Nuke position it
                marker = self.create_marker_node_exact(clean_name, preset_index)
                
                # Set tags if provided BEFORE copy/paste
                tags_text = self.tags_input.text().strip()
                if tags_text and marker.knob('tags'):
                    marker['tags'].setValue(tags_text)
                
                # Apply the copy/paste trick to trigger TCL expression evaluation (like CameraBag)
                # This forces Nuke to properly evaluate the output knob expression
                for n in nuke.allNodes():
                    n['selected'].setValue(False)

                marker['selected'].setValue(True)

                # PRESERVE THE ORIGINAL NAME AND POSITION
                original_name = marker.name()  # Store the original name
                xpos = marker.xpos()
                ypos = marker.ypos()

                nuke.duplicateSelectedNodes()
                new_marker = nuke.selectedNode()
                new_marker.setXYpos(xpos, ypos)

                # DELETE THE OLD MARKER FIRST, THEN RENAME THE NEW ONE
                nuke.delete(marker)

                # NOW RENAME THE NEW MARKER TO THE ORIGINAL NAME
                new_marker.setName(original_name)

                # Update reference to the new marker
                marker = new_marker
                
                # NOW apply the color AFTER the copy/paste trick
                # Adjust for the empty first entry in the preset list
                adjusted_preset_index = preset_index + 1
                
                if preset_index == 0:  # "Marker" preset from UI
                    # Force a refresh/update cycle for the problematic "Marker" preset
                    try:
                        # Set to the correct index (1 now because of empty first entry)
                        marker['presets'].setValue(adjusted_preset_index)
                        
                        # Force immediate color application
                        marker['tile_color'].setValue(2004318207)
                        
                        print(f"Applied Marker preset at adjusted index {adjusted_preset_index}")
                        
                    except Exception as e:
                        print(f"Error with Marker preset: {e}")
                        
                else:
                    # For all other presets
                    preset_items = [
                        '',  # Empty first entry
                        '2004318207\tMarker',
                        '0\tRead', 
                        '24576\tDeep',
                        '1908830719\tRoto/Paint',
                        '2654757887\tChannel',
                        '2617245696\t3D / Scanline',
                        '16711935\tkeyer',
                        '2963561983\tTime',
                        '3165597183\tWrite',
                        '1993542655\tSTMap',
                        '3241845759\tDev',
                        '3448063\tCustom 001',
                        '782318079\tCustom 002'
                    ]
                    
                    if adjusted_preset_index < len(preset_items):
                        preset_value = preset_items[adjusted_preset_index]
                        if '\t' in preset_value:
                            color_value = preset_value.split('\t')[0]
                            try:
                                marker['presets'].setValue(adjusted_preset_index)
                                marker['tile_color'].setValue(int(color_value))
                                print(f"Applied color {color_value} for preset {preset_index} at adjusted index {adjusted_preset_index}")
                            except Exception as e:
                                print(f"Error setting color: {e}")
                
                # Create Connect node if requested 
                if self.create_connect_checkbox.isChecked():
                    print(f"Creating Connect node for marker: {clean_name}")
                    try:
                        connect = self.create_connect_group_node(clean_name)
                        print(f"Successfully created Connect node: {connect.name()}")
                        
                        # Connect it to the marker
                        connect.setInput(0, marker)
                        connect['status'].setValue(f'Connected to: {clean_name}')
                        connect['tile_color'].setValue(0x4a90e2ff)
                        print(f"Connected Connect node to Marker: {clean_name}")
                        
                        # Select both nodes
                        for n in nuke.allNodes():
                            n.setSelected(False)
                        marker.setSelected(True)
                        connect.setSelected(True)
                        
                        print(f"Successfully created Marker and Connect: {clean_name}")
                    except Exception as e:
                        print(f"Error creating Connect node: {e}")
                        # Still select the marker even if Connect creation fails
                        for n in nuke.allNodes():
                            n.setSelected(False)
                        marker.setSelected(True)
                else:
                    # Select just the marker
                    for n in nuke.allNodes():
                        n.setSelected(False)
                    marker.setSelected(True)
                    
                    print(f"Successfully created Marker: {clean_name}")

                # Close the dialog
                print("About to accept dialog")
                self.accept()
                print("Dialog accepted")
                                
            except Exception as e:
                nuke.message(f'Error creating Marker: {str(e)}')
                import traceback
                print(f"Full error traceback: {traceback.format_exc()}")
                return  # Exit on error, don't continue
                
                # Create Connect node if requested
                if self.create_connect_checkbox.isChecked():
                    connect = self.create_connect_group_node(clean_name)
                    
                    # Select both nodes
                    for n in nuke.allNodes():
                        n.setSelected(False)
                    marker.setSelected(True)
                    connect.setSelected(True)
                    
                    print(f"Successfully created Marker and Connect: {clean_name}")
                else:
                    # Select just the marker
                    for n in nuke.allNodes():
                        n.setSelected(False)
                    marker.setSelected(True)
                    
                    print(f"Successfully created Marker: {clean_name}")
                
                print("About to accept dialog")
                self.accept()
                print("Dialog accepted")
                return  # Ensure we exit after success
                
            except Exception as e:
                nuke.message(f'Error creating Marker: {str(e)}')
                return  # Exit on error, don't continue

        def show_preferences(self):
            prefs = load_preferences()
            shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
            if self.pref_widget:
                self.layout().removeWidget(self.main_widget)
                self.main_widget.setVisible(False)
                self.layout().removeWidget(self.pref_widget)
                self.pref_widget.deleteLater()
            self.pref_widget = MarkerConnectPreferences(
                shortcut,
                on_save=self.show_main_ui,
                on_cancel=self.show_main_ui,
                parent=self
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

        def create_marker_node_exact(self, marker_name, preset_index):
            """Create an exact replica of your updated Marker node"""
            marker = nuke.createNode('NoOp', inpanel=False)
            marker.setName(marker_name)
            marker['tile_color'].setValue(0x777777ff)
            
            # Set the onCreate code for the marker
            onCreate_code = '''import nuke

n = nuke.thisNode()

class ConnectNodeCreator:
    def __init__(self):
        self.marker = nuke.thisNode()
        self.name = self.marker.name()
        
    def create_connect(self):
        import nuke
        
        selected = nuke.selectedNodes()
        
        # Calculate position for the new Connect node
        if selected:
            x = selected[-1]["xpos"].value() + 150
            y = selected[-1]["ypos"].value() + 50
        else:
            x = self.marker["xpos"].value() + 150
            y = self.marker["ypos"].value() + 50
        
        # Create the Group node
        connect = nuke.createNode("Group", inpanel=False)
        
        # Set basic properties
        connect["xpos"].setValue(x)
        connect["ypos"].setValue(y)
        connect["tile_color"].setValue(0x666666ff)
        connect["label"].setValue("[value status]")
        connect["hide_input"].setValue(True)
        
        # Generate unique name
        i = 1
        base_name = "Connect"
        if nuke.exists(base_name):
            while nuke.exists(base_name + str(i)):
                i += 1
            connect.setName(base_name + str(i))
        else:
            connect.setName(base_name)
        
        # Add the Connect tab
        connect.addKnob(nuke.Tab_Knob("Connect"))
        
        # Add CLASSIFICATION knob (invisible)
        classification_knob = nuke.String_Knob("CLASSIFICATION", "")
        classification_knob.setValue("Connect")
        classification_knob.setFlag(nuke.INVISIBLE)
        connect.addKnob(classification_knob)
        
        # Add parent knob
        parent_knob = nuke.String_Knob("parent", "parent", self.name)
        parent_knob.setTooltip("Node name of the Marker to connect to")
        connect.addKnob(parent_knob)
        
        # Add status knob
        status_knob = nuke.String_Knob("status", "Status", "Connected to: " + self.name)
        status_knob.setTooltip("Current connection status")
        status_knob.setFlag(nuke.DISABLED)
        connect.addKnob(status_knob)
        
        # Add connectFromIndex button
        connectFromIndex_code = """import nuke

def show_searchable_marker_selector():
    # Try to import Qt
    try:
        from PySide2 import QtWidgets, QtCore
        from PySide2.QtCore import Qt
    except ImportError:
        try:
            from PySide import QtGui as QtWidgets
            from PySide import QtCore
            from PySide.QtCore import Qt
        except ImportError:
            # Fallback to simple choice
            markers = []
            with nuke.thisParent():
                for n in nuke.allNodes():
                    if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and 
                        n['CLASSIFICATION'].value() == 'Marker'):
                        markers.append(n.name())
            
            if not markers:
                nuke.message('No markers found')
                return None
            else:
                choice = nuke.choice('Select Marker', 'Choose marker:', markers)
                return markers[choice] if choice is not None else None
    
    class SearchableMarkerSelector(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super(SearchableMarkerSelector, self).__init__(parent)
            self.setWindowTitle('Select Marker')
            self.setModal(True)
            self.selected_marker = None
            self.all_markers = []
            self.setupUI()
            self.populateMarkers()
            
        def setupUI(self):
            layout = QtWidgets.QVBoxLayout()
            
            header = QtWidgets.QLabel('Choose a Marker to connect to:')
            header.setStyleSheet('font-weight: bold; margin-bottom: 5px;')
            layout.addWidget(header)
            
            # Search box
            search_layout = QtWidgets.QHBoxLayout()
            search_label = QtWidgets.QLabel('Search:')
            self.search_box = QtWidgets.QLineEdit()
            self.search_box.setPlaceholderText('Type to filter markers...')
            self.search_box.textChanged.connect(self.filterMarkers)
            search_layout.addWidget(search_label)
            search_layout.addWidget(self.search_box)
            layout.addLayout(search_layout)
            
            # List widget
            self.listWidget = QtWidgets.QListWidget()
            self.listWidget.setMinimumSize(450, 300)
            layout.addWidget(self.listWidget)
            
            # Status label
            self.status_label = QtWidgets.QLabel('')
            self.status_label.setStyleSheet('color: #666; font-size: 11px;')
            layout.addWidget(self.status_label)
            
            # Buttons
            buttonBox = QtWidgets.QDialogButtonBox()
            self.connectBtn = buttonBox.addButton('Connect', QtWidgets.QDialogButtonBox.AcceptRole)
            cancelBtn = buttonBox.addButton('Cancel', QtWidgets.QDialogButtonBox.RejectRole)
            
            self.connectBtn.setEnabled(False)
            
            buttonBox.accepted.connect(self.accept)
            buttonBox.rejected.connect(self.reject)
            
            layout.addWidget(buttonBox)
            self.setLayout(layout)
            
            self.listWidget.itemDoubleClicked.connect(self.accept)
            self.listWidget.itemSelectionChanged.connect(self.updateConnectButton)
            
            self.search_box.setFocus()
            
        def populateMarkers(self):
            self.all_markers = []
            
            # Search in parent context, not inside the Group
            with nuke.thisParent():
                for n in nuke.allNodes():
                    if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and 
                        n['CLASSIFICATION'].value() == 'Marker'):
                        self.all_markers.append({
                            'node_name': n.name(),
                            'search_text': n.name().lower()
                        })
            
            self.all_markers.sort(key=lambda x: x['node_name'].lower())
            self.filterMarkers('')
            
        def filterMarkers(self, search_text=''):
            if not hasattr(self, 'search_box'):
                return
                
            search_text = self.search_box.text().lower().strip()
            self.listWidget.clear()
            
            if not self.all_markers:
                no_markers = QtWidgets.QListWidgetItem('No markers found')
                no_markers.setFlags(no_markers.flags() & ~Qt.ItemIsSelectable)
                self.listWidget.addItem(no_markers)
                self.status_label.setText('No markers available')
                return
            
            if search_text:
                filtered_markers = [
                    marker for marker in self.all_markers 
                    if search_text in marker['search_text']
                ]
            else:
                filtered_markers = self.all_markers
            
            for marker in filtered_markers:
                item = QtWidgets.QListWidgetItem(marker['node_name'])
                item.setData(Qt.UserRole, marker['node_name'])
                self.listWidget.addItem(item)
            
            total_count = len(self.all_markers)
            filtered_count = len(filtered_markers)
            
            if search_text:
                if filtered_count == 0:
                    self.status_label.setText('No matches found (0 of ' + str(total_count) + ' markers)')
                else:
                    self.status_label.setText('Showing ' + str(filtered_count) + ' of ' + str(total_count) + ' markers')
            else:
                self.status_label.setText(str(total_count) + ' markers available')
            
            if self.listWidget.count() > 0 and filtered_markers:
                self.listWidget.setCurrentRow(0)
                
        def updateConnectButton(self):
            current_item = self.listWidget.currentItem()
            has_valid_selection = (current_item and 
                                 current_item.data(Qt.UserRole) is not None)
            self.connectBtn.setEnabled(has_valid_selection)
            
        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if self.connectBtn.isEnabled():
                    self.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self.reject()
                return
            elif event.key() == Qt.Key_Down:
                if self.search_box.hasFocus() and self.listWidget.count() > 0:
                    self.listWidget.setFocus()
                    self.listWidget.setCurrentRow(0)
                    return
            elif event.key() == Qt.Key_Up:
                if self.listWidget.hasFocus() and self.listWidget.currentRow() == 0:
                    self.search_box.setFocus()
                    return
                    
            super(SearchableMarkerSelector, self).keyPressEvent(event)
            
        def accept(self):
            current_item = self.listWidget.currentItem()
            if current_item and current_item.data(Qt.UserRole):
                self.selected_marker = current_item.data(Qt.UserRole)
            super(SearchableMarkerSelector, self).accept()
    
    try:
        app = QtWidgets.QApplication.instance()
        parent = None
        if app:
            for widget in app.topLevelWidgets():
                if widget.metaObject().className() == 'Foundry::UI':
                    parent = widget
                    break
        
        dialog = SearchableMarkerSelector(parent)
        if dialog.exec_():
            return dialog.selected_marker
        return None
        
    except Exception as e:
        nuke.message('Error creating dialog: ' + str(e))
        return None

# Execute
connect_node = nuke.thisNode()
selected_marker = show_searchable_marker_selector()
if selected_marker:
    connect_node['parent'].setValue(selected_marker)"""
        
        connectFromIndex_knob = nuke.PyScript_Knob("connectFromIndex", "connect from index", connectFromIndex_code)
        connectFromIndex_knob.setTooltip("Show popup to select from available markers")
        connectFromIndex_knob.setFlag(nuke.STARTLINE)
        connect.addKnob(connectFromIndex_knob)
        
        # Add reconnect button
        reconnect_code = """import nuke
n = nuke.thisNode()
target = n['parent'].value()

if not target:
    nuke.message('No target marker set')
else:
    with nuke.thisParent():
        node = nuke.toNode(target)
        if node:
            n.setInput(0, node)
            nuke.message('Reconnected to: ' + target)
        else:
            nuke.message('Target not found: ' + target)"""
        
        reconnect_knob = nuke.PyScript_Knob("reconnect", "reconnect", reconnect_code)
        reconnect_knob.setTooltip("Force reconnection to target marker")
        reconnect_knob.clearFlag(nuke.STARTLINE)
        connect.addKnob(reconnect_knob)
        
        # Add findParent button
        findParent_code = """import nuke
n = nuke.thisNode()
target = n['parent'].value()

if not target:
    nuke.message('No target marker set')
else:
    with nuke.thisParent():
        node = nuke.toNode(target)
        if node:
            nuke.zoom(2, [node.xpos() + node.screenWidth()//2, 
                         node.ypos() + node.screenHeight()//2])
        else:
            nuke.message('Target not found: ' + target)"""
        
        findParent_knob = nuke.PyScript_Knob("findParent", "find parent", findParent_code)
        findParent_knob.setTooltip("Locate and zoom to the target marker")
        findParent_knob.clearFlag(nuke.STARTLINE)
        connect.addKnob(findParent_knob)
        
        # Add Utilities tab
        connect.addKnob(nuke.Tab_Knob("utilities", "Utilities"))
        
        # Add findConnected button
        findConnected_code = """import nuke
connect_node = nuke.thisNode()
parent_name = connect_node['parent'].value()

print('==== Find Connected ====')
print('Current Connect node: ' + connect_node.name())
print('Parent name: "' + str(parent_name) + '"')

if not parent_name:
    nuke.message('No parent marker set')
else:
    # Search in parent context, not inside the Group!
    with nuke.thisParent():
        # Deselect all
        for n in nuke.allNodes():
            n.setSelected(False)
        
        found = 0
        print('Checking all nodes in parent context...')
        
        for n in nuke.allNodes():
            node_name = n.name()
            
            # Check if it has parent knob
            if hasattr(n, 'knob') and n.knob('parent'):
                try:
                    node_parent = n['parent'].value()
                    print('Node: ' + node_name + ' -> parent: "' + str(node_parent) + '"')
                    
                    if node_parent == parent_name and n.name() != connect_node.name():
                        print('  -> MATCH! Selecting ' + node_name)
                        n.setSelected(True)
                        found += 1
                    elif node_parent == parent_name:
                        print('  -> Match but skipping self: ' + node_name)
                    else:
                        print('  -> No match')
                except Exception as e:
                    print('  -> Error reading parent: ' + str(e))
            else:
                print('Node: ' + node_name + ' -> No parent knob')
        
        print('====== SUMMARY ======')
        print('Total found: ' + str(found))
        print('=====================')
        
        if found:
            nuke.message('Selected ' + str(found) + ' Connect nodes targeting: ' + parent_name)
        else:
            nuke.message('No other Connect nodes found targeting: ' + parent_name)"""
        
        findConnected_knob = nuke.PyScript_Knob("findConnected", "find connected", findConnected_code)
        findConnected_knob.setTooltip("Select all Connect nodes that reference the same parent Marker")
        findConnected_knob.setFlag(nuke.STARTLINE)
        connect.addKnob(findConnected_knob)
        
        # Add hideInputToggle button
        hideInputToggle_code = """import nuke

def hideInputToggle():
    node = nuke.thisNode()
    knob = node.knob('hideInputToggle')
    hide_input_knob = node.knob('hide_input')
    
    if hide_input_knob is not None:
        # Toggle the actual hide_input value
        current_value = hide_input_knob.value()
        hide_input_knob.setValue(not current_value)
        
        # Update button label based on new state
        if hide_input_knob.value():
            knob.setLabel('show input')
        else:
            knob.setLabel('hide input')

# Run the function
hideInputToggle()"""
        
        hideInputToggle_knob = nuke.PyScript_Knob("hideInputToggle", "show input", hideInputToggle_code)
        hideInputToggle_knob.setTooltip("Toggle input visibility")
        hideInputToggle_knob.clearFlag(nuke.STARTLINE)
        connect.addKnob(hideInputToggle_knob)
        
        # Add togglePostageStamp button
        togglePostageStamp_code = """import nuke

def togglePostageStamp():
    node = nuke.thisNode()
    knob = node.knob('togglePostageStamp')
    postage_knob = node.knob('postage_stamp')
    
    if postage_knob is not None:
        # Toggle the actual postage_stamp value
        current_value = postage_knob.value()
        postage_knob.setValue(not current_value)
        
        # Update button label based on new state
        if postage_knob.value():
            knob.setLabel('hide stamp')
        else:
            knob.setLabel('show stamp')

# Run the function
togglePostageStamp()"""
        
        togglePostageStamp_knob = nuke.PyScript_Knob("togglePostageStamp", "show stamp", togglePostageStamp_code)
        togglePostageStamp_knob.setTooltip("Toggle postage stamp visibility")
        togglePostageStamp_knob.clearFlag(nuke.STARTLINE)
        connect.addKnob(togglePostageStamp_knob)
        
        # Add Info tab
        connect.addKnob(nuke.Tab_Knob("info", "Info"))
        
        # Add version text
        version_knob = nuke.Text_Knob("version", "", '<font size="5">Connect</font><font color=#777777> v1.2</font>')
        version_knob.setFlag(nuke.STARTLINE)
        connect.addKnob(version_knob)
        
        # Add empty line
        connect.addKnob(nuke.Text_Knob("", ""))
        
        # Add description
        description_text = """<strong>•</strong> <b>Connect nodes</b> act as reference points<br>that link back to this marker
<br><i><br>
<strong>•</strong> Set the "parent" field to the target marker<br>name, then use "Connect"
<br>
<strong>•</strong> Provides quick navigation and organization<br>in complex node graphs<br> 
<strong>•</strong> Maintains visual connection without affecting<br>the actual node flow<br><br>
<b><a href="https://johntothvfx.com" style="color:#777777;">John Toth © 2022</a></b><br>"""
        
        description_knob = nuke.Text_Knob("description", "", description_text)
        description_knob.setFlag(nuke.STARTLINE)
        connect.addKnob(description_knob)
        
        # Add empty line
        connect.addKnob(nuke.Text_Knob("", ""))
        
        # Add demo button (invisible)
        demo_knob = nuke.PyScript_Knob("demo", '<a href="https://johntothvfx.com"><span style="color:#777777">Tool Demo</span></a>', 'nuke.message("coming soon")')
        demo_knob.setTooltip("Launches the web page where it will have more documentation or a video about the node.")
        demo_knob.setFlag(nuke.INVISIBLE)
        demo_knob.setFlag(nuke.STARTLINE)
        connect.addKnob(demo_knob)
        
        # Add version log button
        log_code = """
version_number = "1.2.1"
context = "Other/Connect"
modified_date = "5th June 2025"
developer = "John Toth © 2022"
site = "<a href='website linke here'><span style='color:#BBBBBB'>"
log = \\\"\\\"\\\"
<br></i><b> v 1.0 </b><i>
- connects the input of the node based on the parent
<br></i><b> v 1.1 </b><i>
- index list was added to keep an list of all connect nodes to speed up workflow.
<br></i><b> v 1.2 </b><i>
- index now works through a difference system that works more dynamically
- marker system implementation has been added
- cleaner interface
\\\"\\\"\\\"
thank_you = " Special thanks to Samantha Maiolo for earlier development for this tool"

# Retrieve node name
name = nuke.thisNode()['CLASSIFICATION'].getValue()

# Message components
header = "Version Log:"
dlm = "<b>Date Last Modified: </b>" + modified_date
space = " "
enter = "<br><br>"
upper = "<b>"
lower = "</b>"

# Formatted message using string concatenation to avoid f-string conflicts
message = (
    upper + header + enter +
    "Name: " + lower + name + "<br>" +
    upper + "Version Number: " + lower + version_number + "<br>" +
    upper + "Context: " + lower + context + enter +
    dlm + log + "<br>" +
    "<b>Thank You:</b><br>" + thank_you + "<br>" + enter +
    "</i>" + upper + site + developer + lower + "</span></a>"
)

# Display the message
nuke.message(message)"""
        
        log_knob = nuke.PyScript_Knob("log", '<a href="https://johntothvfx.com"><span style="color:#777777">Version Log</span></a>', log_code)
        log_knob.setTooltip('Contains information about this node.\\n\\n- classification\\n- context\\n- date last modified\\n- developer notes\\n- version number\\n- version log\\n- year made')
        log_knob.clearFlag(nuke.STARTLINE)
        connect.addKnob(log_knob)
        
        # Set the onCreate code
        onCreate_code = """import nuke
# Set unique name
i = 1
while nuke.exists('Connect_' + str(i)):
    i += 1
nuke.thisNode().setName('Connect_' + str(i))
# Try auto-reconnect if targetMarker is set
n = nuke.thisNode()
if n.knob('parent') and n['parent'].value():
    target = n['parent'].value()
    with nuke.thisParent():
        node = nuke.toNode(target)
        if node:
            n.setInput(0, node)"""
        
        connect["onCreate"].setValue(onCreate_code)
        
        # Set the knobChanged code
        knobChanged_code = """import nuke
n = nuke.thisNode()
k = nuke.thisKnob()

if k.name() == 'parent':
    target = n['parent'].value()
    if target:
        with nuke.thisParent():
            node = nuke.toNode(target)
            if node:
                n.setInput(0, node)
                n['status'].setValue('Connected to: ' + target)
                n['tile_color'].setValue(0x4a90e2ff)
            else:
                n['status'].setValue('ERROR: ' + target + ' not found')
                n['tile_color'].setValue(0xff4444ff)
    else:
        n.setInput(0, None)
        n['status'].setValue('No Parent Set')
        n['tile_color'].setValue(0x666666ff)

elif k.name() == 'inputChange':
    target = n['parent'].value()
    input_node = n.input(0)
    
    if not input_node:
        n['tile_color'].setValue(0xff4444ff)
        if target:
            n['status'].setValue('Disconnected from: ' + target)
        else:
            n['status'].setValue('No connection')
    elif target and input_node.name() == target:
        n['tile_color'].setValue(0x4a90e2ff)
        n['status'].setValue('(' + target + ')')
    else:
        n['tile_color'].setValue(0xffa500ff)
        if input_node:
            n['status'].setValue('Wrong connection: ' + input_node.name())
        else:
            n['status'].setValue('Connection mismatch')"""
        
        connect["knobChanged"].setValue(knobChanged_code)
        
        # Create internal Input and Output nodes
        connect.begin()
        input_node = nuke.createNode("Input", inpanel=False)
        input_node["xpos"].setValue(0)
        input_node["ypos"].setValue(-200)
        input_node["label"].setValue("[value number]")
        input_node.setName('Input')
        output_node = nuke.createNode("Output", inpanel=False)
        output_node["xpos"].setValue(0)
        output_node["ypos"].setValue(-100)
        connect.end()
        
        # Connect the group to the marker
        connect.setInput(0, self.marker)
        
        # Select the new Connect node
        for n in nuke.allNodes():
            n.setSelected(False)
        connect.setSelected(True)
        
        nuke.message("Created Connect node: " + connect.name())

def create_connect():
    creator = ConnectNodeCreator()
    creator.create_connect()'''
            
            marker['onCreate'].setValue(onCreate_code)
            
            # Add Marker tab
            marker.addKnob(nuke.Tab_Knob('Marker'))
            
            # Add CLASSIFICATION knob
            classification_knob = nuke.String_Knob('CLASSIFICATION', '', 'Marker')
            classification_knob.setFlag(nuke.INVISIBLE)
            marker.addKnob(classification_knob)
            
            # Add output knob (invisible) - this will trigger the TCL expression
            output_knob = nuke.String_Knob('output', '', '[knob tile_color [value presets]][value knob.tags]')
            output_knob.setFlag(nuke.INVISIBLE)
            marker.addKnob(output_knob)
            
            # Add presets knob - Add empty first entry to fix index 0 issue
            presets_knob = nuke.Enumeration_Knob('presets', 'presets', [
                '',  # Empty first entry to fix index 0 issue
                '2004318207\tMarker',
                '0\tRead',
                '24576\tDeep',
                '1908830719\tRoto/Paint',
                '2654757887\tChannel',
                '2617245696\t3D / Scanline',
                '16711935\tkeyer',
                '2963561983\tTime',
                '3165597183\tWrite',
                '1993542655\tSTMap',
                '3241845759\tDev',
                '3448063\tCustom 001',
                '782318079\tCustom 002',
                '', '', '', ''
            ])
            presets_knob.setTooltip("Choose a preset label and associated tile color")
            presets_knob.setValue(int(preset_index) + 1)  # Add 1 to account for empty first entry
            marker.addKnob(presets_knob)

            # Add tags knob
            tags_knob = nuke.String_Knob('tags', 'Tags', '')
            tags_knob.setTooltip('Comma-separated tags for organization')
            marker.addKnob(tags_knob)
            
            # Add rename button
            rename_code = '''import nuke
n = nuke.thisNode()
old = n.name()
result = nuke.getInput('Rename', 'New name (' + old + '):')
if result and result != old:
    clean = result.replace(' ', '_')
    if not nuke.exists(clean):
        n.setName(clean)
        for node in nuke.allNodes():
            if (hasattr(node, 'knob') and node.knob('targetMarker') and 
                node['targetMarker'].value() == old):
                node['targetMarker'].setValue(clean)
        nuke.message('Renamed to: ' + clean)
    else:
        nuke.message('Name already exists')'''
            
            rename_knob = nuke.PyScript_Knob('rename', '   rename   ', rename_code)
            rename_knob.setTooltip('Rename this marker')
            rename_knob.setFlag(nuke.STARTLINE)
            marker.addKnob(rename_knob)
            
            # Add Connect tab
            marker.addKnob(nuke.Tab_Knob('connect', 'Connect'))
            
            # Add createConnect button
            createConnect_code = '''exec(nuke.thisNode()['onCreate'].value())
creator = ConnectNodeCreator()
creator.create_connect()'''
            
            createConnect_knob = nuke.PyScript_Knob('createConnect', 'create connect', createConnect_code)
            createConnect_knob.setFlag(nuke.STARTLINE)
            createConnect_knob.setTooltip("Create and link a Connect node to this marker")
            marker.addKnob(createConnect_knob)
            
            # Add selectConnects button
            selectConnects_code = '''marker = nuke.thisNode()
name = marker.name()
for n in nuke.allNodes():
    n.setSelected(False)
found = 0
for n in nuke.allNodes():
    if (hasattr(n, 'knob') and n.knob('parent') and
        n['parent'].value() == name):
        n.setSelected(True)
        found += 1
if found:
    nuke.message('Selected ' + str(found) + ' Connect nodes')
else:
    nuke.message('No Connect nodes found')'''
            
            selectConnects_knob = nuke.PyScript_Knob('selectConnects', 'select connected', selectConnects_code)
            selectConnects_knob.setTooltip('Select all Connect nodes referencing this marker')
            selectConnects_knob.clearFlag(nuke.STARTLINE)
            marker.addKnob(selectConnects_knob)
            
            # Add reconnectAll button
            reconnectAll_code = '''markers = []
for n in nuke.allNodes():
    if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and
        n['CLASSIFICATION'].value() == 'Marker'):
        markers.append(n.name())

markers.sort()
updated_count = 0

for n in nuke.allNodes():
    if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and
        n['CLASSIFICATION'].value() == 'Connect'):
        parent_knob = n.knob('parent')
        input_node = n.input(0)
        
        if parent_knob:
            parent_value = parent_knob.value()
            if input_node and parent_value == input_node.name():
                continue
            if parent_value:
                target_node = nuke.toNode(parent_value)
                if target_node:
                    n.setInput(0, target_node)
                    updated_count += 1

nuke.message('Connected ' + str(updated_count) + ' Connect nodes')'''
            
            reconnectAll_knob = nuke.PyScript_Knob('reconnectAll', 'reconnect all', reconnectAll_code)
            reconnectAll_knob.setTooltip('Update all Connect node indexes')
            reconnectAll_knob.clearFlag(nuke.STARTLINE)
            marker.addKnob(reconnectAll_knob)
            
            # Add Info tab
            marker.addKnob(nuke.Tab_Knob('info', 'Info'))
            
            # Add version text
            version_knob = nuke.Text_Knob('version', '', '<font size="5">Marker</font><font color=#777777> v1.0</font>')
            version_knob.setFlag(nuke.STARTLINE)
            marker.addKnob(version_knob)
            
            # Add empty line
            marker.addKnob(nuke.Text_Knob('', ''))
            
            # Add description
            description_text = '<strong>•</strong> <b>Marker</b> act as reference anchors/bookmark<br>for organizing complex node graphs<br><i><br><strong>•</strong> Create Connect nodes to link back to<br>this marker from anywhere in your comp<br><strong>•</strong> Essential for navigation in large<br>node networks and complex workflows<br><strong>•</strong> Use "Create Connect" to generate reference<br>nodes that maintain visual organization<br><br><b><a href="https://johntothvfx.com" style="color:#777777;">John Toth © 2024</a></b><br>'
            
            description_knob = nuke.Text_Knob('description', '', description_text)
            description_knob.setFlag(nuke.STARTLINE)
            marker.addKnob(description_knob)
            
            return marker

        def create_connect_group_node(self, marker_name):
            """Create an exact replica of the Connect Group node from Connect.nk"""
            
            # Create the Group node - let Nuke position it naturally
            connect = nuke.createNode('Group', inpanel=False)
            connect.setName('Connect')
            connect['tile_color'].setValue(0x666666ff)
            connect['label'].setValue('[value status]')
            connect['hide_input'].setValue(True)
            
            # Set onCreate code (exact match from your .nk file)
            onCreate_code = '''import nuke
        # Set unique name
        i = 1
        while nuke.exists('Connect_' + str(i)):
            i += 1
        nuke.thisNode().setName('Connect_' + str(i))
        # Try auto-reconnect if targetMarker is set
        n = nuke.thisNode()
        if n.knob('parent') and n['parent'].value():
            target = n['parent'].value()
            with nuke.thisParent():
                node = nuke.toNode(target)
                if node:
                    n.setInput(0, node)'''
            
            connect['onCreate'].setValue(onCreate_code)
            
            # Set knobChanged code (exact match from your .nk file)
            knobChanged_code = '''import nuke
n = nuke.thisNode()
k = nuke.thisKnob()

if k.name() == 'parent':
    target = n['parent'].value()
    if target:
        with nuke.thisParent():
            node = nuke.toNode(target)
            if node:
                n.setInput(0, node)
                n['status'].setValue('Connected to: ' + target)
                n['tile_color'].setValue(0x4a90e2ff)
            else:
                n['status'].setValue('ERROR: ' + target + ' not found')
                n['tile_color'].setValue(0xff4444ff)
    else:
        n.setInput(0, None)
        n['status'].setValue('No Parent Set')
        n['tile_color'].setValue(0x666666ff)

elif k.name() == 'inputChange':
    target = n['parent'].value()
    input_node = n.input(0)
            
    if not input_node:
        n['tile_color'].setValue(0xff4444ff)
        if target:
            n['status'].setValue('Disconnected from: ' + target)
        else:
            n['status'].setValue('No connection')
    elif target and input_node.name() == target:
        n['tile_color'].setValue(0x4a90e2ff)
        n['status'].setValue('(' + target + ')')
    else:
        n['tile_color'].setValue(0xffa500ff)
        if input_node:
            n['status'].setValue('Wrong connection: ' + input_node.name())
        else:
            n['status'].setValue('Connection mismatch')'''
            
            connect['knobChanged'].setValue(knobChanged_code)
            
            # Add Connect tab
            connect.addKnob(nuke.Tab_Knob('Connect'))
            
            # CLASSIFICATION knob
            classification_knob = nuke.String_Knob('CLASSIFICATION', '', 'Connect')
            classification_knob.setFlag(nuke.STARTLINE)
            classification_knob.setFlag(nuke.INVISIBLE)
            connect.addKnob(classification_knob)
            
            # Parent knob
            parent_knob = nuke.String_Knob('parent', 'parent', marker_name)
            parent_knob.setTooltip('Node name of the Marker to connect to')
            connect.addKnob(parent_knob)
            
            # Status knob
            status_knob = nuke.String_Knob('status', 'Status', 'No Parent Set')
            status_knob.setTooltip('Current connection status')
            status_knob.setFlag(nuke.DISABLED)
            connect.addKnob(status_knob)
            
            # connectFromIndex button (the big searchable selector)
            connectFromIndex_code = '''import nuke

        def show_searchable_marker_selector():
            # Try to import Qt
            try:
                from PySide2 import QtWidgets, QtCore
                from PySide2.QtCore import Qt
            except ImportError:
                try:
                    from PySide import QtGui as QtWidgets
                    from PySide import QtCore
                    from PySide.QtCore import Qt
                except ImportError:
                    # Fallback to simple choice
                    markers = []
                    with nuke.thisParent():
                        for n in nuke.allNodes():
                            if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and 
                                n['CLASSIFICATION'].value() == 'Marker'):
                                markers.append(n.name())
                    
                    if not markers:
                        nuke.message('No markers found')
                        return None
                    else:
                        choice = nuke.choice('Select Marker', 'Choose marker:', markers)
                        return markers[choice] if choice is not None else None
            
            class SearchableMarkerSelector(QtWidgets.QDialog):
                def __init__(self, parent=None):
                    super(SearchableMarkerSelector, self).__init__(parent)
                    self.setWindowTitle('Select Marker')
                    self.setModal(True)
                    self.selected_marker = None
                    self.all_markers = []
                    self.setupUI()
                    self.populateMarkers()
                    
                def setupUI(self):
                    layout = QtWidgets.QVBoxLayout()
                    
                    header = QtWidgets.QLabel('Choose a Marker to connect to:')
                    header.setStyleSheet('font-weight: bold; margin-bottom: 5px;')
                    layout.addWidget(header)
                    
                    # Search box
                    search_layout = QtWidgets.QHBoxLayout()
                    search_label = QtWidgets.QLabel('Search:')
                    self.search_box = QtWidgets.QLineEdit()
                    self.search_box.setPlaceholderText('Type to filter markers...')
                    self.search_box.textChanged.connect(self.filterMarkers)
                    search_layout.addWidget(search_label)
                    search_layout.addWidget(self.search_box)
                    layout.addLayout(search_layout)
                    
                    # List widget
                    self.listWidget = QtWidgets.QListWidget()
                    self.listWidget.setMinimumSize(450, 300)
                    layout.addWidget(self.listWidget)
                    
                    # Status label
                    self.status_label = QtWidgets.QLabel('')
                    self.status_label.setStyleSheet('color: #666; font-size: 11px;')
                    layout.addWidget(self.status_label)
                    
                    # Buttons
                    buttonBox = QtWidgets.QDialogButtonBox()
                    self.connectBtn = buttonBox.addButton('Connect', QtWidgets.QDialogButtonBox.AcceptRole)
                    cancelBtn = buttonBox.addButton('Cancel', QtWidgets.QDialogButtonBox.RejectRole)
                    
                    self.connectBtn.setEnabled(False)
                    
                    buttonBox.accepted.connect(self.accept)
                    buttonBox.rejected.connect(self.reject)
                    
                    layout.addWidget(buttonBox)
                    self.setLayout(layout)
                    
                    self.listWidget.itemDoubleClicked.connect(self.accept)
                    self.listWidget.itemSelectionChanged.connect(self.updateConnectButton)
                    
                    self.search_box.setFocus()
                    
                def populateMarkers(self):
                    self.all_markers = []
                    
                    # Search in parent context, not inside the Group
                    with nuke.thisParent():
                        for n in nuke.allNodes():
                            if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and 
                                n['CLASSIFICATION'].value() == 'Marker'):
                                self.all_markers.append({
                                    'node_name': n.name(),
                                    'search_text': n.name().lower()
                                })
                    
                    self.all_markers.sort(key=lambda x: x['node_name'].lower())
                    self.filterMarkers('')
                    
                def filterMarkers(self, search_text=''):
                    if not hasattr(self, 'search_box'):
                        return
                        
                    search_text = self.search_box.text().lower().strip()
                    self.listWidget.clear()
                    
                    if not self.all_markers:
                        no_markers = QtWidgets.QListWidgetItem('No markers found')
                        no_markers.setFlags(no_markers.flags() & ~Qt.ItemIsSelectable)
                        self.listWidget.addItem(no_markers)
                        self.status_label.setText('No markers available')
                        return
                    
                    if search_text:
                        filtered_markers = [
                            marker for marker in self.all_markers 
                            if search_text in marker['search_text']
                        ]
                    else:
                        filtered_markers = self.all_markers
                    
                    for marker in filtered_markers:
                        item = QtWidgets.QListWidgetItem(marker['node_name'])
                        item.setData(Qt.UserRole, marker['node_name'])
                        self.listWidget.addItem(item)
                    
                    total_count = len(self.all_markers)
                    filtered_count = len(filtered_markers)
                    
                    if search_text:
                        if filtered_count == 0:
                            self.status_label.setText('No matches found (0 of ' + str(total_count) + ' markers)')
                        else:
                            self.status_label.setText('Showing ' + str(filtered_count) + ' of ' + str(total_count) + ' markers')
                    else:
                        self.status_label.setText(str(total_count) + ' markers available')
                    
                    if self.listWidget.count() > 0 and filtered_markers:
                        self.listWidget.setCurrentRow(0)
                        
                def updateConnectButton(self):
                    current_item = self.listWidget.currentItem()
                    has_valid_selection = (current_item and 
                                        current_item.data(Qt.UserRole) is not None)
                    self.connectBtn.setEnabled(has_valid_selection)
                    
                def keyPressEvent(self, event):
                    if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                        if self.connectBtn.isEnabled():
                            self.accept()
                        return
                    elif event.key() == Qt.Key_Escape:
                        self.reject()
                        return
                    elif event.key() == Qt.Key_Down:
                        if self.search_box.hasFocus() and self.listWidget.count() > 0:
                            self.listWidget.setFocus()
                            self.listWidget.setCurrentRow(0)
                            return
                    elif event.key() == Qt.Key_Up:
                        if self.listWidget.hasFocus() and self.listWidget.currentRow() == 0:
                            self.search_box.setFocus()
                            return
                            
                    super(SearchableMarkerSelector, self).keyPressEvent(event)
                    
                def accept(self):
                    current_item = self.listWidget.currentItem()
                    if current_item and current_item.data(Qt.UserRole):
                        self.selected_marker = current_item.data(Qt.UserRole)
                    super(SearchableMarkerSelector, self).accept()
            
            try:
                app = QtWidgets.QApplication.instance()
                parent = None
                if app:
                    for widget in app.topLevelWidgets():
                        if widget.metaObject().className() == 'Foundry::UI':
                            parent = widget
                            break
                
                dialog = SearchableMarkerSelector(parent)
                if dialog.exec_():
                    return dialog.selected_marker
                return None
                
            except Exception as e:
                nuke.message('Error creating dialog: ' + str(e))
                return None

        # Execute
        # Store the node reference BEFORE calling the dialog
        connect_node = nuke.thisNode()

        selected_marker = show_searchable_marker_selector()
        if selected_marker:
            # Use the stored node reference instead of nuke.thisNode()
            connect_node['parent'].setValue(selected_marker)'''
            
            connectFromIndex_knob = nuke.PyScript_Knob('connectFromIndex', 'connect from index', connectFromIndex_code)
            connectFromIndex_knob.setTooltip('Show popup to select from available markers')
            connectFromIndex_knob.setFlag(nuke.STARTLINE)
            connect.addKnob(connectFromIndex_knob)
            
            # Reconnect button
            reconnect_code = '''import nuke
n = nuke.thisNode()
target = n['parent'].value()

if not target:
    nuke.message('No target marker set')
else:
    with nuke.thisParent():
        node = nuke.toNode(target)
        if node:
            n.setInput(0, node)
            nuke.message('Reconnected to: ' + target)
        else:
            nuke.message('Target not found: ' + target)'''
            
            reconnect_knob = nuke.PyScript_Knob('reconnect', 'reconnect', reconnect_code)
            reconnect_knob.setTooltip('Force reconnection to target marker')
            reconnect_knob.clearFlag(nuke.STARTLINE)
            connect.addKnob(reconnect_knob)
            
            # Find parent button
            findParent_code = '''import nuke
n = nuke.thisNode()
target = n['parent'].value()

if not target:
    nuke.message('No target marker set')
else:
    with nuke.thisParent():
        node = nuke.toNode(target)
        if node:
            nuke.zoom(2, [node.xpos() + node.screenWidth()//2, 
                        node.ypos() + node.screenHeight()//2])
        else:
            nuke.message('Target not found: ' + target)'''
            
            findParent_knob = nuke.PyScript_Knob('findParent', 'find parent', findParent_code)
            findParent_knob.setTooltip('Locate and zoom to the target marker')
            findParent_knob.clearFlag(nuke.STARTLINE)
            connect.addKnob(findParent_knob)
            
            # Add Utilities tab
            connect.addKnob(nuke.Tab_Knob('utilities', 'Utilities'))
            
            # Find connected button
            findConnected_code = '''import nuke
connect_node = nuke.thisNode()
parent_name = connect_node['parent'].value()

print('=== Find Connected ===')
print('Current Connect node: ' + connect_node.name())
print('Parent name: "' + str(parent_name) + '"')

if not parent_name:
    nuke.message('No parent marker set')
else:
    # Search in parent context, not inside the Group!
    with nuke.thisParent():
        # Deselect all
        for n in nuke.allNodes():
            n.setSelected(False)
                
        found = 0
        print('Checking all nodes in parent context...')
                
        for n in nuke.allNodes():
            node_name = n.name()
                    
            # Check if it has parent knob
            if hasattr(n, 'knob') and n.knob('parent'):
                try:
                    node_parent = n['parent'].value()
                    print('Node: ' + node_name + ' -> parent: "' + str(node_parent) + '"')
                            
                    if node_parent == parent_name and n.name() != connect_node.name():
                        print('  -> MATCH! Selecting ' + node_name)
                        n.setSelected(True)
                        found += 1
                    elif node_parent == parent_name:
                        print('  -> Match but skipping self: ' + node_name)
                    else:
                        print('  -> No match')
                except Exception as e:
                    print('  -> Error reading parent: ' + str(e))
            else:
                print('Node: ' + node_name + ' -> No parent knob')
                
        print('====== SUMMARY ======')
        print('Total found: ' + str(found))
        print('=====================')
                
        if found:
            nuke.message('Selected ' + str(found) + ' Connect nodes targeting: ' + parent_name)
        else:
            nuke.message('No other Connect nodes found targeting: ' + parent_name)'''
            
            findConnected_knob = nuke.PyScript_Knob('findConnected', 'find connected', findConnected_code)
            findConnected_knob.setTooltip('Select all Connect nodes that reference the same parent Marker')
            findConnected_knob.setFlag(nuke.STARTLINE)
            connect.addKnob(findConnected_knob)
            
            # Hide input toggle button
            hideInputToggle_code = '''import nuke

def hideInputToggle():
    node = nuke.thisNode()
    knob = node.knob('hideInputToggle')
    hide_input_knob = node.knob('hide_input')
            
    if hide_input_knob is not None:
        # Toggle the actual hide_input value
        current_value = hide_input_knob.value()
        hide_input_knob.setValue(not current_value)
                
        # Update button label based on new state
        if hide_input_knob.value():
            knob.setLabel('show input')
        else:
            knob.setLabel('hide input')

# Run the function
hideInputToggle()'''
            
            hideInputToggle_knob = nuke.PyScript_Knob('hideInputToggle', 'show input', hideInputToggle_code)
            hideInputToggle_knob.setTooltip('Toggle input visibility')
            hideInputToggle_knob.clearFlag(nuke.STARTLINE)
            connect.addKnob(hideInputToggle_knob)
            
            # Toggle postage stamp button
            togglePostageStamp_code = '''import nuke

        def togglePostageStamp():
            node = nuke.thisNode()
            knob = node.knob('togglePostageStamp')
            postage_knob = node.knob('postage_stamp')
            
            if postage_knob is not None:
                # Toggle the actual postage_stamp value
                current_value = postage_knob.value()
                postage_knob.setValue(not current_value)
                
                # Update button label based on new state
                if postage_knob.value():
                    knob.setLabel('hide stamp')
                else:
                    knob.setLabel('show stamp')

        # Run the function
        togglePostageStamp()'''
            
            togglePostageStamp_knob = nuke.PyScript_Knob('togglePostageStamp', 'show stamp', togglePostageStamp_code)
            togglePostageStamp_knob.setTooltip('Toggle postage stamp visibility')
            togglePostageStamp_knob.clearFlag(nuke.STARTLINE)
            connect.addKnob(togglePostageStamp_knob)
            
            # Add Info tab
            connect.addKnob(nuke.Tab_Knob('info', 'Info'))
            
            # Version text
            version_knob = nuke.Text_Knob('version', '', '<font size="5">Connect</font><font color=#777777> v1.2</font>')
            version_knob.setFlag(nuke.STARTLINE)
            connect.addKnob(version_knob)
            
            # Empty line
            connect.addKnob(nuke.Text_Knob('', ''))
            
            # Description
            description_text = '''<strong>•</strong> <b>Connect nodes</b> act as reference points<br>that link back to this marker

        <br><i>

        <strong>•</strong> Set the "parent" field to the target marker<br>name, then use "Connect"

        <br>

        <strong>•</strong> Provides quick navigation and organization<br>in complex node graphs<br> 

        <strong>•</strong> Maintains visual connection without affecting<br>the actual node flow<br><br>

        <b><a href="https://johntothvfx.com" style="color:#777777;">John Toth © 2022</a></b><br>'''
            
            description_knob = nuke.Text_Knob('description', '', description_text)
            description_knob.setFlag(nuke.STARTLINE)
            connect.addKnob(description_knob)
            
            # Empty line
            connect.addKnob(nuke.Text_Knob('', ''))
            
            # Demo button (invisible)
            demo_code = 'nuke.message("coming soon")'
            demo_knob = nuke.PyScript_Knob('demo', '<a href="https://johntothvfx.com"><span style="color:#777777">Tool Demo</span></a>', demo_code)
            demo_knob.setTooltip('Launches the web page where it will have more documentation or a video about the node.')
            demo_knob.setFlag(nuke.INVISIBLE)
            demo_knob.setFlag(nuke.STARTLINE)
            connect.addKnob(demo_knob)
            
            # Version log button
            log_code = '''
        version_number = "1.2.1"
        context = "Other/Connect"
        modified_date = "5th June 2025"
        developer = "John Toth © 2022"
        site = "<a href='website linke here'><span style='color:#BBBBBB'>"
        log = """
        <br></i><b> v 1.0 </b><i>
        - connects the input of the node based on the parent
        <br></i><b> v 1.1 </b><i>
        - index list was added to keep an list of all connect nodes to speed up workflow.
        <br></i><b> v 1.2 </b><i>
        - index now works through a difference system that works more dynamically
        - marker system implementation has been added
        - cleaner interface
        """
        thank_you = " Special thanks to Samantha Maiolo for earlier development for this tool"

        # Retrieve node name
        name = nuke.thisNode()['CLASSIFICATION'].getValue()

        # Message components
        header = "Version Log:"
        dlm = "<b>Date Last Modified: </b>" + modified_date
        space = " "
        enter = "<br><br>"
        upper = "<b>"
        lower = "</b>"

        # Formatted message
        message = (
            f"{upper}{header}{enter}"
            f"Name: {lower}{name}<br>"
            f"{upper}Version Number: {lower}{version_number}<br>"
            f"{upper}Context: {lower}{context}{enter}"
            f"{dlm}{log}<br>"
            f"<b>Thank You:</b><br>{thank_you}<br>{enter}"
            f"</i>{upper}{site}{developer}{lower}</span></a>"
        )

        # Display the message
        nuke.message(message)'''
            
            log_knob = nuke.PyScript_Knob('log', '<a href="https://johntothvfx.com"><span style="color:#777777">Version Log</span></a>', log_code)
            log_knob.setTooltip('Contains information about this node.\n\n- classification\n- context\n- date last modified\n- developer notes\n- version number\n- version log\n- year made')
            log_knob.clearFlag(nuke.STARTLINE)
            connect.addKnob(log_knob)
            
            # Create internal nodes
            connect.begin()
            
            input_node = nuke.createNode('Input', inpanel=False)
            input_node['xpos'].setValue(0)
            input_node['ypos'].setValue(-200)
            input_node['label'].setValue('[value number]')
            input_node.setName('Input')
            
            output_node = nuke.createNode('Output', inpanel=False)
            output_node.setName('Output1')
            output_node['xpos'].setValue(0)
            output_node['ypos'].setValue(-100)
            
            connect.end()
            
            # Set the parent field to the marker_name if provided
            if marker_name:
                connect['parent'].setValue(marker_name)
                # Try to connect to the marker
                marker_node = nuke.toNode(marker_name)
                if marker_node:
                    connect.setInput(0, marker_node)
                    connect['status'].setValue(f'Connected to: {marker_name}')
                    connect['tile_color'].setValue(0x4a90e2ff)
                else:
                    connect['status'].setValue(f'ERROR: {marker_name} not found')
                    connect['tile_color'].setValue(0xff4444ff)
            
            return connect
                
        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if self.action_btn.isEnabled():
                    self.execute_action()
                return
            elif event.key() == Qt.Key_Escape:
                self.reject()
                return
            elif self.mode == 'connect':
                if event.key() == Qt.Key_Down:
                    if self.search_box.hasFocus() and self.marker_list.count() > 0:
                        self.marker_list.setFocus()
                        self.marker_list.setCurrentRow(0)
                        return
                elif event.key() == Qt.Key_Up:
                    if self.marker_list.hasFocus() and self.marker_list.currentRow() == 0:
                        self.search_box.setFocus()
                        return
                        
            super(MarkerConnectUI, self).keyPressEvent(event)

    try:
        app = QtWidgets.QApplication.instance()
        parent = None
        if app:
            for widget in app.topLevelWidgets():
                if widget.metaObject().className() == 'Foundry::UI':
                    parent = widget
                    break
        
        dialog = MarkerConnectUI(parent)
        dialog.exec_()
        
    except Exception as e:
        nuke.message(f'Error creating dialog: {str(e)}')

def show_fallback_ui():
    """Fallback UI when Qt is not available"""
    choice = nuke.choice('Marker & Connect', 'What would you like to do?', 
                        ['Create Connect Node', 'Create New Marker', 'Cancel'])
    
    if choice == 0:  # Create Connect
        # Get available markers
        markers = []
        for n in nuke.allNodes():
            if (hasattr(n, 'knob') and n.knob('CLASSIFICATION') and 
                n['CLASSIFICATION'].value() == 'Marker'):
                markers.append(n.name())
        
        if not markers:
            nuke.message('No markers found')
            return
            
        marker_choice = nuke.choice('Select Marker', 'Choose marker:', markers)
        if marker_choice is not None:
            marker_name = markers[marker_choice]
            # Create simple connect node (simplified version)
            connect = nuke.createNode('NoOp')
            connect.setName('Connect_to_' + marker_name)
            nuke.message(f'Created Connect node: {connect.name()}')
            
    elif choice == 1:  # Create Marker
        result = nuke.getInput('Create Marker', 'Enter marker name:')
        if result:
            clean = result.replace(' ', '_').replace('-', '_')
            if nuke.exists(clean):
                i = 1
                while nuke.exists(f'{clean}_{i}'):
                    i += 1
                clean = f'{clean}_{i}'
            
            marker = nuke.createNode('NoOp')
            marker.setName(clean)
            nuke.message(f'Created Marker: {clean}')

# For easy testing - you can call this directly
if __name__ == '__main__':
    show_marker_connect_ui()

# ----- MENU REGISTRATION -----
def register_menu():
    menubar = nuke.menu("Nuke")
    jt_menu = menubar.addMenu("JT Package")
    prefs = load_preferences()
    shortcut = prefs.get("shortcut", DEFAULT_SHORTCUT)
    jt_menu.addCommand(
        "Marker Connect UI",
        lambda: show_marker_connect_ui(),
        shortcut
    )

register_menu()