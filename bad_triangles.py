import bpy
import bmesh


def get_quality_metric(a: float, b: float, c: float, area: float) -> float:
    """
    Вычисляет метрику качества треугольника на основе соотношения
    радиусов вписанной и описанной окружностей.
    r/R → 0 для вырожденных, → 0.5 для равносторонних.
    """
    if a == 0 or b == 0 or c == 0:
        return 0.0
    if area == 0:
        return 0.0

    s = (a + b + c) * 0.5
    r = area / s
    R = (a * b * c) / (4.0 * area)

    if R == 0:
        return 0.0
    return r / R


def _get_original_mode(obj: bpy.types.Object) -> str:
    ctx_obj = bpy.context.object
    if ctx_obj and ctx_obj.name == obj.name:
        return ctx_obj.mode
    return 'OBJECT'


def _ensure_object_mode(obj: bpy.types.Object) -> str:
    original_mode = _get_original_mode(obj)
    ctx_obj = bpy.context.object
    if ctx_obj and ctx_obj.name == obj.name and original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    return original_mode


def _restore_mode(obj: bpy.types.Object, original_mode: str) -> None:
    if original_mode == 'OBJECT':
        return
    ctx_obj = bpy.context.object
    if ctx_obj and ctx_obj.name == obj.name:
        try:
            bpy.ops.object.mode_set(mode=original_mode)
        except Exception:
            pass


def analyze_mesh_quality(
    obj: bpy.types.Object,
    bad_threshold: float,
    warning_threshold: float,
    bad_color: tuple = (1.0, 0.0, 0.0, 1.0),
    warning_color: tuple = (1.0, 1.0, 0.0, 1.0),
):
    if obj.type != 'MESH':
        return 0, 0

    mesh = obj.data
    original_mode = _ensure_object_mode(obj)

    bm = bmesh.new()
    bm.from_mesh(mesh)

    color_layer = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")

    bad_count = 0
    warning_count = 0

    for f in bm.faces:
        if len(f.verts) != 3:
            continue

        v0, v1, v2 = [v.co for v in f.verts]
        a = (v0 - v1).length
        b = (v1 - v2).length
        c = (v2 - v0).length

        area = f.calc_area()
        quality = get_quality_metric(a, b, c, area)

        if quality < bad_threshold:
            color = bad_color
            bad_count += 1
        elif quality < warning_threshold:
            color = warning_color
            warning_count += 1
        else:
            color = (1.0, 1.0, 1.0, 1.0)

        for loop in f.loops:
            loop[color_layer] = color

    bm.to_mesh(mesh)
    bm.free()

    _restore_mode(obj, original_mode)
    return bad_count, warning_count


def analyze_mesh_quality_editmode(
    obj: bpy.types.Object,
    bad_threshold: float,
    warning_threshold: float,
    bad_color: tuple = (1.0, 0.0, 0.0, 1.0),
    warning_color: tuple = (1.0, 1.0, 0.0, 1.0),
):
    """
    Версия analyze для вызова из Edit Mode без переключения режимов.
    Работает напрямую с активным BMesh.
    """
    if obj.type != 'MESH':
        return 0, 0

    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    color_layer = bm.loops.layers.color.get("Col") or bm.loops.layers.color.new("Col")

    bad_count = 0
    warning_count = 0

    for f in bm.faces:
        if len(f.verts) != 3:
            continue

        v0, v1, v2 = [v.co for v in f.verts]
        a = (v0 - v1).length
        b = (v1 - v2).length
        c = (v2 - v0).length

        area = f.calc_area()
        quality = get_quality_metric(a, b, c, area)

        if quality < bad_threshold:
            color = bad_color
            bad_count += 1
        elif quality < warning_threshold:
            color = warning_color
            warning_count += 1
        else:
            color = (1.0, 1.0, 1.0, 1.0)

        for loop in f.loops:
            loop[color_layer] = color

    bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)

    return bad_count, warning_count


def select_bad_triangles(
    obj: bpy.types.Object,
    bad_threshold: float,
    warning_threshold: float,
    select_bad: bool = True,
    select_warning: bool = True,
) -> int:
    if obj.type != 'MESH':
        return 0

    mesh = obj.data
    bpy.context.view_layer.objects.active = obj

    original_mode = _get_original_mode(obj)
    if original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(mesh)

    for f in bm.faces:
        f.select = False
    for e in bm.edges:
        e.select = False
    for v in bm.verts:
        v.select = False

    selected_count = 0

    for f in bm.faces:
        if len(f.verts) != 3:
            continue

        v0, v1, v2 = [v.co for v in f.verts]
        a = (v0 - v1).length
        b = (v1 - v2).length
        c = (v2 - v0).length

        area = f.calc_area()
        quality = get_quality_metric(a, b, c, area)

        should_select = False
        if select_bad and quality < bad_threshold:
            should_select = True
        elif select_warning and bad_threshold <= quality < warning_threshold:
            should_select = True

        if should_select:
            f.select = True
            selected_count += 1

    bm.to_mesh(mesh)
    bm.free()

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)

    return selected_count


def clear_vertex_colors(obj: bpy.types.Object):
    if obj.type != 'MESH':
        return

    mesh = obj.data
    original_mode = _ensure_object_mode(obj)

    bm = bmesh.new()
    bm.from_mesh(mesh)

    color_layer = bm.loops.layers.color.get("Col")
    if color_layer:
        for f in bm.faces:
            for loop in f.loops:
                loop[color_layer] = (1.0, 1.0, 1.0, 1.0)
        bm.to_mesh(mesh)

    bm.free()
    _restore_mode(obj, original_mode)


def has_color_layer(obj: bpy.types.Object) -> bool:
    if obj.type != 'MESH':
        return False
    return "Col" in obj.data.color_attributes