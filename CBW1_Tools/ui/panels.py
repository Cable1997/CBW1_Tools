"""
panels.py - UI Panels in 3D Viewport Sidebar for CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+ (Blender 4.5+ Slotted Action, Binary & Raw IO, Quaternion Flip Tools)
Minimal, clean UI design without dark boxes or bulky elements.
"""

import os
import bpy

UI_CATEGORY = "CBW1_Tool"


class CBW1_PT_MainPanel(bpy.types.Panel):
    """Main Panel for Animation Action Import and Export (Binary & Raw)"""
    bl_label = "Action ImportExport"
    bl_idname = "CBW1_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UI_CATEGORY

    def draw(self, context):
        layout = self.layout
        props = context.scene.cbw1_props
        obj = context.active_object

        # 1. Object & Action Info (Clean & Minimal labels, no dark box)
        col = layout.column(align=True)
        if obj and obj.type == 'ARMATURE':
            col.label(text=f"Rig: {obj.name}", icon='ARMATURE_DATA')
            if obj.animation_data and obj.animation_data.action:
                col.label(text=f"Action: {obj.animation_data.action.name}", icon='ACTION')
            else:
                col.label(text="No Active Action", icon='INFO')

            sk_mesh_names = [
                child.name for child in obj.children
                if child.type == 'MESH' and child.data and getattr(child.data, "shape_keys", None)
            ]
            if sk_mesh_names:
                col.label(text=f"KeyShape: {', '.join(sk_mesh_names)}", icon='SHAPEKEY_DATA')

        elif obj and obj.type == 'MESH':
            col.label(text=f"Mesh: {obj.name}", icon='MESH_DATA')
            if obj.data and getattr(obj.data, "shape_keys", None):
                sk_count = len(obj.data.shape_keys.key_blocks) - 1
                col.label(text=f"KeyShape: {max(0, sk_count)} keys detected", icon='SHAPEKEY_DATA')
            else:
                col.label(text="No KeyShape on Mesh", icon='INFO')
        else:
            col.label(text="Select Armature or Mesh", icon='INFO')

        layout.separator(factor=0.4)

        # 2. Format Selection (Dropdown menu, Binary by default)
        row = layout.row(align=True)
        row.prop(props, "export_format", text="Format")

        layout.separator(factor=0.3)

        # 3. Action Import / Export (Vertical top-to-bottom layout)
        col = layout.column(align=True)
        col.operator("cbw1.export_action", text="Export .cbw1anim", icon='EXPORT')
        col.operator("cbw1.import_action", text="Import .cbw1anim", icon='IMPORT')


class CBW1_MT_FPSPresetMenu(bpy.types.Menu):
    """Dropdown menu for selecting FPS conversion presets (Upscale & Reverse Downscale)"""
    bl_label = "FPS Presets"
    bl_idname = "CBW1_MT_FPSPresetMenu"

    def draw(self, context):
        layout = self.layout
        scene_fps = int(round(context.scene.render.fps / context.scene.render.fps_base))
        layout.label(text=f"Current Scene: {scene_fps} FPS", icon='SCENE_DATA')
        layout.separator()

        layout.label(text="Upscale (Slow → Fast):", icon='FORWARD')
        op = layout.operator("cbw1.set_fps_preset", text="15 → 60 FPS", icon='PLAY')
        op.preset_type = "15_to_60"
        op = layout.operator("cbw1.set_fps_preset", text="24 → 60 FPS", icon='PLAY')
        op.preset_type = "24_to_60"
        op = layout.operator("cbw1.set_fps_preset", text="30 → 60 FPS", icon='PLAY')
        op.preset_type = "30_to_60"

        layout.separator()
        layout.label(text="Downscale (Reverse):", icon='BACK')
        op = layout.operator("cbw1.set_fps_preset", text="60 → 30 FPS", icon='TRIA_LEFT')
        op.preset_type = "60_to_30"
        op = layout.operator("cbw1.set_fps_preset", text="60 → 24 FPS", icon='TRIA_LEFT')
        op.preset_type = "60_to_24"
        op = layout.operator("cbw1.set_fps_preset", text="30 → 15 FPS", icon='TRIA_LEFT')
        op.preset_type = "30_to_15"
        op = layout.operator("cbw1.set_fps_preset", text="60 → 15 FPS", icon='TRIA_LEFT')
        op.preset_type = "60_to_15"


class CBW1_PT_FPSAdjustmentPanel(bpy.types.Panel):
    """Panel for Keyframe Scaling and FPS Adjustment"""
    bl_label = "FPS Adjustment"
    bl_idname = "CBW1_PT_FPSAdjustmentPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UI_CATEGORY

    def draw(self, context):
        layout = self.layout
        props = context.scene.cbw1_props

        # 1. FPS Settings (Auto-adapting, clean single row with swap & refresh)
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(props, "original_fps", text="From")
        row.operator("cbw1.swap_fps", text="", icon='ARROW_LEFTRIGHT')
        row.prop(props, "target_fps", text="To")
        row.operator("cbw1.auto_sync_fps", text="", icon='FILE_REFRESH')

        layout.separator(factor=0.4)

        # 2. Quick Presets (Dropdown Menu Button)
        row = layout.row(align=True)
        row.menu("CBW1_MT_FPSPresetMenu", text="Select FPS Preset", icon='PRESET')

        layout.separator(factor=0.4)

        # 3. Close Frame For Camera For CutScene (Timeline Markers)
        col = layout.column(align=True)
        col.prop(props, "use_cutscene_markers", text="Close Frame For Camera For CutScene")

        if props.use_cutscene_markers:
            marker_count = len(context.scene.timeline_markers)
            info_row = col.row(align=True)
            if marker_count > 0:
                info_row.label(text=f"Timeline Markers: {marker_count} cut(s) detected", icon='MARKER')
            else:
                info_row.label(text="No Markers in Timeline (Auto-detecting cuts)", icon='INFO')

            btn_row = col.row(align=True)
            btn_row.operator("cbw1.create_markers_from_cuts", text="Detect Cuts → Add Markers", icon='ADD')
            if marker_count > 0:
                btn_row.operator("cbw1.clear_cut_markers", text="Clear", icon='TRASH')

        layout.separator(factor=0.5)

        # 4. Apply Button
        layout.operator("cbw1.adjust_fps", text="Apply FPS Adjustment", icon='PLAY')


class CBW1_PT_ItemFlipQuaternion(bpy.types.Panel):
    """Panel in the Item tab shown only in Pose Mode, directly below Transform"""
    bl_label = "Auto Anim FlipQuaternion"
    bl_idname = "CBW1_PT_ItemFlipQuaternion"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Item"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        # Only appears in Pose Mode on an Armature object
        return (
            context.active_object is not None
            and context.active_object.type == 'ARMATURE'
            and context.active_object.mode == 'POSE'
        )

    def draw(self, context):
        layout = self.layout
        selected_bones = context.selected_pose_bones
        if selected_bones:
            layout.operator(
                "cbw1.fix_quaternion_flips",
                text="Auto Anim FlipQuaternion",
                icon='ORIENTATION_GIMBAL'
            )
        else:
            layout.label(text="Select Bone(s) in Pose Mode", icon='INFO')


class CBW1_PT_DevPanel(bpy.types.Panel):
    """Developer and Debugging Utilities"""
    bl_label = "Developer & Debug"
    bl_idname = "CBW1_PT_DevPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UI_CATEGORY
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="CBW1_Tool v1.0.0 (by Nampukkk)", icon='PREFERENCES')
        col.operator("cbw1.reload_addon", text="Reload CBW1_Tool", icon='FILE_REFRESH')


classes = (
    CBW1_PT_ItemFlipQuaternion,
    CBW1_MT_FPSPresetMenu,
    CBW1_PT_MainPanel,
    CBW1_PT_FPSAdjustmentPanel,
    CBW1_PT_DevPanel,
)
