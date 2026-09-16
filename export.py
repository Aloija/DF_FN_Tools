# export.py
import bpy # type: ignore
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


def collect_related_meshes(selected):
    pass

# Main export function
def get_export_group_name(mesh_obj, combine_lods, lod0_export_names):
    if combine_lods and mesh_obj.lod != "LOD0" and is_lod_name(mesh_obj.lod):
        lod0_name = mesh_obj.exportname.rsplit("_", 1)[0]
        if lod0_name in lod0_export_names:
            return lod0_name
    return mesh_obj.exportname


def ExportMain(selected):
    obj_dict = {}
    exported_names = []
    combine_lods = bpy.context.scene.export_lods_with_lod0
    lod0_export_names = {obj.exportname for obj in selected if obj.lod == "LOD0"}

    for obj in selected:
        exported_names.append(obj.name)
        if obj.lod in ("NITE", "UCX") or is_lod_name(obj.lod):
            group_name = get_export_group_name(obj, combine_lods, lod0_export_names)
            obj_dict.setdefault(group_name, []).append(obj)

    path = GetExportPath()
    ExportMeshes(obj_dict, path)

    return exported_names


def ExportMeshes(obj_dict, path):
    scene = bpy.context.scene

    bpy.ops.object.select_all(action='DESELECT')

    # создаем подпапку для дополнительных LOD
    lods_dir = os.path.join(path, "LODs")
    create_dir(lods_dir)
    nanite_dir = os.path.join(path, "NITE")
    create_dir(nanite_dir)

    for key in obj_dict:
        meshes = obj_dict[key]

        # определяем тип LOD по первому элементу группы
        lod_type = meshes[0].lod if meshes else None

        # Группа с LOD0 всегда экспортируется как основной FBX.
        if any(mesh.lod == "LOD0" for mesh in meshes):
            target_dir = path
        elif is_lod_name(lod_type):
            target_dir = lods_dir
        elif lod_type == "NITE":
            target_dir = nanite_dir
        else:
            target_dir = path
        final_path = os.path.join(target_dir, str(key))

        for mesh in meshes:
            mesh.select_set(True)

        # bake_space_transform запекает юнит-скейл в вершины, а не в трансформ
        # объекта: меш приезжает в Maya в сантиметрах с единичным скейлом
        # независимо от Unit Scale сцены.
        bpy.ops.export_scene.fbx(
            filepath=final_path + ".fbx",
            use_selection=True,
            mesh_smooth_type="FACE",
            bake_space_transform=scene.export_auto_scale,
            axis_forward="Y",
            axis_up="Z",
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

        # Выделение вьюпорта + выделение Outliner, если он открыт
        orig_selection = collect_export_selection()

        if not orig_selection:
            self.report({'WARNING'}, "Nothing selected")
            return {'CANCELLED'}

        # Автоматический поиск связанных мешей по имени (LOD'ы, UCX).
        # Ищет в bpy.data.objects, поэтому находит и скрытые.
        if scene.export_with_related:
            expanded_selection = find_related_meshes(orig_selection, bpy.data.objects)

            additional_count = len(expanded_selection) - len(orig_selection)
            if additional_count > 0:
                self.report({'INFO'}, f"Found {additional_count} additional related mesh(es)")

            orig_selection = expanded_selection

        # Раскрываем всё, что экспортируем: объекты, их коллекции и layer collections
        visibility_states = ensure_objects_visible(orig_selection)

        # if name is valid, append to export array
        for obj in orig_selection:
            valid_msg = name_validation(obj)
            if valid_msg is not None:
                self.report({'WARNING'}, str(valid_msg))

        # Выделяем ВСЕ объекты перед дублированием
        bpy.ops.object.select_all(action='DESELECT')
        for obj in orig_selection:
            obj.select_set(True)

        # Устанавливаем активный объект
        if orig_selection:
            view_layer.objects.active = orig_selection[0].bl_object

        # linked=False: иначе дубликат шарит mesh data с оригиналом
        # и правки материалов/UV уходят в исходный меш сцены
        bpy.ops.object.duplicate(linked=False)
        dublicate_selection = save_selected()

        # Select\Create material
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
            if obj.lod == "UCX":
                strip_ucx_data(obj)
                continue
            if scene.apply_material:
                apply_single_material(obj, material)
            if scene.reassigne_materials:
                reassign_materials(obj, context)

        # if name is valid, append to export array
        for obj in dublicate_selection:
            valid_msg = name_validation(obj)
            if valid_msg is not None:
                self.report({'WARNING'}, str(valid_msg))
            else:
                obj_for_export.append(obj)

        exported_names = ExportMain(obj_for_export)

        if exported_names:
            self.report({'INFO'}, str(", ").join(exported_names) + " are exported")

        # Delete doubles
        for obj in dublicate_selection:
            bpy.data.objects.remove(obj.bl_object)

        # Rename origs back
        for obj in orig_selection:
            obj.name = obj.orig_name

        view_layer.objects.active = obj_active
        for obj in orig_selection:
            obj.select_set(True)

        # Восстанавливаем видимость последней: скрытый объект не выделяется
        restore_objects_visibility(orig_selection, visibility_states)

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
