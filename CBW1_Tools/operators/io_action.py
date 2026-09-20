"""
io_action.py - Animation Action Import and Export operators for CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+ (Blender 4.5+ Slotted Action, Binary & Raw formats)
"""

import os
import bpy
from bpy.props import StringProperty, EnumProperty, CollectionProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from ..utils import anim_utils


class CBW1_OT_ExportAction(bpy.types.Operator, ExportHelper):
    """Export Action's keyframe data (Rig, Model, KeyShape, Props) to a .cbw1anim file"""
    bl_idname = "cbw1.export_action"
    bl_label = "Export CBW1 Action"
    filename_ext = ".cbw1anim"

    filter_glob: StringProperty(
        default="*.cbw1anim;*.bdcbanim;*.json;*.cbw1bin",
        options={'HIDDEN'},
        maxlen=255,
    )

    export_type: EnumProperty(
        name="Format",
        description="Choose export format: Raw (readable JSON) or Binary (compressed, small size)",
        items=[
            ('BINARY', "Binary (Compact)", "High-compression binary format (.cbw1anim) to reduce file size"),
            ('RAW', "Raw (JSON)", "Human-readable JSON text format (.cbw1anim)"),
        ],
        default='BINARY'
    )

    def invoke(self, context, event):
        # Sync with scene export format setting
        if hasattr(context.scene, "cbw1_props"):
            self.export_type = context.scene.cbw1_props.export_format

        self.filename_ext = ".cbw1anim"
        return super().invoke(context, event)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_type", text="Format")

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "Please select an animated object (Armature, Mesh, etc.).")
            return {'CANCELLED'}

        primary_action = None
        related_objs = []

        if obj.animation_data and obj.animation_data.action:
            primary_action = obj.animation_data.action

        if obj.type == 'ARMATURE':
            for child in obj.children:
                if child.type == 'MESH':
                    related_objs.append(child)
            for sel in context.selected_objects:
                if sel.type == 'MESH' and sel not in related_objs:
                    related_objs.append(sel)

        elif obj.type == 'MESH':
            if obj.data and hasattr(obj.data, "shape_keys") and obj.data.shape_keys:
                sk_anim = obj.data.shape_keys.animation_data
                if sk_anim and sk_anim.action:
                    primary_action = sk_anim.action

        if not primary_action:
            for r_obj in related_objs:
                if r_obj.data and hasattr(r_obj.data, "shape_keys") and r_obj.data.shape_keys:
                    sk_anim = r_obj.data.shape_keys.animation_data
                    if sk_anim and sk_anim.action:
                        primary_action = sk_anim.action
                        break

        if not primary_action:
            self.report({'ERROR'}, f"Selected '{obj.name}' has no active Action to export.")
            return {'CANCELLED'}

        # Ensure .cbw1anim extension if none or unrecognized provided
        filepath = self.filepath
        if not filepath.endswith(('.cbw1anim', '.cbw1bin', '.json', '.bdcbanim')):
            filepath += ".cbw1anim"

        try:
            animation_data = anim_utils.serialize_action(primary_action, related_objects=related_objs)

            bytes_written, format_used = anim_utils.save_animation_file(
                filepath, animation_data, format_type=self.export_type
            )

            # Format file size nicely
            if bytes_written < 1024:
                size_str = f"{bytes_written} B"
            elif bytes_written < 1024 * 1024:
                size_str = f"{bytes_written / 1024:.1f} KB"
            else:
                size_str = f"{bytes_written / (1024 * 1024):.2f} MB"

            slots_count = len(animation_data.get("slots", []))
            bone_count = len(animation_data.get("bones", {}))
            sk_count = len(animation_data.get("shape_keys", {}))

            msg = f"Exported '{primary_action.name}' [{format_used}] ({size_str}, {slots_count} slots: {bone_count} bones, {sk_count} shape keys)"
            self.report({'INFO'}, msg)
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to export action: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class CBW1_OT_ImportAction(bpy.types.Operator, ImportHelper):
    """Import Action(s) (.cbw1anim, supporting multi-file selection and smart auto-match)"""
    bl_idname = "cbw1.import_action"
    bl_label = "Import CBW1 Action"
    filename_ext = ".cbw1anim"

    filter_glob: StringProperty(
        default="*.cbw1anim;*.bdcbanim;*.json;*.cbw1bin",
        options={'HIDDEN'},
        maxlen=255,
    )

    directory: StringProperty(
        name="Directory",
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    files: CollectionProperty(
        name="Files",
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    def execute(self, context):
        filepaths = []
        if self.files and self.directory:
            for f in self.files:
                if f.name:
                    filepaths.append(os.path.join(self.directory, f.name))
        if not filepaths and self.filepath:
            filepaths.append(self.filepath)

        if not filepaths:
            self.report({'ERROR'}, "No file selected.")
            return {'CANCELLED'}

        success_count = 0
        summary_messages = []

        for fpath in filepaths:
            if not os.path.isfile(fpath):
                continue

            try:
                animation_data, detected_format = anim_utils.load_animation_file(fpath)
            except Exception as e:
                self.report({'WARNING'}, f"Could not load {os.path.basename(fpath)}: {e}")
                continue

            if not animation_data:
                continue

            res = anim_utils.deserialize_action(
                target_obj_or_data=context.active_object,
                data_or_target=animation_data,
                context=context
            )
            new_action, warnings = res
            for warning in warnings:
                self.report({'WARNING'}, warning)

            success_count += 1
            desc = res.match_info.get("description", "")
            summary_messages.append((new_action.name, res.match_mode, desc))

        if success_count == 0:
            self.report({'ERROR'}, "No animations were successfully imported.")
            return {'CANCELLED'}

        if success_count == 1:
            act_name, mode, desc = summary_messages[0]
            self.report({'INFO'}, f"Imported '{act_name}' [{mode}]: {desc}")
        else:
            self.report({'INFO'}, f"Successfully imported {success_count} animation file(s).")

        return {'FINISHED'}


classes = (
    CBW1_OT_ExportAction,
    CBW1_OT_ImportAction,
)
