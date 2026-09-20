"""
Operator registration for CBW1_Tool.
"""

import bpy
from . import io_action
from . import fps_adjust
from . import close_frames
from . import debug_reload
from . import quaternion_flip

modules = (
    io_action,
    fps_adjust,
    close_frames,
    debug_reload,
    quaternion_flip,
)


def register():
    for mod in modules:
        for cls in mod.classes:
            try:
                bpy.utils.register_class(cls)
            except ValueError:
                pass


def unregister():
    for mod in reversed(modules):
        for cls in reversed(mod.classes):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
