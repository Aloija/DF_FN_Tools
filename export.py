# export.py
import bpy
import os

from .mesh_object_classes import *
from .ui import *
from .utils import *

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

    for key in obj_dict:
        meshes = obj_dict[key]

        # определяем тип LOD по первому элементу группы
        lod_type = meshes[0].lod if meshes else None

        # все LOD1–LOD3 уезжают в подпапку LODs
        target_dir = lods_dir if lod_type in ["LOD1", "LOD2", "LOD3"] else path
        final_path = os.path.join(target_dir, str(key))

        for mesh in meshes:
            mesh.data.select_set(True)

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
            bpy.data.objects.remove(obj.data)

        # Rename origs back
        for obj in orig_selection:
            obj.data.name = obj.orig_name

        view_layer.objects.active = obj_active
        for obj in orig_selection:
            obj.data.select_set(True)
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
