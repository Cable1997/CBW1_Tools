"""
anim_utils.py - Core animation processing utilities for CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+ (Full Blender 4.5+ Slotted & Layered Action standard, Binary & Raw IO)
"""

import json
import zlib
from typing import List, Tuple, Dict, Any, Optional, Set
import bpy

# 8-byte magic header for CBW1 binary animation files
MAGIC_BINARY_HEADER = b"CBW1_BIN\x01"

VALID_SLOT_ID_TYPES = {
    'ACTION', 'ARMATURE', 'BRUSH', 'CACHEFILE', 'CAMERA', 'COLLECTION', 'CURVE',
    'CURVES', 'FONT', 'GREASEPENCIL', 'IMAGE', 'KEY', 'LATTICE', 'LIBRARY',
    'LIGHT', 'LIGHT_PROBE', 'LINESTYLE', 'MASK', 'MATERIAL', 'MESH', 'META',
    'MOVIECLIP', 'NODETREE', 'OBJECT', 'POINTCLOUD', 'SCENE', 'SPEAKER', 'TEXT',
    'TEXTURE', 'VOLUME', 'WORLD'
}


def save_animation_file(filepath: str, data: Dict[str, Any], format_type: str = 'RAW') -> Tuple[int, str]:
    """
    Saves animation data to disk in either RAW (readable JSON) or BINARY (compressed) format.
    Returns (bytes_written, format_used).
    """
    if format_type == 'BINARY':
        # Binary: Magic Header + zlib compressed UTF-8 JSON
        json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')
        compressed_payload = zlib.compress(json_bytes, level=9)
        binary_data = MAGIC_BINARY_HEADER + compressed_payload

        with open(filepath, 'wb') as f:
            f.write(binary_data)

        return len(binary_data), 'BINARY'

    else:
        # Raw: Human-readable formatted JSON text
        raw_text = json.dumps(data, indent=4)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(raw_text)

        return len(raw_text.encode('utf-8')), 'RAW'


def load_animation_file(filepath: str) -> Tuple[Dict[str, Any], str]:
    """
    Loads animation data from disk.
    Automatically detects whether the file is BINARY (compressed) or RAW (JSON).
    Returns (data_dict, detected_format).
    """
    with open(filepath, 'rb') as f:
        content = f.read()

    # Check for binary magic signature
    if content.startswith(MAGIC_BINARY_HEADER):
        compressed_payload = content[len(MAGIC_BINARY_HEADER):]
        decompressed_json = zlib.decompress(compressed_payload).decode('utf-8')
        data = json.loads(decompressed_json)
        return data, 'BINARY'

    else:
        # Parse as raw text JSON
        text = content.decode('utf-8')
        data = json.loads(text)
        return data, 'RAW'


def get_all_action_fcurves(action: bpy.types.Action) -> List[bpy.types.FCurve]:
    """
    Returns all FCurves in the Action.
    In Blender 4.5+ (slotted actions), iterates through layers, strips, and channelbags across all slots.
    In Blender 4.2 - 4.4 (legacy actions), falls back to action.fcurves.
    """
    fcurves_list: List[bpy.types.FCurve] = []

    if hasattr(action, "layers") and action.layers:
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, "channelbags"):
                    for cb in strip.channelbags:
                        fcurves_list.extend(cb.fcurves)

    if not fcurves_list and hasattr(action, "fcurves"):
        fcurves_list.extend(action.fcurves)

    return fcurves_list


def serialize_fcurve(fc: bpy.types.FCurve) -> Dict[str, Any]:
    """Serializes an individual FCurve with full keyframe handles, interpolation, and extrapolation."""
    kps_data = []
    for kp in fc.keyframe_points:
        kp_dict = {
            "frame": kp.co.x,
            "value": kp.co.y,
            "handle_left": [kp.handle_left.x, kp.handle_left.y],
            "handle_right": [kp.handle_right.x, kp.handle_right.y],
            "handle_left_type": getattr(kp, "handle_left_type", "ALIGNED"),
            "handle_right_type": getattr(kp, "handle_right_type", "ALIGNED"),
            "interpolation": getattr(kp, "interpolation", "BEZIER"),
            "easing": getattr(kp, "easing", "AUTO"),
        }
        kps_data.append(kp_dict)

    return {
        "data_path": fc.data_path,
        "array_index": fc.array_index,
        "extrapolation": getattr(fc, "extrapolation", "CONSTANT"),
        "keyframe_points": kps_data
    }


def populate_legacy_dictionaries(
    fcurves: List[bpy.types.FCurve],
    animation_data: Dict[str, Any]
) -> None:
    """Populates legacy fields ('bones', 'shape_keys', 'object_custom_properties') for backward compatibility."""
    for fc in fcurves:
        dpath = fc.data_path
        arr_idx = fc.array_index
        keyframes = [{"frame": kp.co.x, "value": kp.co.y} for kp in fc.keyframe_points]

        # Shape Key (e.g. key_blocks["Blink"].value)
        if dpath.startswith('key_blocks["') and '"].value' in dpath:
            sk_start = dpath.find('["') + 2
            sk_end = dpath.find('"]', sk_start)
            sk_name = dpath[sk_start:sk_end]
            if "shape_keys" not in animation_data:
                animation_data["shape_keys"] = {}
            animation_data["shape_keys"][sk_name] = keyframes

        # Bone transform property (e.g. pose.bones["BoneName"].location)
        elif dpath.startswith('pose.bones["') and '"].' in dpath:
            bone_name_start = dpath.find('["') + 2
            bone_name_end = dpath.find('"]', bone_name_start)
            bone_name = dpath[bone_name_start:bone_name_end]
            channel_path = dpath[bone_name_end + 3:]

            if bone_name not in animation_data["bones"]:
                animation_data["bones"][bone_name] = {"properties": {}, "custom_properties": {}}

            bone_props = animation_data["bones"][bone_name]["properties"]
            if channel_path not in bone_props:
                bone_props[channel_path] = {}
            bone_props[channel_path][f"channel_{arr_idx}"] = keyframes

        # Bone custom property (e.g. pose.bones["BoneName"]["CustomProp"])
        elif dpath.startswith('pose.bones["') and dpath.endswith('"]'):
            parts = dpath.split('"]["')
            if len(parts) == 2:
                bone_name = parts[0].replace('pose.bones["', '')
                prop_name = parts[1].replace('"]', '')
                if bone_name not in animation_data["bones"]:
                    animation_data["bones"][bone_name] = {"properties": {}, "custom_properties": {}}
                bone_custom = animation_data["bones"][bone_name]["custom_properties"]
                if prop_name not in bone_custom:
                    bone_custom[prop_name] = {}
                bone_custom[prop_name][f"channel_{arr_idx}"] = keyframes

        # Object custom property (e.g. ["ObjectProp"])
        elif dpath.startswith('["') and dpath.endswith('"]'):
            prop_name_start = dpath.find('["') + 2
            prop_name_end = dpath.find('"]', prop_name_start)
            prop_name = dpath[prop_name_start:prop_name_end]
            if prop_name not in animation_data["object_custom_properties"]:
                animation_data["object_custom_properties"][prop_name] = {}
            animation_data["object_custom_properties"][prop_name][f"channel_{arr_idx}"] = keyframes


def serialize_action(
    action: bpy.types.Action,
    related_objects: Optional[List[bpy.types.Object]] = None
) -> Dict[str, Any]:
    """
    Serializes a complete Action into a structured JSON-compatible dictionary.
    Preserves all internal Layers, Slots (Rig, Model, KeyShape, Props), Channelbags, and FCurves (Blender 4.5+ standard).
    Also includes backward-compatible structures ('bones', 'shape_keys', etc.).
    """
    animation_data: Dict[str, Any] = {
        "format_version": "2.0",
        "standard": "Blender 4.5 Slotted Action",
        "action_name": action.name,
        "slots": [],
        "bones": {},
        "object_custom_properties": {},
        "shape_keys": {}
    }

    all_exported_fcurves: List[bpy.types.FCurve] = []

    # 1. Blender 4.5 Slotted Action structure
    if hasattr(action, "slots") and len(action.slots) > 0 and hasattr(action, "layers") and action.layers:
        layer = action.layers[0]
        strip = layer.strips[0] if layer.strips else None

        for slot in action.slots:
            cb = strip.channelbag(slot) if strip else None
            slot_fcurves = cb.fcurves if cb else []

            s_id_type = slot.target_id_type
            if s_id_type not in VALID_SLOT_ID_TYPES:
                # Infer from curves if UNSPECIFIED
                has_key = any('key_blocks["' in fc.data_path for fc in slot_fcurves)
                s_id_type = 'KEY' if has_key else 'OBJECT'

            slot_data = {
                "name": slot.name_display,
                "id_type": s_id_type,
                "identifier": slot.identifier,
                "fcurves": []
            }

            for fc in slot_fcurves:
                slot_data["fcurves"].append(serialize_fcurve(fc))
                all_exported_fcurves.append(fc)

            animation_data["slots"].append(slot_data)

    else:
        # Single-slot or legacy action structure
        fcurves = get_all_action_fcurves(action)
        if fcurves:
            slot_data = {
                "name": action.name,
                "id_type": "OBJECT",
                "identifier": "DefaultSlot",
                "fcurves": [serialize_fcurve(fc) for fc in fcurves]
            }
            animation_data["slots"].append(slot_data)
            all_exported_fcurves.extend(fcurves)

    # 2. Check if related objects (e.g. child meshes of Armature) have separate shape key actions to integrate
    if related_objects:
        existing_slot_names = {s["name"] for s in animation_data["slots"]}
        for r_obj in related_objects:
            if r_obj.type == 'MESH' and r_obj.data and hasattr(r_obj.data, "shape_keys") and r_obj.data.shape_keys:
                sk_anim = r_obj.data.shape_keys.animation_data
                if sk_anim and sk_anim.action and sk_anim.action != action:
                    sk_fcurves = get_all_action_fcurves(sk_anim.action)
                    if sk_fcurves:
                        slot_name = f"{r_obj.name}_ShapeKeys"
                        if slot_name not in existing_slot_names:
                            sk_slot_data = {
                                "name": slot_name,
                                "id_type": "KEY",
                                "identifier": f"KE_{r_obj.name}",
                                "fcurves": [serialize_fcurve(fc) for fc in sk_fcurves]
                            }
                            animation_data["slots"].append(sk_slot_data)
                            all_exported_fcurves.extend(sk_fcurves)
                            existing_slot_names.add(slot_name)

    # 3. Populate legacy mappings for compatibility
    populate_legacy_dictionaries(all_exported_fcurves, animation_data)

    return animation_data


class ActionImportResult(tuple):
    """
    Subclass of tuple (new_action, warnings) for full backward compatibility with:
        action, warnings = anim_utils.deserialize_action(...)
    while also providing extended properties:
        res.match_mode: 'SELECTED_RIG', 'AUTO_MATCHED', or 'ACTION_LIBRARY'
        res.bound_objects: list of object names bound
        res.match_info: complete matching details dict
    """
    def __new__(cls, action, match_info, warnings):
        return super().__new__(cls, (action, warnings))

    def __init__(self, action, match_info, warnings):
        self.action = action
        self.match_info = match_info
        self.match_mode = match_info.get("mode", "ACTION_LIBRARY")
        self.bound_objects = match_info.get("bound_objects", [])
        self.warnings = warnings


def deserialize_action(
    target_obj_or_data: Any = None,
    data_or_target: Any = None,
    context: Optional[bpy.types.Context] = None
) -> ActionImportResult:
    """
    Deserializes animation data and reconstructs the complete Action in Blender 4.5 standard.
    Recreates all internal Slots (Rig, Model, KeyShape), Layers, Channelbags, FCurves, and Handles.

    Implements 3-tier Smart Matching:
    - Priority 1 (Selected/Active Rig): If an Armature is selected/active, the animation is bound
      directly to this Armature (and its child meshes with ShapeKeys), regardless of source names.
    - Priority 2 (Auto-Match by Name): If no Rig is selected, matches scene objects by slot names
      (Armatures, Meshes, ShapeKeys) and binds automatically.
    - Priority 3 (Action Library): If no objects match and no rig is selected, imports cleanly
      into bpy.data.actions with fake user enabled without failing or canceling.
    """
    if isinstance(target_obj_or_data, dict):
        animation_data = target_obj_or_data
        target_obj = data_or_target
    elif isinstance(data_or_target, dict):
        target_obj = target_obj_or_data
        animation_data = data_or_target
    else:
        animation_data = target_obj_or_data if isinstance(target_obj_or_data, dict) else (data_or_target if isinstance(data_or_target, dict) else {})
        target_obj = target_obj_or_data if target_obj_or_data != animation_data else None

    if context is None:
        context = getattr(bpy, "context", None)

    warnings: List[str] = []
    action_name = animation_data.get("action_name", "ImportedAction")
    new_action = bpy.data.actions.new(name=action_name)

    use_45_slots = hasattr(new_action, "slots")
    created_slots: Dict[str, Any] = {}
    slots_by_id_type: Dict[str, List[Any]] = {}

    slots_list = animation_data.get("slots", [])

    # If file has Blender 4.5 'slots' structure
    if use_45_slots and slots_list:
        layer = new_action.layers.new(name='MainLayer')
        strip = layer.strips.new(type='KEYFRAME')

        for slot_info in slots_list:
            s_name = slot_info.get("name", "Slot")
            s_id_type = slot_info.get("id_type", "OBJECT")

            # Guard against UNSPECIFIED or invalid enum values
            if s_id_type not in VALID_SLOT_ID_TYPES:
                fcurves_info = slot_info.get("fcurves", [])
                has_key = any('key_blocks["' in fc.get("data_path", "") for fc in fcurves_info)
                s_id_type = 'KEY' if has_key else 'OBJECT'

            slot = new_action.slots.new(id_type=s_id_type, name=s_name)
            created_slots[s_name] = slot
            created_slots[slot.identifier] = slot

            if s_id_type not in slots_by_id_type:
                slots_by_id_type[s_id_type] = []
            slots_by_id_type[s_id_type].append(slot)

            cb = strip.channelbags.new(slot)

            for fc_info in slot_info.get("fcurves", []):
                dpath = fc_info["data_path"]
                arr_idx = fc_info.get("array_index", 0)

                fc = cb.fcurves.new(data_path=dpath, index=arr_idx)
                fc.extrapolation = fc_info.get("extrapolation", 'CONSTANT')

                for kp_info in fc_info.get("keyframe_points", []):
                    kp = fc.keyframe_points.insert(kp_info["frame"], kp_info["value"])
                    if "handle_left" in kp_info:
                        kp.handle_left = kp_info["handle_left"]
                    if "handle_right" in kp_info:
                        kp.handle_right = kp_info["handle_right"]
                    if "handle_left_type" in kp_info:
                        kp.handle_left_type = kp_info["handle_left_type"]
                    if "handle_right_type" in kp_info:
                        kp.handle_right_type = kp_info["handle_right_type"]
                    if "interpolation" in kp_info:
                        kp.interpolation = kp_info["interpolation"]
                    if "easing" in kp_info:
                        kp.easing = kp_info["easing"]

    else:
        # Legacy fallback reconstruction (build 4.5 slots from legacy 'bones', 'shape_keys', etc.)
        bones_data = animation_data.get("bones", {})
        shape_keys_data = animation_data.get("shape_keys", {})
        obj_custom_props = animation_data.get("object_custom_properties", {})

        target_name = getattr(target_obj, "name", "Armature")

        if use_45_slots:
            layer = new_action.layers.new(name='MainLayer')
            strip = layer.strips.new(type='KEYFRAME')

            slot_arm = None
            slot_key = None
            if bones_data or obj_custom_props or getattr(target_obj, "type", None) == 'ARMATURE':
                slot_arm = new_action.slots.new(id_type='OBJECT', name=target_name)
                created_slots[target_name] = slot_arm
                created_slots["OBJECT"] = slot_arm
                slots_by_id_type["OBJECT"] = [slot_arm]
                cb_arm = strip.channelbags.new(slot_arm)

                for bname, bprops in bones_data.items():
                    for cpath, chs in bprops.get("properties", {}).items():
                        for ch_key, kps in chs.items():
                            a_idx = int(ch_key.split('_')[1])
                            fc = cb_arm.fcurves.new(data_path=f'pose.bones["{bname}"].{cpath}', index=a_idx)
                            for kp in kps:
                                fc.keyframe_points.insert(kp["frame"], kp["value"])

                    for pname, chs in bprops.get("custom_properties", {}).items():
                        for ch_key, kps in chs.items():
                            a_idx = int(ch_key.split('_')[1])
                            fc = cb_arm.fcurves.new(data_path=f'pose.bones["{bname}"]["{pname}"]', index=a_idx)
                            for kp in kps:
                                fc.keyframe_points.insert(kp["frame"], kp["value"])

                for pname, chs in obj_custom_props.items():
                    for ch_key, kps in chs.items():
                        a_idx = int(ch_key.split('_')[1])
                        fc = cb_arm.fcurves.new(data_path=f'["{pname}"]', index=a_idx)
                        for kp in kps:
                            fc.keyframe_points.insert(kp["frame"], kp["value"])

            if shape_keys_data:
                slot_key = new_action.slots.new(id_type='KEY', name="ShapeKeys")
                created_slots["ShapeKeys"] = slot_key
                created_slots["KEY"] = slot_key
                slots_by_id_type["KEY"] = [slot_key]
                cb_key = strip.channelbags.new(slot_key)

                for sk_name, kps in shape_keys_data.items():
                    fc = cb_key.fcurves.new(data_path=f'key_blocks["{sk_name}"].value', index=0)
                    for kp in kps:
                        fc.keyframe_points.insert(kp["frame"], kp["value"])

        else:
            # Fallback for Blender 4.2 / 4.3 legacy single-slot actions
            for bname, bprops in bones_data.items():
                for cpath, chs in bprops.get("properties", {}).items():
                    for ch_key, kps in chs.items():
                        a_idx = int(ch_key.split('_')[1])
                        fc = new_action.fcurves.new(data_path=f'pose.bones["{bname}"].{cpath}', index=a_idx)
                        for kp in kps:
                            fc.keyframe_points.insert(kp["frame"], kp["value"])

    # 4. Smart Matching & Binding System (3 Priorities)
    match_info: Dict[str, Any] = {
        "mode": "ACTION_LIBRARY",
        "bound_objects": [],
        "description": ""
    }

    # Detect if user currently has an Armature selected / active
    selected_rig = None
    if target_obj and getattr(target_obj, "type", None) == 'ARMATURE':
        selected_rig = target_obj
    elif context:
        active = getattr(context, "active_object", None)
        if active and getattr(active, "type", None) == 'ARMATURE':
            selected_rig = active
        else:
            for o in getattr(context, "selected_objects", []):
                if getattr(o, "type", None) == 'ARMATURE':
                    selected_rig = o
                    break

    # -------------------------------------------------------------------------
    # Priority 1: User has an Armature selected / active in Blender
    # Match directly to this Armature regardless of original source names
    # -------------------------------------------------------------------------
    if selected_rig:
        match_info["mode"] = "SELECTED_RIG"
        if not selected_rig.animation_data:
            selected_rig.animation_data_create()
        selected_rig.animation_data.action = new_action
        match_info["bound_objects"].append(selected_rig.name)

        # In Blender 4.5+, find the Rig slot (slot with bone curves or first OBJECT slot)
        rig_slot = None
        if use_45_slots:
            layer = new_action.layers[0] if new_action.layers else None
            strip = layer.strips[0] if layer and layer.strips else None

            # First priority: OBJECT slot that contains bone animation
            for slot in slots_by_id_type.get('OBJECT', []):
                cb = strip.channelbag(slot) if strip else None
                if cb and any(fc.data_path.startswith('pose.bones[') for fc in cb.fcurves):
                    rig_slot = slot
                    break

            # Second priority: Slot named after selected rig
            if not rig_slot:
                rig_slot = created_slots.get(selected_rig.name)

            # Third priority: Any OBJECT slot
            if not rig_slot and slots_by_id_type.get('OBJECT'):
                rig_slot = slots_by_id_type['OBJECT'][0]

            if rig_slot and hasattr(selected_rig.animation_data, "action_slot"):
                selected_rig.animation_data.action_slot = rig_slot

        # Bind Shape Keys to child meshes or selected meshes
        key_slots = slots_by_id_type.get('KEY', [])
        if use_45_slots and key_slots:
            candidate_meshes = [c for c in selected_rig.children if getattr(c, "type", None) == 'MESH']
            if context:
                for o in getattr(context, "selected_objects", []):
                    if getattr(o, "type", None) == 'MESH' and o not in candidate_meshes:
                        candidate_meshes.append(o)

            used_meshes = set()
            for key_slot in key_slots:
                matched_mesh = None
                # Check candidate meshes by name
                for cm in candidate_meshes:
                    if cm in used_meshes:
                        continue
                    if cm.name == key_slot.name_display or key_slot.name_display.startswith(cm.name):
                        matched_mesh = cm
                        break

                # If not matched by name, pick candidate mesh with shape keys
                if not matched_mesh:
                    for cm in candidate_meshes:
                        if cm not in used_meshes and cm.data and getattr(cm.data, "shape_keys", None):
                            matched_mesh = cm
                            break

                if matched_mesh and matched_mesh.data and getattr(matched_mesh.data, "shape_keys", None):
                    sk_data = matched_mesh.data.shape_keys
                    if not sk_data.animation_data:
                        sk_data.animation_data_create()
                    sk_data.animation_data.action = new_action
                    if hasattr(sk_data.animation_data, "action_slot"):
                        sk_data.animation_data.action_slot = key_slot
                    used_meshes.add(matched_mesh)
                    match_info["bound_objects"].append(f"{matched_mesh.name} (ShapeKeys)")

        match_info["description"] = f"Bound to selected Rig '{selected_rig.name}'"
        if len(match_info["bound_objects"]) > 1:
            match_info["description"] += f" and {len(match_info['bound_objects'])-1} related component(s)"

    # -------------------------------------------------------------------------
    # Priority 2: No Rig selected -> Auto-match by name with scene objects
    # Scan scene objects matching slot names (Rig, Model, ShapeKey)
    # -------------------------------------------------------------------------
    else:
        scene_objects = bpy.data.objects

        # 1. Match OBJECT slots
        for slot in slots_by_id_type.get('OBJECT', []):
            target_scene_obj = scene_objects.get(slot.name_display)
            if target_scene_obj:
                if not target_scene_obj.animation_data:
                    target_scene_obj.animation_data_create()
                target_scene_obj.animation_data.action = new_action
                if use_45_slots and hasattr(target_scene_obj.animation_data, "action_slot"):
                    target_scene_obj.animation_data.action_slot = slot
                match_info["bound_objects"].append(target_scene_obj.name)

        # 2. Match KEY slots
        for key_slot in slots_by_id_type.get('KEY', []):
            matched_mesh = None
            s_name = key_slot.name_display

            # Check direct name match
            cand = scene_objects.get(s_name)
            if cand and cand.type == 'MESH' and cand.data and getattr(cand.data, "shape_keys", None):
                matched_mesh = cand

            # Check suffix stripping (e.g. "Body_ShapeKeys" -> "Body")
            if not matched_mesh:
                for suffix in ("_ShapeKeys", "_KeyShape", "_SK", "_sk", "_keys"):
                    if s_name.endswith(suffix):
                        base = s_name[:-len(suffix)]
                        cand = scene_objects.get(base)
                        if cand and cand.type == 'MESH' and cand.data and getattr(cand.data, "shape_keys", None):
                            matched_mesh = cand
                            break

            # Check by curve key_block names
            if not matched_mesh and use_45_slots:
                layer = new_action.layers[0] if new_action.layers else None
                strip = layer.strips[0] if layer and layer.strips else None
                cb = strip.channelbag(key_slot) if strip else None
                slot_kb_names = set()
                if cb:
                    for fc in cb.fcurves:
                        if 'key_blocks["' in fc.data_path:
                            kb = fc.data_path.split('key_blocks["')[1].split('"]')[0]
                            slot_kb_names.add(kb)
                if slot_kb_names:
                    for obj in scene_objects:
                        if obj.type == 'MESH' and obj.data and getattr(obj.data, "shape_keys", None):
                            existing_kbs = {kb.name for kb in obj.data.shape_keys.key_blocks}
                            if slot_kb_names.issubset(existing_kbs) or slot_kb_names.intersection(existing_kbs):
                                matched_mesh = obj
                                break

            if matched_mesh and matched_mesh.data and getattr(matched_mesh.data, "shape_keys", None):
                sk_data = matched_mesh.data.shape_keys
                if not sk_data.animation_data:
                    sk_data.animation_data_create()
                sk_data.animation_data.action = new_action
                if use_45_slots and hasattr(sk_data.animation_data, "action_slot"):
                    sk_data.animation_data.action_slot = key_slot
                match_info["bound_objects"].append(f"{matched_mesh.name} (ShapeKeys)")

        if match_info["bound_objects"]:
            match_info["mode"] = "AUTO_MATCHED"
            match_info["description"] = f"Auto-matched to: {', '.join(match_info['bound_objects'])}"

    # -------------------------------------------------------------------------
    # Priority 3: No Rig selected AND No scene objects matched by name
    # Import cleanly as Action library file (bpy.data.actions)
    # -------------------------------------------------------------------------
    if not match_info["bound_objects"]:
        match_info["mode"] = "ACTION_LIBRARY"
        new_action.use_fake_user = True
        match_info["description"] = f"Imported '{new_action.name}' to Action Library (no matching scene objects)"

    return ActionImportResult(new_action, match_info, warnings)


def detect_close_keyframe_pairs(action: bpy.types.Action) -> List[Tuple[int, int]]:
    """
    Scans the action for keyframe pairs that are adjacent (1 frame apart)
    across all slots and channels.
    """
    all_frames = []
    fcurves = get_all_action_fcurves(action)
    for fcurve in fcurves:
        for kp in fcurve.keyframe_points:
            all_frames.append(round(kp.co.x))

    sorted_frames = sorted(list(set(all_frames)))
    pairs = []
    for i in range(len(sorted_frames) - 1):
        curr_frame = sorted_frames[i]
        next_frame = sorted_frames[i + 1]
        if next_frame == curr_frame + 1:
            pairs.append((curr_frame, next_frame))

    return pairs


def scale_action_keyframes(action: bpy.types.Action, scale_factor: float) -> None:
    """
    Scales all keyframe positions and handles in the Action across all slots/channelbags by scale factor.
    """
    fcurves = get_all_action_fcurves(action)
    for fcurve in fcurves:
        for kp in fcurve.keyframe_points:
            kp.co.x *= scale_factor
            if kp.handle_left_type != 'FREE':
                kp.handle_left.x *= scale_factor
            if kp.handle_right_type != 'FREE':
                kp.handle_right.x *= scale_factor
        fcurve.update()


def find_keyframe_points_for_pairs(
    action: bpy.types.Action,
    pairs: List[Tuple[int, int]],
    scale_factor: float
) -> Dict[Tuple[int, int], Dict[str, List[Any]]]:
    """
    Locates actual keyframe points in an already-scaled action matching the original frame pairs.
    """
    close_pairs_data = {}
    fcurves = get_all_action_fcurves(action)

    for old_head, old_tail in pairs:
        head_kps = []
        tail_kps = []

        for fcurve in fcurves:
            for kp in fcurve.keyframe_points:
                orig_frame = round(kp.co.x / scale_factor)
                if orig_frame == old_head:
                    head_kps.append(kp)
                elif orig_frame == old_tail:
                    tail_kps.append(kp)

        if head_kps and tail_kps:
            close_pairs_data[(old_head, old_tail)] = {
                'head_kps': head_kps,
                'tail_kps': tail_kps
            }

    return close_pairs_data


def find_cut_pairs_from_markers(
    action: bpy.types.Action,
    marker_frames: List[int]
) -> List[Tuple[int, int]]:
    """
    Identifies cut transition keyframe pairs in the action corresponding to timeline markers.
    For each marker frame M, searches for adjacent keyframes (M, M+1), (M-1, M), or nearby cuts.
    """
    action_frames = set()
    fcurves = get_all_action_fcurves(action)
    for fc in fcurves:
        for kp in fc.keyframe_points:
            action_frames.add(round(kp.co.x))

    pairs = []
    for m_frame in sorted(marker_frames):
        if (m_frame in action_frames) and ((m_frame + 1) in action_frames):
            pairs.append((m_frame, m_frame + 1))
        elif ((m_frame - 1) in action_frames) and (m_frame in action_frames):
            pairs.append((m_frame - 1, m_frame))
        elif ((m_frame - 1) in action_frames) and ((m_frame + 1) in action_frames):
            pairs.append((m_frame - 1, m_frame + 1))
        else:
            # Look within +/- 2 frames for any adjacent keyframe pair
            found = False
            for offset in (-1, 1, -2, 2):
                cand = m_frame + offset
                if (cand in action_frames) and ((cand + 1) in action_frames):
                    pairs.append((cand, cand + 1))
                    found = True
                    break
            if not found:
                pairs.append((m_frame, m_frame + 1))

    # Deduplicate while preserving order
    unique_pairs = []
    for p in pairs:
        if p not in unique_pairs:
            unique_pairs.append(p)

    return unique_pairs


def scale_timeline_markers(
    scene: bpy.types.Scene,
    scale_factor: float,
    cut_pairs_map: Optional[Dict[int, int]] = None
) -> None:
    """
    Scales timeline markers by scale_factor while preserving relative ordering,
    proportions, and preventing any marker collisions/overlaps.
    cut_pairs_map: optional dict mapping original cut frame -> new scaled cut frame.
    """
    markers = list(scene.timeline_markers)
    if not markers:
        return

    # Sort markers by original frame position and name
    markers.sort(key=lambda m: (m.frame, m.name))

    scaled_positions = []
    for m in markers:
        old_f = m.frame
        if cut_pairs_map and old_f in cut_pairs_map:
            target_f = cut_pairs_map[old_f]
        else:
            target_f = round(old_f * scale_factor)
        scaled_positions.append(target_f)

    # Collision prevention (guarantee markers stay strictly ordered without overlapping)
    for i in range(1, len(markers)):
        if markers[i].frame > markers[i-1].frame:
            if scaled_positions[i] <= scaled_positions[i-1]:
                scaled_positions[i] = scaled_positions[i-1] + 1

    for m, new_f in zip(markers, scaled_positions):
        m.frame = int(new_f)


def apply_offsets_to_close_pairs(
    action: bpy.types.Action,
    close_pairs_data: Dict[Tuple[int, int], Dict[str, List[Any]]],
    scale_factor: float,
    head_offset: int = 0,
    tail_offset: int = 0,
    auto_snap_adjacent: bool = True
) -> Dict[int, int]:
    """
    Applies offsets to identified close keyframe pairs in the action.
    When auto_snap_adjacent is True (default for CutScene Camera Close Frames):
    Automatically ensures adjacent cut frames (old_tail == old_head + 1) remain
    exactly 1 frame apart in the scaled animation (new_tail = new_head + 1),
    completely eliminating cut gaps without needing manual offset tweaking.
    """
    cut_pairs_map = {}
    for (old_head, old_tail), kf_data in close_pairs_data.items():
        if auto_snap_adjacent and old_tail == old_head + 1:
            new_head = round(old_head * scale_factor)
            new_tail = new_head + 1
        else:
            scaled_head = old_head * scale_factor
            scaled_tail = old_tail * scale_factor
            new_head = round(scaled_head + head_offset)
            new_tail = round(scaled_tail + tail_offset)

        cut_pairs_map[old_head] = int(new_head)
        cut_pairs_map[old_tail] = int(new_tail)

        for kp in kf_data['head_kps']:
            diff = new_head - kp.co.x
            kp.co.x = new_head
            kp.handle_left.x += diff
            kp.handle_right.x += diff

        for kp in kf_data['tail_kps']:
            diff = new_tail - kp.co.x
            kp.co.x = new_tail
            kp.handle_left.x += diff
            kp.handle_right.x += diff

    fcurves = get_all_action_fcurves(action)
    for fc in fcurves:
        fc.update()

    return cut_pairs_map


def get_action_max_frame(action: bpy.types.Action) -> float:
    """Returns the maximum keyframe time (in frames) across all channels in the action."""
    max_frame = 0.0
    fcurves = get_all_action_fcurves(action)
    for fcurve in fcurves:
        for kp in fcurve.keyframe_points:
            if kp.co.x > max_frame:
                max_frame = kp.co.x
    return max_frame
