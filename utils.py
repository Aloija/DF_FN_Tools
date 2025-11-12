import bpy # type: ignore
import re
import bmesh # type: ignore

from .mesh_object_classes import MeshObject


# Name validation
validate_list = ["LOD0", "LOD1", "LOD2", "LOD3", "UCX"]

MATERIAL_REASSIGN_SLOT_COUNT = 4

def name_validation(mesh_obj: MeshObject):
    valid_msg = None
    name = []
    invalid_characters = '[\u0400-\u04FF+@!#$%^&*()<>?/\|}{~:]'

    if bool(re.search(invalid_characters, mesh_obj.name)):
        valid_msg = (mesh_obj.name + " has invalid characters: " + str((re.findall(invalid_characters, mesh_obj.name))))
        return valid_msg

    if "_" in mesh_obj.name:
        name = mesh_obj.name.split("_")
    else:
        valid_msg = (mesh_obj.name + " has incorrect name")
        return valid_msg
    

    if name[0] in validate_list:
        if name[0] == "UCX":
            if name [1] != "LOD0":
                valid_msg = ("add 'LOD0' to the ", mesh_obj.name, " name")
                return valid_msg
            try:
                test = int(name[-1])
                return valid_msg
            except ValueError:
                valid_msg = (mesh_obj.name + " should be enumerated")
                return valid_msg
        else:
            return valid_msg
    else:
        has_second_part = len(name) > 1
        if has_second_part and name[1] == "NITE":
            return valid_msg
        else: 
            valid_msg = (mesh_obj.name + " has incorrect prefix: " + str(name[0]))
            return valid_msg
    

def rename_origs(mesh_obj: MeshObject):
    prefix = "og_"
    mesh_obj.orig_name = mesh_obj.name
    mesh_obj.name = prefix + mesh_obj.name


def rename_doubles(mesh_obj: MeshObject):
    base_name = mesh_obj.name.split(".")[0]
    mesh_obj.name = base_name


def set_name(mesh_obj: MeshObject):
    mesh = mesh_obj.mesh
    if mesh and hasattr(mesh, "name"):
        mesh.name = mesh_obj.name


def reset_transforms(mesh_obj: MeshObject):
    location = (0.0, 0.0, 0.0)
    rotation = (0.0, 0.0, 0.0)
    scale = (1.0, 1.0, 1.0)
    bl_obj = mesh_obj.bl_object
    bl_obj.location = location
    bl_obj.rotation_euler = rotation
    bl_obj.scale = scale


def create_material(material_name):
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        mat = bpy.data.materials.new(name=material_name)
    return mat
    

def apply_single_material(mesh_obj: MeshObject, material):
    mesh_data = mesh_obj.mesh
    mesh_data.materials.clear()
    mesh_data.materials.append(material)


def reassign_materials(mesh_obj: MeshObject, context):
    scene = context.scene
    mesh_data = mesh_obj.mesh

    # Карта старых имен материалов к новым
    material_map = {
        getattr(scene, f"material_from_{i}"): getattr(scene, f"material_to_{i}")
        for i in range(4)
        if getattr(scene, f"material_from_{i}") and getattr(scene, f"material_to_{i}") and
           getattr(scene, f"material_from_{i}") != getattr(scene, f"material_to_{i}")
    }

    if not material_map:
        return

    def ensure_material_slot(material):
        for i, m in enumerate(mesh_data.materials):
            if m and m.name == material.name:
                return i
        mesh_data.materials.append(material)
        return len(mesh_data.materials) - 1

    # Карта: индекс полигона → имя нового материала
    poly_material_names = {}

    for poly in mesh_data.polygons:
        old_index = poly.material_index
        if old_index >= len(mesh_data.materials):
            continue
        old_mat = mesh_data.materials[old_index]
        if not old_mat:
            continue

        to_name = material_map.get(old_mat.name)
        if to_name:
            new_mat = create_material(to_name)
            ensure_material_slot(new_mat)
            poly_material_names[poly.index] = new_mat.name
        else:
            poly_material_names[poly.index] = old_mat.name

    # Собираем только те материалы, которые реально используются
    used_mat_names = set(poly_material_names.values())
    used_materials = [mat for mat in mesh_data.materials if mat and mat.name in used_mat_names]

    # Перезаписываем материалы
    mesh_data.materials.clear()
    for mat in used_materials:
        mesh_data.materials.append(mat)

    # Обновляем индексы полигонов
    name_to_new_index = {mat.name: i for i, mat in enumerate(mesh_data.materials)}
    for poly in mesh_data.polygons:
        mat_name = poly_material_names.get(poly.index)
        if mat_name:
            poly.material_index = name_to_new_index.get(mat_name, 0)  # default fallback to 0


def is_isolated():
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            view_3d = area.spaces.active
        
    if view_3d.local_view:
        print("Local view active")
    else:
        print("Local view not active")


def get_id_type(obj):
    return obj.bl_rna.identifier.upper()


def is_hidden_selection():
    hidden_selection = []
    scr = bpy.context.screen
    areas = [area for area in scr.areas if area.type == 'OUTLINER']
    regions = [region for region in areas[0].regions if region.type == 'WINDOW']

    with bpy.context.temp_override(area=areas[0], region=regions[0], screen=scr):
        for obj in bpy.context.selected_ids:
            id_type = get_id_type(obj)
            if id_type == "OBJECT":
                if obj.visible_get() == False:
                    hidden_selection.append(obj)
    return hidden_selection


def unhide_selected(hidden_selection):
    for obj in hidden_selection:
        obj.hide_set(False)
        obj.select_set(True)


def hide_back(hidden_selection):
    for obj in hidden_selection:
        obj.hide_set(True)


def get_materials(self, context):
    return [(mat.name, mat.name, "") for mat in bpy.data.materials]


def get_split_vertex_count():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total_vertices = 0

    # Фильтруем только MESH-объекты
    mesh_objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not mesh_objs:
        return 0

    r6 = lambda x: round(x, 6)
    r4 = lambda x: round(x, 4)

    for obj in mesh_objs:
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        if mesh is None:
            continue

        # Триангулируем все полигоны, чтобы убрать N-гоны
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(
            bm,
            faces=bm.faces[:],
            quad_method='BEAUTY',
            ngon_method='BEAUTY'
        )
        bm.to_mesh(mesh)
        bm.free()

        # Получаем loop-триангуляцию
        mesh.calc_loop_triangles()

        uv_layers = mesh.uv_layers
        color_layers = mesh.vertex_colors

        # Если есть UV, считаем тангенты на уже триангулированном меше
        if uv_layers:
            mesh.calc_tangents()

        loops = mesh.loops
        tris = mesh.loop_triangles

        uv_data = [uv.data for uv in uv_layers]
        col_data = [col.data for col in color_layers]

        unique_corners = set()

        for tri in tris:
            mat_idx = tri.material_index
            for li in tri.loops:
                lp = loops[li]
                key = (
                    lp.vertex_index,
                    r6(lp.normal.x), r6(lp.normal.y), r6(lp.normal.z),
                    r6(lp.tangent.x) if uv_layers else 0.0,
                    r6(lp.tangent.y) if uv_layers else 0.0,
                    r6(lp.tangent.z) if uv_layers else 0.0,
                    r6(lp.bitangent_sign) if uv_layers else 0.0,
                    mat_idx,
                )
                for data in uv_data:
                    uv = data[li].uv
                    key += (r6(uv.x), r6(uv.y))
                for data in col_data:
                    c = data[li].color
                    key += (r4(c[0]), r4(c[1]), r4(c[2]), r4(c[3]))
                unique_corners.add(key)

        total_vertices += len(unique_corners)
        eval_obj.to_mesh_clear()

    return total_vertices


def update_split_vertex_count(scene):
    obj = bpy.context.view_layer.objects.active
    if obj:
        count = get_split_vertex_count()
        scene.split_vertex_count = count
    else:
        scene.split_vertex_count = -1


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

            try:
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            except Exception:
                pass

            try:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.normals_make_consistent(inside=False)
            except Exception:
                pass
            finally:
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass

            for mod in list(obj.modifiers):
                if mod.type == 'TRIANGULATE':
                    continue  # keep triangulate modifiers intact
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
        rename_uv()
        bpy.ops.object.join()

        joined_obj = context.active_object

        if joined_obj:
            source_colls = [coll for coll in joined_obj.users_collection if coll.name != "Scene Collection"]
            if source_colls:
                new_name = source_colls[0].name
                joined_obj.name = new_name
                if getattr(joined_obj, "data", None):
                    joined_obj.data.name = new_name

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


def rename_uv():
    context = bpy.context
    for obj in [o for o in context.selected_objects if o.type == 'MESH' and hasattr(o, 'data') and o.data]:
        mesh = obj.data
        uv_layers = mesh.uv_layers
        # Ensure at least one UV layer exists
        if len(uv_layers) == 0:
            uv_layers.new(name='map1')
        # Rename first channel to 'map1'
        uv_layers[0].name = 'map1'
        # Ensure second channel exists and rename to 'uvSet1'
        if len(uv_layers) < 2:
            uv_layers.new(name='uvSet1')
        else:
            uv_layers[1].name = 'uvSet1'
        # If there is a third channel, merge it into the first
        if len(uv_layers) >= 3:
            first_layer = uv_layers[0]
            third_layer = uv_layers[2]
            # Merge rule: copy UVs from the 3rd layer into the 1st
            # only where the 1st layer UVs are (0,0). This keeps
            # existing 1st layer data while augmenting from the 3rd.
            loop_count = len(mesh.loops)
            for li in range(loop_count):
                uv1 = first_layer.data[li].uv
                uv3 = third_layer.data[li].uv
                if abs(uv1.x) < 1e-6 and abs(uv1.y) < 1e-6:
                    first_layer.data[li].uv = (uv3.x, uv3.y)
            # Remove the third layer after merge
            uv_layers.remove(third_layer)
        # Remove all channels beyond the first two
        while len(uv_layers) > 2:
            uv_layers.remove(uv_layers[-1])
        # Re-assert names in case indices shifted after removals
        uv_layers[0].name = 'map1'
        if len(uv_layers) >= 2:
            uv_layers[1].name = 'uvSet1'


class OBJECT_OT_rename_uv(bpy.types.Operator):
    bl_idname = "object.rename_uv"
    bl_label = "Rename UVs"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            rename_uv()
        except Exception as e:
            self.report({'ERROR'}, f"Failed to rename UVs: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}

