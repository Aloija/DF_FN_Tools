# export.py
import bpy # type: ignore
import os

from .mesh_object_classes import *
from .ui import *
from .utils import *

# Clean Join operator: duplicate selection, apply mods, join
class OBJECT_OT_duplicate_clean_join(bpy.types.Operator):
    bl_idname = "object.duplicate_clean_join"
    bl_label = "Clean Join"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

        bpy.ops.object.duplicate(linked=False)
        dup_objects = list(context.selected_objects)

        for obj in dup_objects:
            context.view_layer.objects.active = obj
            try:
                bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
            except Exception:
                pass

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)

            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass

            for mod in list(obj.modifiers):
                if mod.show_viewport:
                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    except Exception:
                        # Ignore modifiers that fail to apply
                        continue

        bpy.ops.object.select_all(action='DESELECT')
        for obj in dup_objects:
            obj.select_set(True)
        context.view_layer.objects.active = dup_objects[0]
        bpy.ops.object.join()

        joined_obj = context.active_object

        export_coll = bpy.data.collections.get("Export")
        if export_coll and joined_obj:
            if joined_obj.name not in export_coll.objects:
                export_coll.objects.link(joined_obj)
            for coll in list(joined_obj.users_collection):
                if coll.name != "Export":
                    try:
                        coll.objects.unlink(joined_obj)
                    except Exception:
                        pass

        return {'FINISHED'}


# Export Path
def GetExportPath(abspath=False):
    scene = bpy.context.scene

    path = bpy.path.abspath(scene.export_folder)

    create_dir(path)

    return path


# Creates directory if none
def create_dir(path):
    # безопасно создаем даже вложенные директории
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass


# Main export function
def ExportMain(selected):
    obj_dict = {}
    exported_names = []

    for obj in selected:
        obj_dict[obj.exportname] = []
        exported_names.append(obj.name)
    for obj in selected:
        if obj.lod == "NITE":
            obj_dict[obj.exportname].append(obj)
        if obj.lod == "LOD0":
            obj_dict[obj.exportname].append(obj)
        if obj.lod in ["LOD1", "LOD2", "LOD3"]:
            obj_dict[obj.exportname].append(obj)
        if obj.lod == "UCX":
            obj_dict[obj.exportname].append(obj)

    path = GetExportPath()
    ExportMeshes(obj_dict, path)

    return exported_names


def ExportMeshes(obj_dict, path):
    bpy.ops.object.select_all(action='DESELECT')

    # создаем подпапку для LOD1–LOD3
    lods_dir = os.path.join(path, "LODs")
    create_dir(lods_dir)
    nanite_dir = os.path.join(path, "Nanite")
    create_dir(nanite_dir)

    for key in obj_dict:
        meshes = obj_dict[key]

        # определяем тип LOD по первому элементу группы
        lod_type = meshes[0].lod if meshes else None

        # все LOD1–LOD3 уезжают в подпапку LODs
        if lod_type in ["LOD1", "LOD2", "LOD3"]:
            target_dir = lods_dir
        elif lod_type == "NITE":
            target_dir = nanite_dir
        else:
            target_dir = path
        final_path = os.path.join(target_dir, str(key))

        for mesh in meshes:
            mesh.select_set(True)

        if bpy.app.version >= (4, 2):
            bpy.ops.export_scene.fbx(
                filepath=final_path + ".fbx",
                use_selection=True,
                mesh_smooth_type="FACE",
                bake_space_transform=False,
                axis_forward="Y",
                axis_up="Z",
                bake_anim=False
            )
        else:
            bpy.ops.export_scene.fbx(
                filepath=final_path + ".fbx",
                use_selection=True,
                mesh_smooth_type="FACE",
                bake_space_transform=False,
                bake_anim=False
            )

        bpy.ops.object.select_all(action='DESELECT')


# Export button
class Exportfbx(bpy.types.Operator):
    bl_idname = "object.exportfbx_operator"
    bl_label = "Export .fbx"

    def execute(self, context):
        scene = bpy.context.scene
        view_layer = bpy.context.view_layer
        obj_active = view_layer.objects.active

        valid_msg = None
        obj_for_export = []

        hidden_selection = is_hidden_selection()

        unhide_selected(hidden_selection)
        orig_selection = save_selected()
        # if name is valid, append to export array
        for obj in orig_selection:
            valid_msg = name_validation(obj)
            if valid_msg is not None:
                self.report({'WARNING'}, str(valid_msg))

        bpy.ops.object.duplicate()
        dublicate_selection = save_selected()

        # Secect\Create material
        if scene.apply_material:
            material_name = scene.material_name
            material = create_material(material_name)

        # Rename meshes
        for obj in orig_selection:
            obj_init(obj)
            rename_origs(obj)

        # Prepare doubles for export
        for obj in dublicate_selection:
            rename_doubles(obj)
            obj_init(obj)
            if scene.reset_tramsforms:
                reset_transforms(obj)
            if scene.apply_material:
                apply_single_material(obj, material)
            if scene.reassigne_materials:
                reassign_materials(obj, context)
                pass

        # if name is valid, append to export array
        for obj in dublicate_selection:
            valid_msg = name_validation(obj)
            if valid_msg is not None:
                self.report({'WARNING'}, str(valid_msg))
            else:
                obj_for_export.append(obj)

        exported_names = ExportMain(obj_for_export)

        if exported_names != []:
            self.report({'INFO'}, str(", ").join(exported_names) + " are exported")
        else:
            None

        # Delete doubles
        for obj in dublicate_selection:
            bpy.data.objects.remove(obj.bl_object)

        # Rename origs back
        for obj in orig_selection:
            obj.name = obj.orig_name

        view_layer.objects.active = obj_active
        for obj in orig_selection:
            obj.select_set(True)
        hide_back(hidden_selection)

        orig_selection = None
        dublicate_selection = None

        return {'FINISHED'}


class Open_Folder(bpy.types.Operator):
    bl_idname = "object.open_folder_operator"
    bl_label = "Open Export folder"

    def execute(self, context):
        scene = bpy.context.scene

        path = bpy.path.abspath(scene.export_folder)
        path = os.path.realpath(path)
        os.startfile(path)

        return {'FINISHED'}
