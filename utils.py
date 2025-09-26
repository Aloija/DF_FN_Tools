import bpy
import re
import bmesh

from .mesh_object_classes import *
from bpy.app.handlers import persistent


# Name validation 
validate_list = ["LOD0", "LOD1", "LOD2", "LOD3", "UCX"]

def name_validation (obj):
    valid_msg = None
    name = []
    invalid_characters = '[\u0400-\u04FF+@!#$%^&*()<>?/\|}{~:]'

    if bool(re.search(invalid_characters, obj.name)):
        valid_msg = (obj.name + " has invalid characters: " + str((re.findall(invalid_characters, obj.name))))
        return valid_msg

    if "_" in obj.name:
        name = obj.name.split("_")
    else:
        valid_msg = (obj.name + " has incorrect name")
        return valid_msg
    

    if name[0] in validate_list:
        if name[0] == "UCX":
            if name [1] != "LOD0":
                valid_msg = ("add 'LOD0' to the ", obj.name, " name")
                return valid_msg
            try:
                test = int(name[-1])
                return valid_msg
            except ValueError:
                valid_msg = (obj.name + " should be enumerated")
                return valid_msg
        else:
            return valid_msg
    else:
        if name[1] == "NITE":
            return valid_msg
        else: 
            valid_msg = (obj.name + " has incorrect prefix: " + str(name[0]))
            return valid_msg
    

def rename_origs(obj):
    prefix = "og_"
    obj.orig_name = obj.name
    obj.name = prefix + obj.name
    obj.data.name = obj.name


def rename_doubles(obj):
    name = obj.name.split(".")
    obj.name = str(name[0])
    obj.data.name = obj.name


def set_name(obj):
    obj.data.name = obj.name


def reset_transforms(obj):
    location = (0.0, 0.0, 0.0)
    rotation = (0.0, 0.0, 0.0)
    scale = (1.0, 1.0, 1.0)
    obj.data.location = location
    obj.data.rotation_euler = rotation
    obj.data.scale = scale


def create_material(material_name):
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        mat = bpy.data.materials.new(name=material_name)
    return mat
    

def apply_single_material(obj, material):
    obj.data.data.materials.clear()
    obj.data.data.materials.append(material)


def reassign_materials(obj, context):
    scene = context.scene
    mesh_data = obj.data.data

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


def rename_uv():
    context = bpy.context

    for obj in context.selected_objects:
        try:
            obj.data.uv_layers.data.uv_layer_stencil.name = 'map1'
            obj.data.uv_layers.new(name='uvSet1')
        except:    
            continue


def get_materials(self, context):
    return [(mat.name, mat.name, "") for mat in bpy.data.materials]


for i in range(4):
    setattr(bpy.types.Scene, f"material_from_{i}", bpy.props.EnumProperty(
        name=f"Material {i+1}",
        description="Select a material to reassign",
        items=get_materials
    ))
    setattr(bpy.types.Scene, f"material_to_{i}", bpy.props.StringProperty(
        name="New Name",
        description="Enter a new material name",
        default=""
    ))


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


@persistent
def depsgraph_update(scene, depsgraph):
    context_scene = bpy.context.scene
    if context_scene and getattr(context_scene, "auto_update_split_vertex_count", False):
        update_split_vertex_count(context_scene)


@persistent
def load_handler(dummy):
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update)
    update_split_vertex_count(bpy.context.scene)

