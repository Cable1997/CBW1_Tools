"""
CBW1_Tool - Animation Action & FPS Management Add-on for Blender.
Author: Nampukkk
Target: Blender 4.2+
"""

bl_info = {
    "name": "CBW1 Tools",
    "author": "Nampukkk",
    "version": (1, 0, 0),
    "blender": (4, 5, 14),
    "location": "3D Viewport > Sidebar > CBW1_Tool",
    "description": "CBW1 Animation Tools: Action Export/Import, FPS Adjustment, and Close Keyframe Management",
    "category": "Animation",
}

# Reload handling when reloaded within Blender
if "bpy" in locals():
    import importlib
    if "utils" in locals():
        importlib.reload(utils)
    if "properties" in locals():
        importlib.reload(properties)
    if "operators" in locals():
        importlib.reload(operators)
    if "ui" in locals():
        importlib.reload(ui)

import bpy
from . import utils
from . import properties
from . import operators
from . import ui


def register():
    properties.register()
    operators.register()
    ui.register()
    print("CBW1_Tool Add-on Registered!")


def unregister():
    ui.unregister()
    operators.unregister()
    properties.unregister()
    print("CBW1_Tool Add-on Unregistered!")


if __name__ == "__main__":
    register()