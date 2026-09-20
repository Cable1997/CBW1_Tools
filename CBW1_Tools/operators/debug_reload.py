"""
debug_reload.py - In-UI Hot Reload Operator for CBW1_Tool.
Author: Nampukkk
Target: Blender 4.2+
"""

import sys
import importlib
import bpy


class CBW1_OT_ReloadAddon(bpy.types.Operator):
    """Hot-reload all CBW1_Tool modules and refresh registration without restarting Blender"""
    bl_idname = "cbw1.reload_addon"
    bl_label = "Reload CBW1_Tool"
    bl_description = "Reload all CBW1_Tool Python modules and refresh UI"

    def execute(self, context):
        package_name = "CBW1_Tool"

        self.report({'INFO'}, f"Reloading {package_name}...")
        print(f"[CBW1_Tool DEBUG] Hot reload initiated from UI...")

        try:
            # 1. Unregister FIRST using old registered classes
            if package_name in sys.modules:
                mod = sys.modules[package_name]
                if hasattr(mod, "unregister"):
                    try:
                        mod.unregister()
                        print("[CBW1_Tool DEBUG] Unregistered old version.")
                    except Exception as unreg_err:
                        print(f"[CBW1_Tool DEBUG] Note on unregister: {unreg_err}")

            # 2. Reload submodules
            submodule_names = [
                "utils.anim_utils",
                "utils",
                "properties",
                "operators.io_action",
                "operators.fps_adjust",
                "operators.close_frames",
                "operators.quaternion_flip",
                "operators.debug_reload",
                "operators",
                "ui.panels",
                "ui",
            ]

            for sub in submodule_names:
                full_mod_name = f"{package_name}.{sub}"
                if full_mod_name in sys.modules:
                    try:
                        importlib.reload(sys.modules[full_mod_name])
                        print(f"[CBW1_Tool DEBUG] Reloaded: {sub}")
                    except Exception as e:
                        print(f"[CBW1_Tool DEBUG] Warning reloading {sub}: {e}")

            # 3. Reload main package
            if package_name in sys.modules:
                mod = importlib.reload(sys.modules[package_name])
            else:
                mod = importlib.import_module(package_name)

            # 4. Re-register new version
            if hasattr(mod, "register"):
                mod.register()
                print("[CBW1_Tool DEBUG] Re-registered new version.")

            # 5. Force redraw of 3D Viewport areas
            for window in bpy.context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()

            self.report({'INFO'}, "CBW1_Tool reloaded successfully!")
            return {'FINISHED'}

        except Exception as e:
            err_msg = f"Reload failed: {e}"
            print(f"[CBW1_Tool ERROR] {err_msg}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, err_msg)
            return {'CANCELLED'}


classes = (
    CBW1_OT_ReloadAddon,
)
