"""
UI Panel registration for CBW1_Tool.
"""

import bpy
from . import panels


def register():
    for cls in panels.classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass


def unregister():
    for cls in reversed(panels.classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
