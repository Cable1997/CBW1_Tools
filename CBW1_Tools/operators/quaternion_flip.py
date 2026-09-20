"""
quaternion_flip.py - Operator to fix quaternion sign flips (antipodal jumps) on animated bones.
Author: Nampukkk
Target: Blender 4.2+ (including Blender 4.5+ Slotted Actions)
"""

import bpy
import mathutils
from ..utils import anim_utils


class CBW1_OT_FixQuaternionFlips(bpy.types.Operator):
    """Automatically fix quaternion sign flips/jumps on selected pose bones across all animated keyframes"""
    bl_idname = "cbw1.fix_quaternion_flips"
    bl_label = "Auto Anim FlipQuaternion"
    bl_description = "Fix quaternion sign flips on selected bones across all keyframes in the active Action"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'ARMATURE'
            and context.active_object.mode == 'POSE'
            and bool(context.selected_pose_bones)
        )

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        if obj is None or obj.type != 'ARMATURE' or obj.mode != 'POSE':
            self.report({'ERROR'}, "Please select an Armature and enter Pose Mode.")
            return {'CANCELLED'}

        selected_bones = context.selected_pose_bones
        if not selected_bones:
            self.report({'ERROR'}, "Please select at least one Pose Bone.")
            return {'CANCELLED'}

        if not obj.animation_data or not obj.animation_data.action:
            self.report({'ERROR'}, "Active Armature has no Action.")
            return {'CANCELLED'}

        action = obj.animation_data.action
        original_frame = scene.frame_current

        # Get all action FCurves (compatible with both 4.5 slotted actions and 4.2 legacy actions)
        all_fcurves = anim_utils.get_all_action_fcurves(action)

        bone_data = {}
        all_frames = set()

        for bone in selected_bones:
            if bone.rotation_mode != 'QUATERNION':
                continue

            target_path = f'pose.bones["{bone.name}"].rotation_quaternion'
            fcurves = [fc for fc in all_fcurves if fc.data_path == target_path]

            if len(fcurves) != 4:
                continue

            frames = sorted({
                kp.co.x
                for fc in fcurves
                for kp in fc.keyframe_points
            })

            if len(frames) < 2:
                continue

            bone_data[bone.name] = {
                "bone": bone,
                "frames": frames,
                "frame_set": set(frames),
                "prev_quat": None,
            }

            all_frames.update(frames)

        if not bone_data:
            self.report({'WARNING'}, "No animated Quaternion keyframes found on selected bones.")
            return {'CANCELLED'}

        # Process frames in chronological order
        all_frames = sorted(all_frames)
        flips_fixed = 0

        try:
            for frame in all_frames:
                scene.frame_set(int(frame))

                for data in bone_data.values():
                    if frame not in data["frame_set"]:
                        continue

                    bone = data["bone"]
                    q = bone.rotation_quaternion.copy()

                    if data["prev_quat"] is not None:
                        # If dot product is negative, the quaternion has flipped sign to the opposite hemisphere
                        if data["prev_quat"].dot(q) < 0:
                            bone.rotation_quaternion = -q
                            bone.keyframe_insert(
                                data_path="rotation_quaternion",
                                frame=frame
                            )
                            q = bone.rotation_quaternion.copy()
                            flips_fixed += 1

                    data["prev_quat"] = q

        finally:
            scene.frame_set(original_frame)

        msg = f"Quat Flip Complete: Fixed {flips_fixed} flip(s) on {len(bone_data)} bone(s) across {len(all_frames)} frame(s)."
        print(f"[CBW1_Tool] {msg}")
        self.report({'INFO'}, msg)
        return {'FINISHED'}


classes = (
    CBW1_OT_FixQuaternionFlips,
)
