"""==========================================================================


DEVELOPER: John Toth
https://www.linkedin.com/in/johntothvfx/
contact: Johntothvfx@gmail.com
Site: johntothvfx.com
IMDb: www.imdb.com/name/nm7230091/
=========================================================================="""

VERSION = 'v2.0.9'
UPDATE = 'Last Updated: 25th May, 2025'


###########################################################################
"""========================================================================
GLOBAL IMPORTS
========================================================================"""
###########################################################################

import nuke
import nukescripts.panels
import sys
import os
import time
import datetime


current_date = datetime.datetime.now().date()
currentPath  = os.path.dirname(os.path.abspath(__file__))



###########################################################################
"""========================================================================
NUKE VERSION, NUKE TAGS
========================================================================"""
###########################################################################

def addmenuItem(MenuItem, menu_text, function_to_execute=None, icon=None, tag=None, is_menu=False):
    if nuke.NUKE_VERSION_MAJOR >= 14 and tag:
        if is_menu:
            # Creating sub-menu with tag for Nuke 14 and above
            return MenuItem.addMenu(menu_text, icon=icon, tag=tag)
        else:
            # Creating command with tag for Nuke 14 and above
            return MenuItem.addCommand(menu_text, function_to_execute, icon=icon, tag=tag, tagTarget=3)
    else:
        if is_menu:
            # Creating sub-menu for Nuke 13 and below (no tag)
            return MenuItem.addMenu(menu_text, icon=icon)
        else:
            # Creating command for Nuke 13 and below (no tag)
            return MenuItem.addCommand(menu_text, function_to_execute, icon=icon)

# example tag
#filter_classics = sub_menu.addMenu("Classics", icon="Classic.png", tag=2)
#filter_classics.addCommand("Directional Blur", "nuke.createNode(\"DirectionalBlur.nk\")", icon="DirectionalBlur.png", tag=2, tagTarget=3)


###########################################################################
"""========================================================================
DISABLING GROUP VIEWS
========================================================================"""
###########################################################################

# disabling group views for nuke.createNode and nuke.nodePaste to set disable_group_view = 1 in Nuke 16+
if nuke.NUKE_VERSION_MAJOR >= 16:
    def _set_disable_group_view(node):
        if node.Class() == "Group":
            knob = node.knob("disable_group_view")
            if knob:
                knob.setValue(1)

    _original_createNode = nuke.createNode
    def createNode_patched(*args, **kwargs):
        node = _original_createNode(*args, **kwargs)
        _set_disable_group_view(node)
        return node
    nuke.createNode = createNode_patched

    _original_nodePaste = nuke.nodePaste
    def nodePaste_patched(*args, **kwargs):
        before_nodes = set(nuke.allNodes())
        result = _original_nodePaste(*args, **kwargs)
        after_nodes = set(nuke.allNodes())
        new_nodes = after_nodes - before_nodes
        for node in new_nodes:
            _set_disable_group_view(node)
        return result
    nuke.nodePaste = nodePaste_patched



###########################################################################
"""========================================================================
PLUGIN ADDED PATH (SAFETY)
========================================================================"""
###########################################################################

class JTPluginManager:
    def __init__(self, root_folder):
        # Store the base path to JT_Toolsets root
        self.root_folder = root_folder

    def add_plugin_paths(self, tools_subfolder='Tools', python_subfolder='Python'):
        # -- Add all subdirectories inside JT_Toolsets/Tools as plugin paths
        tools_path = os.path.join(self.root_folder, tools_subfolder)
        self._add_plugin_path_recursive(tools_path)

        # -- Add JT_Toolsets/Icons path for loading custom toolbar icons
        nuke.pluginAddPath(os.path.join(self.root_folder, "Icons"))

        # -- Add JT_Toolsets/Python and its subfolders to sys.path for Python imports
        python_path = os.path.join(self.root_folder, python_subfolder)
        self._add_python_subfolders(python_path)

    def _add_plugin_path_recursive(self, path):
        # Recursively add folders containing gizmos or .nk scripts to plugin paths
        if os.path.isdir(path):
            nuke.pluginAddPath(path)
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    self._add_plugin_path_recursive(item_path)

    def _add_python_subfolders(self, base):
        # Recursively walk JT_Toolsets/Python and add folders with .py files to sys.path
        if os.path.isdir(base):
            for root, dirs, files in os.walk(base):
                if any(f.endswith(".py") for f in files):
                    if root not in sys.path:
                        sys.path.append(root)

# -- Automatically initialize the plugin manager using the current file location
JT_root_folder = os.path.dirname(__file__)
plugin_manager = JTPluginManager(JT_root_folder)
plugin_manager.add_plugin_paths()



###########################################################################
"""========================================================================
LOADS OLD PLUGINS
========================================================================"""
###########################################################################

def plugin_update():
    global all_plugins_menu

    plugin_dir = os.path.join(currentPath, 'Plugins', 'Tools')

    if not os.path.isdir(plugin_dir):
        nuke.message("Plugin directory not found:\n" + plugin_dir)
        return

    # Clear all but the first item ("Update")
    for item in all_plugins_menu.items()[1:]:
        all_plugins_menu.removeItem(item.name())

    plugin_count = 0
    folder_menus = {}

    for root, dirs, files in os.walk(plugin_dir):
        dirs.sort()
        files = sorted(files)

        relative_path = os.path.relpath(root, plugin_dir)
        if relative_path == ".":
            continue

        # Build submenu hierarchy
        menu_ref = all_plugins_menu
        parts = relative_path.split(os.sep)
        path_key = ""
        for part in parts:
            path_key = os.path.join(path_key, part)
            if path_key not in folder_menus:
                folder_menus[path_key] = menu_ref.addMenu(part)
            menu_ref = folder_menus[path_key]

        for file in files:
            ext = os.path.splitext(file)[-1]
            name = os.path.splitext(file)[0]
            full_path = os.path.join(root, file)

            if ext in ['.nk', '.gizmo', '.py']:
                plugin_count += 1
                nuke.pluginAddPath(root)

                # Use clean name — assume you've handled versioning in class name
                if ext == '.nk':
                    menu_ref.addCommand(name, lambda p=full_path: nuke.nodePaste(p))
                elif ext == '.py':
                    menu_ref.addCommand(name, lambda p=full_path: exec(open(p).read(), globals()))
                elif ext == '.gizmo':
                    menu_ref.addCommand(name, lambda n=name: nuke.createNode(n))

    nuke.message(f"{plugin_count} plugins loaded.")



###########################################################################
"""========================================================================
PYTHON SCRIPTS
========================================================================"""
###########################################################################

import axis_to_tracker
import keyframe_animator
import marker_and_connect_manager
import set_label




###########################################################################
"""========================================================================
SETTING HOLIDAY ICONS ON DATE/TIME
========================================================================"""
###########################################################################

# Check seasonal events and puts new icon
if current_date.month == 1 and current_date.day == 1:
    icon = "JT_NewYears.png"
elif current_date.month == 12 and current_date.day == 31:
    icon = "JT_NewYears.png"
elif current_date.month == 12 and 1 <= current_date.day <= 25:
    icon = "JT_Christmas_Green.png"
else:
    icon = "JT_Orange.png"




###########################################################################
"""========================================================================
JT TOOLSET TOOLBAR
========================================================================"""
###########################################################################

toolbar = nuke.toolbar("Nodes")

# THE "JOHN TOTH" MENU FOLDER
# Add the menu with the appropriate icon
toolbar = nuke.toolbar("Nodes")
menu = toolbar.addMenu("John Toth Package", icon)



# ------------------------------------------------------------------------
#  3D MENU :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("3D", icon="Cube.png")



classic = sub_menu.addMenu("3D Classic", icon="Cube.png")
classic.addCommand( 'Cone', "nuke.createNode(\"Cone.nk\")", icon="Cone.png", tag=2)

sub_menu.addSeparator()

tag_subMenu = classic.addMenu("Bag and Tag", icon="Camera.png", tag=2)
tag_subMenu.addCommand( 'Camera Bag', "nuke.createNode(\"CameraBag.nk\")", icon="CameraBag.png", tag=2)
tag_subMenu.addCommand( 'Camera Tag', "nuke.createNode(\"CameraTag.nk\")", icon="CameraTag.png", tag=2)

sub_menu.addSeparator()

sub_menu.addCommand("Axis To Tracker", "nuke.createNode(\"AxisToTracker.nk\")", icon="AxisToTracker.png")
sub_menu.addCommand("Distance from Camera", "nuke.createNode(\"DistanceFromCamera.nk\")", icon="DistanceFromCamera.png")
sub_menu.addCommand("Vertex Tracker", "nuke.createNode(\"VertexTracker.nk\")", icon="VertexTracker.png")



# ------------------------------------------------------------------------
#  AOV MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("AOV", icon="AOV.png")



sub_menu.addCommand("AOV Grade", "nuke.createNode(\"AOVGrade.nk\")", icon="AOVGrade.png")

sub_menu.addSeparator()

sub_menu.addCommand("AOV Noise", "nuke.createNode(\"AOVNoise.nk\")", icon="AOVNoise.png")
sub_menu.addCommand("AOV Matte", "nuke.createNode(\"AOVMatte.nk\")", icon="AOVMatte.png")
sub_menu.addCommand("AOV Ramp", "nuke.createNode(\"AOVRamp.nk\")", icon="AOVRamp.png")
sub_menu.addCommand("AOV Rotation", "nuke.createNode(\"AOVRotation.nk\")", icon="AOVRotation.png")
sub_menu.addCommand("AOV Point Light", "nuke.createNode(\"AOVPointLight.nk\")", icon="Shader.png")

sub_menu.addSeparator()

sub_menu.addCommand("AOV Facing Ratio", "nuke.createNode(\"AOVFacingRatio.nk\")", icon="Shader.png")
sub_menu.addCommand("AOV Fresnel", "nuke.createNode(\"AOVFresnel.nk\")", icon="Shader.png")
sub_menu.addCommand("AOV Reflections", "nuke.createNode(\"AOVReflections.nk\")", icon="Shader.png")
sub_menu.addCommand("AOV Refractions", "nuke.createNode(\"AOVRefractions.nk\")", icon="Shader.png")

sub_menu.addSeparator()

sub_menu.addCommand("Depth Convert", "nuke.createNode(\"DepthConvert.nk\")", icon="DepthConvert.png")
sub_menu.addCommand("Depth Draw Distance", "nuke.createNode(\"DepthDrawDistance.nk\")", icon="DepthDrawDistance.png")
sub_menu.addCommand("Depth From Axis", "nuke.createNode(\"DepthFromAxis.nk\")", icon="DepthFromAxis.png")
sub_menu.addCommand("Depth to Normals", "nuke.createNode(\"DepthToNormals.nk\")", icon="DepthToNormals.png")
sub_menu.addCommand("Depth to Position", "nuke.createNode(\"DepthToPosition.nk\")", icon="DepthToPosition.png")

sub_menu.addSeparator()

#sub_menu.addCommand("Normals Convert", "nuke.createNode(\"NormalsConvert.nk\")", icon="Shader.png")
sub_menu.addCommand("Normals Relight", "nuke.createNode(\"NormalsRelight.nk\")", icon="NormalsRelight.png")
sub_menu.addCommand("Normals To UV", "nuke.createNode(\"NormalsToUV.nk\")", icon="NormalsToUV.png")

sub_menu.addSeparator()

sub_menu.addCommand("Position Convert", "nuke.createNode(\"PositionConvert.nk\")", icon="PositionConvert.png")
sub_menu.addCommand("Position to Axis", "nuke.createNode(\"PositionToAxis.nk\")", icon="PositionToAxis.png")
sub_menu.addCommand("Position to Depth", "nuke.createNode(\"PositionToDepth.nk\")", icon="PositionToDepth.png")
sub_menu.addCommand("Position to Normals", "nuke.createNode(\"PositionToNormals.nk\")", icon="PositionToNormals.png")
sub_menu.addCommand("Position to Tracker", "nuke.createNode(\"PositionToTracker.nk\")", icon="PositionToTracker.png")



# ------------------------------------------------------------------------
#  CHANNEL MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Channel", icon="Channel.png")

shufflepresets = sub_menu.addMenu("Shuffle Presets", icon="Shuffle.png")
addmenuItem(shufflepresets, "Shuffle - Alpha", "nuke.createNode('Shuffle - Alpha (classic).nk')", icon="ShuffleAlpha.png", tag=2)
addmenuItem(shufflepresets, "Shuffle - Black", "nuke.createNode('Shuffle - Black (classic).nk')", icon="ShuffleBlack.png", tag=2)
addmenuItem(shufflepresets, "Shuffle - Depth", "nuke.createNode('Shuffle - Depth (classic).nk')", icon="ShuffleDepth.png", tag=2)
addmenuItem(shufflepresets, "Shuffle - RGB", 'nuke.nodePaste("{}/Tools/Channel/Shuffles/Shuffle - RGB (classic).nk")'.format(currentPath), icon="Shuffle.png", tag=2)
addmenuItem(shufflepresets, "Shuffle - White", "nuke.createNode('Shuffle - White (classic).nk')", icon="ShuffleWhite.png", tag=2)

shufflepresets.addSeparator()

shufflepresets.addCommand("Shuffle2 - Depth", "nuke.createNode(\"Shuffle - Depth.nk\")", icon="ShuffleDepth.png",)


sub_menu.addSeparator()

sub_menu.addCommand("Channel Exists", "nuke.createNode(\"ChannelExists.nk\")", icon="ChannelExists.png")
sub_menu.addCommand("Channel Sampler", "nuke.createNode(\"ChannelSampler.nk\")", icon="ChannelSampler.png")
sub_menu.addCommand("Channel List", "nuke.createNode(\"ChannelList.nk\")", icon="ChannelList.png")
sub_menu.addCommand("Channel Suffix Remover", "nuke.createNode(\"ChannelSuffixRemover.nk\")", icon="ChannelSuffixRemover.png")
sub_menu.addCommand("Copy Layers", "nuke.createNode(\"CopyLayers.nk\")", icon="CopyLayers.png")
sub_menu.addCommand("Layer Combine", "nuke.createNode(\"LayerCombine.nk\")", icon="LayerCombine.png")
sub_menu.addCommand("Layer Select", "nuke.createNode(\"LayerSelect.nk\")", icon="LayerSelect.png")
sub_menu.addCommand("Purge BBox", "nuke.createNode(\"PurgeBBox.nk\")", icon="PurgeBBox.png")
sub_menu.addCommand("Matte Select", "nuke.createNode(\"MatteSelect.nk\")", icon="MatteSelect.png")
sub_menu.addCommand("Remove Layers", "nuke.createNode(\"RemoveLayers.nk\")", icon="RemoveLayers.png")



# ------------------------------------------------------------------------
#  COLOR MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#-------------------------------------------------------------------------

sub_menu = menu.addMenu("Color", icon="Color.png")



ColorMath_subMenu = sub_menu.addMenu("Math", icon="ColorMath.png")
ColorMath_subMenu.addCommand("Binary Buddy", "nuke.createNode(\"BinaryBuddy.nk\")", icon="BinaryBuddy.png")
ColorMath_subMenu.addCommand("Falloff", "nuke.createNode(\"Falloff.nk\")", icon="Falloff.png")
ColorMath_subMenu.addCommand("Splice", "nuke.createNode(\"Splice.nk\")", icon="Splice.png")

sub_menu.addSeparator()

sub_menu.addCommand("Color Converter", "nuke.createNode(\"ColorConverter.nk\")", icon="ColorConverter.png")
sub_menu.addCommand("Color Sampler", "nuke.createNode(\"ColorSampler.nk\")", icon="ColorSampler.png")
sub_menu.addCommand("Copy Chroma", "nuke.createNode(\"CopyChroma.nk\")", icon="CopyChroma.png")
sub_menu.addCommand("CopyHSL", "nuke.createNode(\"CopyHSL.nk\")", icon="CopyHSL.png")
sub_menu.addCommand("Frame Stat", "nuke.createNode(\"FrameStat.nk\")", icon="FrameStat.png")
sub_menu.addCommand("Hue Blur", "nuke.createNode(\"HueBlur.nk\")", icon="HueBlur.png")
sub_menu.addCommand("Hue Rotate", "nuke.createNode(\"HueRotate.nk\")", icon="HueRotate.png")
sub_menu.addCommand("Lift", "nuke.createNode(\"Lift.nk\")", icon="Lift.png")
sub_menu.addCommand("LumaGrade", "nuke.createNode(\"LumaGrade.nk\")", icon="LumaGrade.png")
sub_menu.addCommand("Monochrome", "nuke.createNode(\"Monochrome.nk\")", icon="Monochrome.png")
sub_menu.addCommand("Rolloff", "nuke.createNode(\"Rolloff.nk\")", icon="Rolloff.png")
sub_menu.addCommand("Vibrance", "nuke.createNode(\"Vibrance.nk\")", icon="Vibrance.png")



# ------------------------------------------------------------------------
#  DEEP MENU :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Deep", icon="Deep.png")



sub_menu.addSeparator()

sub_menu.addCommand("Deep Add Channel", "nuke.createNode(\"DeepAddChannel.nk\")", icon="DeepAddChannel.png")
sub_menu.addCommand("Deep Add Sample", "nuke.createNode(\"DeepAddSample.nk\")", icon="DeepAddSample.png")
sub_menu.addCommand("Deep AdjBBox", "nuke.createNode(\"DeepAdjBBox.nk\")", icon="DeepAdjBBox.png")
sub_menu.addCommand("Deep Auto Holdouts", "nuke.createNode(\"DeepAutoHoldouts.nk\")", icon="DeepAutoHoldouts.png")
sub_menu.addCommand("Deep CopyBBox", "nuke.createNode(\"DeepCopyBBox.nk\")", icon="DeepCopyBBox.png")
sub_menu.addCommand("Deep Exposure", "nuke.createNode(\"DeepExposure.nk\")", icon="DeepExposure.png")
sub_menu.addCommand("Deep From Depth", "nuke.createNode(\"DeepFromDepth.nk\")", icon="DeepFromDepth.png")
sub_menu.addCommand("Deep Keymix", "nuke.createNode(\"DeepKeymix.nk\")", icon="DeepKeymix.png")
sub_menu.addCommand("Deep Mirror", "nuke.createNode(\"DeepMirror.nk\")", icon="DeepMirror.png")
sub_menu.addCommand("Deep Soften", "nuke.createNode(\"DeepSoften.nk\")", icon="DeepSoften.png")
sub_menu.addCommand("Deep STMap", "nuke.createNode(\"DeepSTMap.nk\")", icon="DeepSTMap.png")
sub_menu.addCommand("Deep to Depth", "nuke.createNode(\"DeepToDepth.nk\")", icon="DeepToDepth.png")
sub_menu.addCommand("Deep to Position", "nuke.createNode(\"DeepToPosition.nk\")", icon="DeepToPosition.png")
sub_menu.addCommand("Deep to Utility", "nuke.createNode(\"DeepToUtility.nk\")", icon="DeepToUtility.png")


# ------------------------------------------------------------------------
#  DRAW MENU :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Draw", icon="Draw.png")



sub_menu.addCommand("Alpha Edge", "nuke.createNode(\"AlphaEdge.nk\")", icon="AlphaEdge.png")
sub_menu.addCommand("Atmos Magic", "nuke.createNode(\"AtmosMagic.nk\")", icon="AtmosMagic.png")
sub_menu.addCommand("Light Wrap", "nuke.createNode(\"LightWrap.nk\")", icon="LightWrap.png")
sub_menu.addCommand("Spherical Noise", "nuke.createNode(\"SphericalNoise.nk\")", icon="SphericalNoise.png")
sub_menu.addCommand("Stripes", "nuke.createNode(\"Stripes.nk\")", icon="Stripes.png")
sub_menu.addCommand("Rainbow", "nuke.createNode(\"Rainbow.nk\")", icon="Rainbow.png")
sub_menu.addCommand("Text Overlay", "nuke.createNode(\"TextOverlay.nk\")", icon="TextOverlay.png")
sub_menu.addCommand("UV map", "nuke.createNode(\"UVmap.nk\")", icon="UV.png")
sub_menu.addCommand("Vector Expressions", "nuke.createNode(\"VectorExpressions.nk\")", icon="VectorExpressions.png")

# ------------------------------------------------------------------------
#  FILTER MENU :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Filter", icon="Filter.png")


filter_classics = addmenuItem(sub_menu, "classics", is_menu=True, icon="Classic.png", tag=2)
addmenuItem(filter_classics, "Directional Blur", "nuke.createNode('DirectionalBlur.nk')", icon="DirectionalBlur.png", tag=2)
addmenuItem(filter_classics, "Radial Blur", f'nuke.nodePaste("{currentPath}/Tools/Filter/Classic/RadialBlur.nk")', icon="RadialBlur.png", tag=2)
addmenuItem(filter_classics, "Zoom Blur", f'nuke.nodePaste("{currentPath}/Tools/Filter/Classic/ZoomBlur.nk")', icon="ZoomBlur.png", tag=2)


sub_menu.addSeparator()

sub_menu.addCommand("ColorDilate", "nuke.createNode(\"ColorDilate.nk\")", icon="ColorDilate.png")
sub_menu.addCommand("Diffuser", "nuke.createNode(\"Diffuser.nk\")", icon="Diffuser.png")
sub_menu.addCommand("Distant Edge", "nuke.createNode(\"DistantEdge.nk\")", icon="DistantEdge.png")
sub_menu.addCommand("Erode (Sub Pixel)", "nuke.createNode(\"SubErode.nk\")", icon="SubErode.png")
sub_menu.addCommand("Exponential Glow", "nuke.createNode(\"ExponentialGlow.nk\")", icon="ExponentialGlow.png")
sub_menu.addCommand("Flexi Blur", "nuke.createNode(\"FlexiBlur.nk\")", icon="FlexiBlur.png")
sub_menu.addCommand("Fractal Blur", 'nuke.nodePaste("{}/Tools/Filter/FractalBlur.nk")'.format(currentPath), icon="FractalBlur.png")
sub_menu.addCommand("IBlur", "nuke.createNode(\"IBlur.nk\")", icon="IBlur.png")
sub_menu.addCommand("IErode", "nuke.createNode(\"IErode.nk\")", icon="IErode.png")
sub_menu.addCommand("Multi Blur", 'nuke.nodePaste("{}/Tools/Filter/MultiBlur.nk")'.format(currentPath), icon="MultiBlur.png")
sub_menu.addCommand("Pixelate", "nuke.createNode(\"Pixelate.nk\")", icon="Pixelate.png")
sub_menu.addCommand("Vector Denoise", "nuke.createNode(\"VectorDenoise.nk\")", icon="VectorDenoise.png")


# ------------------------------------------------------------------------
#  KEYER MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Keyer", icon="Keyer.png")



sub_menu.addCommand("Difference key", "nuke.createNode(\"DifferenceKey.nk\")", icon="DifferenceKey.png")
sub_menu.addCommand("IBKColour Stacker", "nuke.createNode(\"IBKColourStacker.nk\")", icon="IBKColourStacker.png")
sub_menu.addCommand("ID Picker", "nuke.createNode(\"IDPicker.nk\")", icon="IDPicker.png")
sub_menu.addCommand("Keyer Extra", "nuke.createNode(\"KeyerExtra.nk\")", icon="KeyerExtra.png")



# ------------------------------------------------------------------------
#  MERGE MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Merge", icon="Merge.png")


precomp_switch = sub_menu.addMenu("Precomp Switch", icon="PrecompSwitch_Orange.png")
precomp_switch.addCommand("Precomp Switch Module", "nuke.createNode(\"PrecompSwitchModule.nk\")", icon="PrecompSwitch_Red.png")
precomp_switch.addCommand("Precomp Switch", "nuke.createNode(\"PrecompSwitch.nk\")", icon="PrecompSwitch_Green.png")

sub_menu.addSeparator()

sub_menu.addCommand("Contact Sheet Plus", "nuke.createNode(\"ContactSheetPlus.nk\")", icon="ContactSheet.png")
sub_menu.addCommand("Custom Switch", "nuke.createNode(\"CustomSwitch.nk\")", icon="CustomSwitch.png")
sub_menu.addCommand("Depth Merge", "nuke.createNode(\"DepthMerge.nk\")", icon="DepthMerge.png")
sub_menu.addCommand("Layer Contact Sheet (Input BBox)", "nuke.createNode(\"Layer Contact Sheet.nk\")", icon="LayerContactSheet.png")
sub_menu.addCommand("Premult Extra", "nuke.createNode(\"Premult Extra.nk\")", icon="Premult.png")
sub_menu.addCommand("Unpremult Extra", "nuke.createNode(\"Unpremult Extra.nk\")", icon="Unpremult.png")



# ------------------------------------------------------------------------
#  OPTICAL MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Optical", icon="Optical.png")

flare_subMnu = addmenuItem(sub_menu, "Lens Flare", is_menu=True, icon="LensFlare.png", tag=1)

addmenuItem(flare_subMnu, "Lens Flare Info", "nuke.createNode('LensFlareInfo.nk')", icon="LensFlareInfo.png", tag=1)
addmenuItem(flare_subMnu, "Lens Flare Sun", "nuke.createNode('LensFlareSun.nk')", icon="LensFlareSun.png", tag=1)
addmenuItem(flare_subMnu, "Lens Flare From Image", "nuke.createNode('LensFlareFromImage.nk')", icon="LensFlareSun.png", tag=1)



sub_menu.addCommand("Depth of Field", "nuke.createNode(\"DepthofField.nk\")", icon="DepthofField.png")
sub_menu.addCommand("Depth Visualizer", "nuke.createNode(\"DepthVisualizer.nk\")", icon="DepthVisualizer.png")
sub_menu.addCommand("Lens Smudge", "nuke.createNode(\"LensSmudge.nk\")", icon="LensSmudge.png")



# ------------------------------------------------------------------------
#  OTHER MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Other", icon="Other.png")



#breakdown_subMenu = sub_menu.addMenu("Breakdowns", icon="ToolbarToolsets.png")
#breakdown_2D = breakdown_subMenu.addMenu("2D", icon="2D.png")
#breakdown_2D.addCommand("Jt Breakdown Grid", "nuke.createNode(\"Jt Breakdown Grid.nk\")", icon="Breakdown Grid.png")

#breakdown_3D = breakdown_subMenu.addMenu("3D", icon="3D.png")
#breakdown_3D.addCommand("test", "nuke.createNode(\"Jt Breakdown Grid.nk\")", icon="Breakdown Grid.png")

sub_menu.addSeparator()

input_process = sub_menu.addMenu("Connect", icon="Connect.png")
input_process.addCommand("Connect", "nuke.createNode(\"Connect.nk\")", icon="Connect.png")
input_process.addCommand("Marker", "nuke.createNode(\"Marker.nk\")", icon="Marker.png")


#BackdropPreset
sub_menu.addSeparator()
#sub_menu.addCommand("Backdrop Presets", "nuke.createNode(\"BackdropPresets.nk\")", icon="BackdropPresets.png", tag=1, tagTarget=3)

# Define the file path
preset_path = os.path.expanduser('~/.nuke/JT_Toolsets/Tools/Other/BackdropPresets/BackdropPresetsTemp.nk')

# Function to create Backdrop Preset node
def create_backdrop_preset_node():
    if os.path.isfile(preset_path):
        nuke.nodePaste(preset_path)
    else:
        nuke.createNode("BackdropPresets.nk")

# Add Backdrop Presets command to the menu
addmenuItem(sub_menu, "Backdrop Presets", lambda: create_backdrop_preset_node(), icon="BackdropPresets.png", tag=1)



# ------------------------------------------------------------------------
#  PARTICLES MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Particles", icon="Particles.png")



sub_menu.addCommand("Particle Opacity", "nuke.createNode(\"ParticleOpacity.nk\")", icon="ParticleOpacity.png")
sub_menu.addCommand("Particle Magnet", "nuke.createNode(\"ParticleMagnet.nk\")", icon="ParticleMagnet.png")



# ------------------------------------------------------------------------
#  UTILITY MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Utility", icon="Utility.png")



sub_menu.addSeparator()

input_process = sub_menu.addMenu("Input Process", icon="IP_Orange.png")
input_process.addCommand("Set Input Process (VIEWER INPUT)", "nuke.createNode(\"SetInputProcess.nk\")", icon="SetInputProcess.png")
input_process.addCommand("Set Input Process Group (VIEWER INPUT)", "nuke.createNode(\"SetInputProcessGroup.nk\")", icon="SetInputProcessGroup.png")


sub_menu.addSeparator()

#python_subMenu = sub_menu.addMenu("Python", icon="Python.png")
#python_examples = python_subMenu.addMenu("Examples", icon="Python.png")
#python_examples.addCommand("Python (Callback) Example - Disable Knob", "nuke.createNode(\"Python (Callback)  Example - Disable Knob.nk\")", icon="Python.png")
#python_examples.addCommand("Python Example - lock and unlock toggle", "nuke.createNode(\"Python Example - lock and unlock toggle.nk\")", icon="Python.png")

sub_menu.addSeparator()

sub_menu.addCommand("Configure Knobs", "nuke.createNode(\"ConfigureKnobs.nk\")", icon="ConfigureKnobs.png")
sub_menu.addCommand("Disable Write Nodes", "nuke.createNode(\"DisableWriteNodes.nk\")", icon="DisableWriteNodes.png")
sub_menu.addCommand("Get Render", "nuke.createNode(\"GetRender.nk\")", icon="GetRender.png")
sub_menu.addCommand("Kill All Viewers", "nuke.createNode(\"KillAllViewers.nk\")", icon="KillAllViewers.png")
sub_menu.addCommand("Plot Scanline", "nuke.createNode(\"PlotScanline.nk\")", icon="miscellaneous.png")
sub_menu.addCommand("Save Node Selection", "nuke.createNode(\"SaveNodeSelection.nk\")", icon="SaveNodeSelection.png")
sub_menu.addCommand("Script Manager", "nuke.createNode(\"ScriptManager.nk\")", icon="ScriptManager.png")
#sub_menu.addCommand("Script Runner", "nuke.createNode(\"ScriptRunner.nk\")", icon="miscellaneous.png")


# ------------------------------------------------------------------------
#  TEMPLATE MENU :::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Template", icon="Templates.png")



template_3D_subMenu = sub_menu.addMenu("3D Templates", icon="Template3D.png")
addmenuItem(template_3D_subMenu, "Template - Projection 3D", lambda: nuke.nodePaste("{}/Tools/Template/3D/Template - Project3D (classic).nk".format(currentPath)), icon="Template3D.png", tag=2)


#template_CG_subMenu = sub_menu.addMenu("CG Templates", icon="TemplateAOV.png")
#template_CG_subMenu.addCommand("Template - CG Template", 'nuke.nodePaste("{}/Tools/Template/Template - CG Template.nk")'.format(currentPath), icon="TemplateAOV.png")



template_channel_subMenu = sub_menu.addMenu("Channel Template", icon="TemplateChannel.png")
template_channel_subMenu.addCommand("Template - Restore Plate.nk", 'nuke.nodePaste("{}/Tools/Template/Channel/Template - Restore Plate.nk")'.format(currentPath), icon="TemplateChannel.png")



template_draw_subMenu = sub_menu.addMenu("Draw Template", icon="TemplateDraw.png")
template_draw_subMenu.addCommand("Template - UV map", 'nuke.nodePaste("{}/Tools/Template/Draw/Template - UV map.nk")'.format(currentPath), icon="TemplateTransform.png")
template_draw_subMenu.addCommand("Template - Rainbow Ramp", 'nuke.nodePaste("{}/Tools/Template/Draw/Template - Rainbow Ramp.nk")'.format(currentPath), icon="TemplateTransform.png")



template_image_subMenu = sub_menu.addMenu("Image Template", icon="TemplateImage.png")
template_image_subMenu.addCommand("Template - Precomp", 'nuke.nodePaste("{}/Tools/Template/Image/Template - Precomp.nk")'.format(currentPath), icon="TemplateImage.png")



template_keyer_subMenu = sub_menu.addMenu("Keying Template", icon="TemplateKeyer.png")
#template_keyer_subMenu.addCommand("Template - AdditiveKeyer", 'nuke.nodePaste("{}/Tools/Template/Keyer/Template - AdditiveKeyer.nk")'.format(currentPath), icon="TemplateKeyer.png")
template_keyer_subMenu.addCommand("Template - Log Keyer", 'nuke.nodePaste("{}/Tools/Template/Keyer/Template - Log Keyer.nk")'.format(currentPath), icon="TemplateKeyer.png")



template_merge_subMenu = sub_menu.addMenu("Merge Template", icon="TemplateMerge.png")
template_merge_subMenu.addCommand("Template - OCIO Log Merge", 'nuke.nodePaste("{}/Tools/Template/Merge/Template - OCIO Log Merge.nk")'.format(currentPath), icon="TemplateMerge.png")



template_optical_subMenu = sub_menu.addMenu("Optical Template", icon="TemplateOptical.png")
template_optical_subMenu.addCommand("Template - Chromatic Aberration", 'nuke.nodePaste("{}/Tools/Template/Optical/Template - Chromatic Aberration (Godrays).nk")'.format(currentPath), icon="TemplateOptical.png")
template_optical_subMenu.addCommand("Template - Chromatic Aberration Merge", 'nuke.nodePaste("{}/Tools/Template/Optical/Template - Chromatic Aberration Merge.nk")'.format(currentPath), icon="TemplateOptical.png")
template_optical_subMenu.addCommand("Template - Fringing", 'nuke.nodePaste("{}/Tools/Template/Optical/Template - Fringing.nk")'.format(currentPath), icon="TemplateOptical.png")
template_optical_subMenu.addCommand("Template - Grain", 'nuke.nodePaste("{}/Tools/Template/Optical/Template - Grain.nk")'.format(currentPath), icon="TemplateOptical.png")



template_other_subMenu = sub_menu.addMenu("Other Template", icon="TemplateOther.png")
template_other_subMenu.addCommand("Template - Shot Reference backdrops", 'nuke.nodePaste("{}/Tools/Template/Other/Template - Shot Reference backdrops.nk")'.format(currentPath), icon="TemplateOther.png")



template_particle_subMenu = sub_menu.addMenu("Particle Template", icon="TemplateParticles.png")
template_particle_subMenu.addCommand("Template - Particle Atmospherics at Camera", 'nuke.nodePaste("{}/Tools/Template/Particles/Template - Particle Atmospherics at Camera.nk")'.format(currentPath), icon="TemplateParticles.png")



template_transform_subMenu = sub_menu.addMenu("Transform Template", icon="TemplateTransform.png")




#template_utility_subMenu = sub_menu.addMenu("Utility Template", icon="ToolbarToolsets.png")
#template_utility_subMenu.addCommand("Template - Compositing Startup", 'nuke.nodePaste("{}/Tools/Template/Template - Compositing Startup.nk")'.format(currentPath), icon="Backdrop.png")



##template_QC_subMenu = sub_menu.addMenu("QC Template", icon="QualityCheck.png")
#template_QC_subMenu.addCommand("Template - Compositing QC", 'nuke.nodePaste("{}/Tools/Template/Template - Compositing QC.nk")'.format(currentPath), icon="Backdrop.png")



# ------------------------------------------------------------------------
#  TIME MENU :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Time", icon="Time.png")



sub_menu.addCommand("Frame Counter", "nuke.createNode(\"FrameCounter.nk\")", icon="FrameCounter.png")
sub_menu.addCommand("Frame Fader", "nuke.createNode(\"FrameFader.nk\")", icon="FrameFader.png")
sub_menu.addCommand("Frame Repair", "nuke.createNode(\"FrameRepair.nk\")", icon="FrameRepair.png")
sub_menu.addCommand("Frame Skip", "nuke.createNode(\"Frame Skip.nk\")", icon="FrameSkip.png")
sub_menu.addCommand("Time Code", "nuke.createNode(\"TimeCode.nk\")", icon="TimeCode.png")
sub_menu.addCommand("Time Transfer", "nuke.createNode(\"TimeTransfer.nk\")", icon="TimeTransfer.png")



# ------------------------------------------------------------------------
#  TRANSFORM MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Transform", icon="Transform.png")

transformPoint_subMenu = sub_menu.addMenu("Math", icon="ColorMath.png")
transformPoint = transformPoint_subMenu.addMenu("TransformPoint", icon="TransformPoint.png")
transformPoint_subMenu.addCommand( 'TargetPoint', "nuke.createNode(\"TargetPoint.nk\")", icon="TargetPoint.png")

sub_menu.addSeparator()

distortion_subMenu = sub_menu.addMenu("Distortion", icon="STMap.png")
distortion_subMenu.addCommand( 'Distorter', "nuke.createNode(\"Distorter.nk\")", icon="Distorter.png")
#distortion_subMenu.addCommand( 'Ripple', lambda: nuke.message('Coming Soon'), icon='Liquid.png')
#distortion_subMenu.addCommand( 'Heat Distortion', lambda: nuke.message('Coming Soon'), icon='Heat.png')

sub_menu.addSeparator()

sub_menu = menu.addMenu("Transform", icon="Transform.png")
sub_menu.addCommand("AdjBBox Extra", "nuke.createNode(\"AdjBBoxExtra.nk\")", icon="AdjBBoxExtra.png")
sub_menu.addCommand("AutoCrop", "nuke.createNode(\"AutoCrop.nk\")", icon="AutoCrop.png")
sub_menu.addCommand("Crop Box", "nuke.createNode(\"CropBox.nk\")", icon="CropBox.png")
sub_menu.addCommand("Copy Format", "nuke.createNode(\"CopyFormat.nk\")", icon="CopyFormat.png")

sub_menu.addCommand("ITransform", 'nuke.nodePaste("{}/Tools/Transform/ITransform.nk")'.format(currentPath), icon="ITransform.png")
sub_menu.addCommand("Pixel Offset", "nuke.createNode(\"Pixel Offset.nk\")", icon="PixelOffset.png")
sub_menu.addCommand("Tile Extra", "nuke.createNode(\"Tile.nk\")", icon="TileExtra.png")
sub_menu.addCommand("Tile Image", "nuke.createNode(\"TileImage.nk\")", icon="TileImage.png")


# ------------------------------------------------------------------------
#  QUALITY CHECK MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Quality Check", icon="QualityCheck.png")


sub_menu.addCommand("Pixel Police", "nuke.createNode(\"PixelPolice.nk\")", icon="PixelPoliceColour.png")
sub_menu.addCommand("Pixel Repair", "nuke.createNode(\"PixelRepair.nk\")", icon="PixelRepair.png")
sub_menu.addCommand("PixelQC", "nuke.createNode(\"PixelQC.nk\")", icon="PixelQC.png")
sub_menu.addCommand("RotoCheck", "nuke.createNode(\"RotoCheck.nk\")", icon="RotoCheck.png")



# ------------------------------------------------------------------------
#  Developer ::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------

sub_menu = menu.addMenu("Developer", icon="Terminal.png")

autocomp = sub_menu.addMenu("Autocomp", icon="Autocomp.png")

builder = autocomp.addMenu("Builders", icon="Builders.png")
builder.addCommand("AOV Builder", "nuke.createNode(\"AOVBuilder.nk\")", icon="AOVBuilder.png")

sub_menu.addSeparator()

sub_menu.addCommand("Node Generator", "nuke.createNode(\"NodeGenerator.nk\")", icon="NodeGenerator.png")

sub_menu.addSeparator()

sub_menu.addCommand("ClassRender", "nuke.createNode(\"ClassReader.nk\")", icon="ClassReader.png")

sub_menu.addSeparator()

sub_menu.addCommand("Developer Cam", "nuke.createNode(\"DeveloperCam.nk\")", icon="DeveloperCam.png")
sub_menu.addCommand("Node Finder", "nuke.createNode(\"NodeFinder.nk\")", icon="NodeFinder.png")


# ------------------------------------------------------------------------
#  INFORMATION MENU ::::::::::::::::::::::::::::::::::::::::::::::::::::
# ------------------------------------------------------------------------


sub_menu = menu.addMenu("Information", icon="Information.png")



# About Package Version
message = f'''
Version: {VERSION}
{UPDATE}

Hi,

Over the years, I have developed a variety of tools as part of my journey to understand and master different aspects of my craft. 
These tools, some of which have been redesigned from existing ones, reflect my learning process and evolving understanding.

Inspired by the goal of becoming a better artist and creating user-friendly tools, I have found these to be invaluable in my daily compositing work.
I am grateful to every artist I have had the pleasure of working with and learning from, and I hope these tools will be as beneficial to you as they have been to me.

Cheers,
John Toth
'''

def show_about_message():
    nuke.message(message)

sub_menu.addCommand(f'About Package {VERSION}', show_about_message, icon='Information.png')





# All Plugins menu
all_plugins_menu = sub_menu.addMenu("All Plugins", icon="Plug.png")
all_plugins_menu.addCommand("Update", plugin_update)





#LICENSE
def show_license_info():
    try:
        try:
            from PySide2 import QtWidgets
        except ImportError:
            from PySide6 import QtWidgets

        base_path = os.path.dirname(os.path.abspath(__file__))
        possible_names = ["License", "License.txt"]

        license_text = "License is not found."
        for name in possible_names:
            full_path = os.path.join(base_path, name)
            if os.path.isfile(full_path):
                with open(full_path, "r") as f:
                    license_text = f.read()
                break  # Stop once found

        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("John Toth Toolkit — License Info")
        dialog.resize(600, 400)

        layout = QtWidgets.QVBoxLayout(dialog)

        text_edit = QtWidgets.QPlainTextEdit()
        text_edit.setPlainText(license_text)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("padding: 10px; font-family: Courier; font-size: 10pt;")
        layout.addWidget(text_edit)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec_()

    except Exception as e:
        import nuke
        nuke.message("Failed to display license panel.\n\n" + str(e))




sub_menu.addCommand("License", show_license_info, icon="License.png")





