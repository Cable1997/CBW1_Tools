"""
fps_adjust.py - FPS scaling and curve adjustment operators for CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+
"""

from typing import List, Tuple, Dict, Any
import bpy
from bpy.props import StringProperty
from ..utils import anim_utils


class CBW1_OT_AdjustFPS(bpy.types.Operator):
    """Adjust FPS of the active Action's keyframes and curves based on Scene Properties or loaded external data"""
    bl_idname = "cbw1.adjust_fps"
    bl_label = "Apply FPS Adjustment"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cbw1_props

        original_fps = props.original_fps
        target_fps = props.target_fps

        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "Please select one or more animated objects.")
            return {'CANCELLED'}

        if original_fps <= 0 or target_fps <= 0:
            self.report({'ERROR'}, "Original and Target FPS must be positive integers.")
            return {'CANCELLED'}

        if original_fps == target_fps:
            self.report({'WARNING'}, "Original FPS and Target FPS are identical.")
            return {'CANCELLED'}

        # Update scene render FPS
        context.scene.render.fps = target_fps
        context.scene.render.fps_base = 1.0
        self.report({'INFO'}, f"Scene FPS updated to {target_fps} FPS.")

        scale_factor = target_fps / original_fps
        max_overall_frame = 0.0
        processed_count = 0

        all_cut_pairs_map: Dict[int, int] = {}
        use_cutscene = getattr(props, "use_cutscene_markers", True)

        for obj in selected_objects:
            if not obj.animation_data or not obj.animation_data.action:
                self.report({'WARNING'}, f"Object '{obj.name}' has no active Action. Skipping.")
                continue

            action = obj.animation_data.action
            processed_count += 1

            # 1. Determine close keyframe pairs on the original unscaled action
            target_cut_pairs = []
            if use_cutscene:
                timeline_marker_frames = [m.frame for m in context.scene.timeline_markers]
                if timeline_marker_frames:
                    target_cut_pairs = anim_utils.find_cut_pairs_from_markers(action, timeline_marker_frames)
                else:
                    target_cut_pairs = anim_utils.detect_close_keyframe_pairs(action)

            # 2. Scale all keyframes and handles
            anim_utils.scale_action_keyframes(action, scale_factor)

            # 3. Locate points and apply automated Close Frame snapping
            if target_cut_pairs:
                close_pairs_data = anim_utils.find_keyframe_points_for_pairs(
                    action, target_cut_pairs, scale_factor
                )
                if close_pairs_data:
                    cut_pairs_map = anim_utils.apply_offsets_to_close_pairs(
                        action, close_pairs_data, scale_factor, auto_snap_adjacent=True
                    )
                    all_cut_pairs_map.update(cut_pairs_map)

            # Track end frame
            obj_max = anim_utils.get_action_max_frame(action)
            if obj_max > max_overall_frame:
                max_overall_frame = obj_max

        if processed_count == 0:
            self.report({'WARNING'}, "No animated objects found to process.")
            return {'CANCELLED'}

        # 4. Scale Timeline Markers proportionally and resolve collisions
        if context.scene.timeline_markers and use_cutscene:
            anim_utils.scale_timeline_markers(context.scene, scale_factor, all_cut_pairs_map)

        # Adjust scene end frame
        context.scene.frame_end = max(context.scene.frame_end, int(max_overall_frame + 1))

        # Auto-adapt for next action: scene is now target_fps, set target to old original
        props["auto_detect_fps"] = True
        props["target_fps"] = original_fps

        marker_msg = f" and {len(context.scene.timeline_markers)} marker(s)" if context.scene.timeline_markers else ""
        self.report({'INFO'}, f"Adjusted {processed_count} action(s){marker_msg} to {target_fps} FPS (End Frame: {context.scene.frame_end}).")
        return {'FINISHED'}


class CBW1_OT_SwapFPS(bpy.types.Operator):
    """Swap Original and Target FPS"""
    bl_idname = "cbw1.swap_fps"
    bl_label = "Swap FPS"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cbw1_props
        orig = props.original_fps
        targ = props.target_fps
        props.original_fps = targ
        props.target_fps = orig
        self.report({'INFO'}, f"Swapped FPS: From {props.original_fps} → To {props.target_fps}")
        return {'FINISHED'}


class CBW1_OT_AutoSyncFPS(bpy.types.Operator):
    """Reset and automatically sync Original FPS from the current Scene FPS"""
    bl_idname = "cbw1.auto_sync_fps"
    bl_label = "Auto Sync Scene FPS"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cbw1_props
        props["auto_detect_fps"] = True
        props["target_fps"] = 0
        scene_fps = int(round(context.scene.render.fps / context.scene.render.fps_base))
        self.report({'INFO'}, f"Auto-synced from Scene: {scene_fps} FPS (Target: {props.target_fps} FPS)")
        return {'FINISHED'}


class CBW1_OT_SetFPSPreset(bpy.types.Operator):
    """Set predefined FPS conversion settings"""
    bl_idname = "cbw1.set_fps_preset"
    bl_label = "Set FPS Preset"

    preset_type: StringProperty(
        name="Preset Type",
        description="Conversion preset (e.g. '15_to_60', '30_to_60', '24_to_60')"
    )

    def execute(self, context):
        props = context.scene.cbw1_props

        if self.preset_type == "15_to_60":
            props.original_fps = 15
            props.target_fps = 60
            self.report({'INFO'}, "Applied preset: 15 FPS -> 60 FPS")

        elif self.preset_type == "30_to_60":
            props.original_fps = 30
            props.target_fps = 60
            self.report({'INFO'}, "Applied preset: 30 FPS -> 60 FPS")

        elif self.preset_type == "24_to_60":
            props.original_fps = 24
            props.target_fps = 60
            self.report({'INFO'}, "Applied preset: 24 FPS -> 60 FPS")

        elif self.preset_type == "60_to_30":
            props.original_fps = 60
            props.target_fps = 30
            self.report({'INFO'}, "Applied reverse preset: 60 FPS -> 30 FPS")

        elif self.preset_type == "30_to_15":
            props.original_fps = 30
            props.target_fps = 15
            self.report({'INFO'}, "Applied reverse preset: 30 FPS -> 15 FPS")

        elif self.preset_type == "60_to_24":
            props.original_fps = 60
            props.target_fps = 24
            self.report({'INFO'}, "Applied reverse preset: 60 FPS -> 24 FPS")

        elif self.preset_type == "60_to_15":
            props.original_fps = 60
            props.target_fps = 15
            self.report({'INFO'}, "Applied reverse preset: 60 FPS -> 15 FPS")

        else:
            self.report({'WARNING'}, f"Unknown preset type: {self.preset_type}")
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    CBW1_OT_AdjustFPS,
    CBW1_OT_SwapFPS,
    CBW1_OT_AutoSyncFPS,
    CBW1_OT_SetFPSPreset,
)
