"""
properties.py - Property groups and scene settings for CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+ (Blender 4.5+ Slotted Action & Binary/Raw format support)
"""

import bpy
from bpy.props import (
    IntProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty
)


def _get_original_fps(self):
    if self.get("auto_detect_fps", True):
        try:
            scene = bpy.context.scene
            return max(1, int(round(scene.render.fps / scene.render.fps_base)))
        except Exception:
            return self.get("original_fps", 30)
    return self.get("original_fps", 30)


def _set_original_fps(self, value):
    self["original_fps"] = max(1, int(value))
    self["auto_detect_fps"] = False


def _get_target_fps(self):
    val = self.get("target_fps", 0)
    if val > 0:
        return val
    orig = _get_original_fps(self)
    return 30 if orig >= 60 else 60


def _set_target_fps(self, value):
    self["target_fps"] = max(1, int(value))


class CBW1_SceneProperties(bpy.types.PropertyGroup):
    """Scene properties for FPS adjustment and Action export/import settings."""

    # Export Format setting (Raw vs Binary)
    export_format: EnumProperty(
        name="Export Anim Format",
        description="Choose between human-readable Raw format or compact Binary format",
        items=[
            ('BINARY', "Binary (Compact)", "High-compression binary format (.cbw1anim) to reduce file size"),
            ('RAW', "Raw (JSON)", "Human-readable JSON text format (.cbw1anim)"),
        ],
        default='BINARY'
    )

    auto_detect_fps: BoolProperty(
        name="Auto Scene FPS",
        description="Automatically detect and adapt to the current Scene FPS",
        default=True
    )

    original_fps: IntProperty(
        name="Original FPS",
        description="The original frames per second of the source animation (auto-synced with Scene FPS)",
        get=_get_original_fps,
        set=_set_original_fps,
        min=1,
        max=240
    )

    target_fps: IntProperty(
        name="Target FPS",
        description="The desired target frames per second for the animation",
        get=_get_target_fps,
        set=_set_target_fps,
        min=1,
        max=240
    )

    use_cutscene_markers: BoolProperty(
        name="Close Frame For Camera For CutScene",
        description="Uses Timeline Markers as CutScene cut boundaries so camera cuts are preserved without stretching, and automatically scales marker positions during FPS adjustment",
        default=True
    )


# Backward compatibility alias
CBAnimTool_SceneProperties = CBW1_SceneProperties

classes = (
    CBW1_SceneProperties,
)


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    bpy.types.Scene.cbw1_props = PointerProperty(type=CBW1_SceneProperties)
    bpy.types.Scene.bdcbanim_props = PointerProperty(type=CBW1_SceneProperties)


def unregister():
    if hasattr(bpy.types.Scene, "cbw1_props"):
        del bpy.types.Scene.cbw1_props

    if hasattr(bpy.types.Scene, "bdcbanim_props"):
        del bpy.types.Scene.bdcbanim_props

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
