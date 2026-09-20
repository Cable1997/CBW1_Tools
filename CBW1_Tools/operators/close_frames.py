"""
close_frames.py - Timeline Marker Operators for CutScene Close Keyframe Detection in CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+ / Blender 4.5+ LTS
"""

import bpy
from ..utils import anim_utils


class CBW1_OT_CreateMarkersFromCuts(bpy.types.Operator):
    """Detect cut transitions in the active Action and create Timeline Markers automatically"""
    bl_idname = "cbw1.create_markers_from_cuts"
    bl_label = "Detect Cuts → Add Markers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        action = None
        if obj and obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
        else:
            for sel in context.selected_objects:
                if sel.animation_data and sel.animation_data.action:
                    action = sel.animation_data.action
                    break

        if not action:
            self.report({'ERROR'}, "Please select an animated object (Camera, Rig, or Mesh) with an active Action.")
            return {'CANCELLED'}

        detected_pairs = anim_utils.detect_close_keyframe_pairs(action)
        if not detected_pairs:
            self.report({'WARNING'}, f"No cut transitions found in Action '{action.name}'.")
            return {'CANCELLED'}

        scene = context.scene
        existing_frames = {m.frame for m in scene.timeline_markers}
        created_count = 0

        for i, (head, tail) in enumerate(detected_pairs, 1):
            cut_frame = tail
            if cut_frame not in existing_frames:
                scene.timeline_markers.new(name=f"Cut_{i:02d}", frame=cut_frame)
                existing_frames.add(cut_frame)
                created_count += 1

        self.report({'INFO'}, f"Added {created_count} cut marker(s) to Timeline (from {len(detected_pairs)} cuts).")
        return {'FINISHED'}


class CBW1_OT_ClearCutMarkers(bpy.types.Operator):
    """Clear all Timeline Markers"""
    bl_idname = "cbw1.clear_cut_markers"
    bl_label = "Clear Timeline Markers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = len(context.scene.timeline_markers)
        context.scene.timeline_markers.clear()
        self.report({'INFO'}, f"Cleared {count} timeline marker(s).")
        return {'FINISHED'}


classes = (
    CBW1_OT_CreateMarkersFromCuts,
    CBW1_OT_ClearCutMarkers,
)
