import bpy
import os

from bpy.types import AddonPreferences
from bpy.props import EnumProperty

from .bad_triangles import (
    analyze_mesh_quality,
    analyze_mesh_quality_editmode,
    clear_vertex_colors,
    has_color_layer,
    select_bad_triangles,
)


# ---------------------------------------------------------------------------
# Live‑update state
# ---------------------------------------------------------------------------

_live_update_timer = None
_live_update_dirty = False


# ---------------------------------------------------------------------------
# Scene properties — Bad Triangles
# ---------------------------------------------------------------------------

def _on_live_update_changed(self, context):
    """Вызывается при переключении галочки Live Update."""
    if self.bt_live_update:
        _live_start(context)
    else:
        _live_stop(context)


def _register_bad_triangles_props():
    bpy.types.Scene.bt_bad_threshold = bpy.props.FloatProperty(
        name="Bad threshold",
        description="Грани с метрикой ниже этого значения окрашиваются как плохие",
        default=0.05, min=0.0, max=1.0, step=1, precision=3,
        update=_on_threshold_or_color_changed,
    )
    bpy.types.Scene.bt_warning_threshold = bpy.props.FloatProperty(
        name="Warning threshold",
        description="Грани с метрикой ниже этого значения окрашиваются как предупреждение",
        default=0.15, min=0.0, max=1.0, step=1, precision=3,
        update=_on_threshold_or_color_changed,
    )
    bpy.types.Scene.bt_bad_color = bpy.props.FloatVectorProperty(
        name="Bad color",
        description="Цвет плохих треугольников",
        subtype='COLOR', size=4,
        default=(1.0, 0.0, 0.0, 1.0), min=0.0, max=1.0,
        update=_on_threshold_or_color_changed,
    )
    bpy.types.Scene.bt_warning_color = bpy.props.FloatVectorProperty(
        name="Warning color",
        description="Цвет предупреждающих треугольников",
        subtype='COLOR', size=4,
        default=(1.0, 1.0, 0.0, 1.0), min=0.0, max=1.0,
        update=_on_threshold_or_color_changed,
    )
    bpy.types.Scene.bt_select_mode = bpy.props.EnumProperty(
        name="Select mode",
        description="Какие треугольники выделять",
        items=[
            ('BAD',     "Bad Only",      "Выделить только плохие треугольники"),
            ('WARNING', "Warning Only",  "Выделить только предупреждающие треугольники"),
            ('BOTH',    "Bad + Warning", "Выделить плохие и предупреждающие треугольники"),
        ],
        default='BOTH',
    )
    bpy.types.Scene.bt_live_update = bpy.props.BoolProperty(
        name="Live Update",
        description="Автоматически обновлять раскраску при изменении меша",
        default=False,
        update=_on_live_update_changed,
    )
    bpy.types.Scene.bt_bad_count = bpy.props.IntProperty(
        name="Bad triangles", default=-1, options={'SKIP_SAVE'},
    )
    bpy.types.Scene.bt_warning_count = bpy.props.IntProperty(
        name="Warning triangles", default=-1, options={'SKIP_SAVE'},
    )


def _unregister_bad_triangles_props():
    props = (
        "bt_bad_threshold", "bt_warning_threshold",
        "bt_bad_color", "bt_warning_color",
        "bt_select_mode", "bt_live_update",
        "bt_bad_count", "bt_warning_count",
    )
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)


# ---------------------------------------------------------------------------
# Live‑update helpers
# ---------------------------------------------------------------------------

def _on_threshold_or_color_changed(self, context):
    """Мгновенно пересчитать, если live update включён."""
    if self.bt_live_update:
        _run_live_analysis(context)


def _run_live_analysis(context):
    """Выполняет анализ для активного меша и обновляет счётчики."""
    scene = context.scene
    obj = context.view_layer.objects.active
    if not obj or obj.type != 'MESH':
        return

    bad_threshold     = scene.bt_bad_threshold
    warning_threshold = scene.bt_warning_threshold
    if bad_threshold >= warning_threshold:
        return

    bad_color     = tuple(scene.bt_bad_color)
    warning_color = tuple(scene.bt_warning_color)

    # Выбираем функцию в зависимости от текущего режима
    if obj.mode == 'EDIT':
        bad_count, warning_count = analyze_mesh_quality_editmode(
            obj, bad_threshold, warning_threshold,
            bad_color=bad_color, warning_color=warning_color,
        )
    else:
        bad_count, warning_count = analyze_mesh_quality(
            obj, bad_threshold, warning_threshold,
            bad_color=bad_color, warning_color=warning_color,
        )

    scene.bt_bad_count     = bad_count
    scene.bt_warning_count = warning_count

    # Vertex color display
    if obj.data.color_attributes:
        obj.data.attributes.active_color_index = 0

    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.color_type = 'VERTEX'


def _depsgraph_handler(scene, depsgraph):
    """Обработчик depsgraph — помечает что нужен пересчёт."""
    global _live_update_dirty

    if not scene.bt_live_update:
        return

    obj = bpy.context.view_layer.objects.active
    if not obj or obj.type != 'MESH':
        return

    # Проверяем, что обновился именно наш объект
    for update in depsgraph.updates:
        if update.id.name == obj.data.name:
            _live_update_dirty = True
            return


def _timer_tick():
    """Таймер — выполняет пересчёт если depsgraph пометил dirty."""
    global _live_update_dirty

    if _live_update_dirty:
        _live_update_dirty = False
        ctx = bpy.context
        if ctx and hasattr(ctx, 'scene') and ctx.scene and ctx.scene.bt_live_update:
            try:
                _run_live_analysis(ctx)
            except Exception:
                pass

    return 0.2  # интервал в секундах


def _live_start(context):
    """Запускает live‑update: таймер + хэндлер."""
    global _live_update_timer

    # Хэндлер
    if _depsgraph_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_handler)

    # Таймер
    if _live_update_timer is None:
        _live_update_timer = bpy.app.timers.register(_timer_tick, persistent=True)

    # Первый запуск сразу
    _run_live_analysis(context)


def _live_stop(context):
    """Останавливает live‑update."""
    global _live_update_timer

    if _depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_handler)

    if _live_update_timer is not None:
        try:
            bpy.app.timers.unregister(_timer_tick)
        except Exception:
            pass
        _live_update_timer = None


# ---------------------------------------------------------------------------
# Operators — Bad Triangles
# ---------------------------------------------------------------------------

class DFT_OT_analyze_triangles(bpy.types.Operator):
    """Окрасить плохие треугольники в активном меше"""
    bl_idname = "object.dft_analyze_triangles"
    bl_label = "Analyze Triangles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.view_layer.objects.active
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        scene = context.scene
        obj = context.view_layer.objects.active

        bad_threshold     = scene.bt_bad_threshold
        warning_threshold = scene.bt_warning_threshold

        if bad_threshold >= warning_threshold:
            self.report({'WARNING'}, "Bad threshold должен быть меньше Warning threshold")
            return {'CANCELLED'}

        bad_color     = tuple(scene.bt_bad_color)
        warning_color = tuple(scene.bt_warning_color)

        bad_count, warning_count = analyze_mesh_quality(
            obj, bad_threshold, warning_threshold,
            bad_color=bad_color, warning_color=warning_color,
        )

        scene.bt_bad_count     = bad_count
        scene.bt_warning_count = warning_count

        if obj.data.color_attributes:
            obj.data.attributes.active_color_index = 0

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.color_type = 'VERTEX'

        self.report({'INFO'}, f"Bad: {bad_count}  |  Warning: {warning_count}")
        return {'FINISHED'}


class DFT_OT_clear_triangle_colors(bpy.types.Operator):
    """Сбросить вершинные цвета активного меша"""
    bl_idname = "object.dft_clear_triangle_colors"
    bl_label = "Clear Colors"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.view_layer.objects.active
        return obj is not None and obj.type == 'MESH' and has_color_layer(obj)

    def execute(self, context):
        scene = context.scene
        obj = context.view_layer.objects.active

        clear_vertex_colors(obj)

        scene.bt_bad_count     = -1
        scene.bt_warning_count = -1

        self.report({'INFO'}, "Vertex colors cleared")
        return {'FINISHED'}


class DFT_OT_select_bad_triangles(bpy.types.Operator):
    """Выделить плохие/предупреждающие треугольники в Edit Mode"""
    bl_idname = "object.dft_select_bad_triangles"
    bl_label = "Select Bad Triangles"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.view_layer.objects.active
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        scene = context.scene
        obj = context.view_layer.objects.active

        bad_threshold     = scene.bt_bad_threshold
        warning_threshold = scene.bt_warning_threshold

        if bad_threshold >= warning_threshold:
            self.report({'WARNING'}, "Bad threshold должен быть меньше Warning threshold")
            return {'CANCELLED'}

        mode = scene.bt_select_mode
        select_bad     = mode in ('BAD', 'BOTH')
        select_warning = mode in ('WARNING', 'BOTH')

        selected_count = select_bad_triangles(
            obj, bad_threshold, warning_threshold,
            select_bad=select_bad, select_warning=select_warning,
        )

        self.report({'INFO'}, f"Selected {selected_count} triangle(s)")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panel — Bad Triangles (popover)
# ---------------------------------------------------------------------------

class DFT_PT_bad_triangles_panel(bpy.types.Panel):
    bl_idname = "DFT_PT_bad_triangles_panel"
    bl_label = "Bad Triangles"
    bl_space_type = 'TOPBAR'
    bl_region_type = 'HEADER'
    bl_category = "DF FN Tools"

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.ui_units_x = 14

        obj = context.view_layer.objects.active
        is_mesh = obj is not None and obj.type == 'MESH'

        # --- Live Update ---
        row = layout.row()
        row.prop(scene, "bt_live_update", icon='FILE_REFRESH', toggle=True)

        layout.separator()

        # --- Пороги ---
        col = layout.column(align=True)
        col.label(text="Thresholds:")
        col.prop(scene, "bt_bad_threshold",     text="Bad")
        col.prop(scene, "bt_warning_threshold", text="Warning")

        if scene.bt_bad_threshold >= scene.bt_warning_threshold:
            row = layout.row()
            row.alert = True
            row.label(text="Bad must be < Warning", icon='ERROR')

        layout.separator()

        # --- Цвета ---
        col = layout.column(align=True)
        col.label(text="Colors:")
        row = col.row(align=True)
        row.prop(scene, "bt_bad_color",     text="Bad")
        row = col.row(align=True)
        row.prop(scene, "bt_warning_color", text="Warning")

        layout.separator()

        # --- Кнопки Analyze / Clear ---
        row = layout.row(align=True)
        row.enabled = is_mesh
        row.scale_y = 1.3
        row.operator("object.dft_analyze_triangles",     text="Analyze", icon='HIDE_OFF')
        row.operator("object.dft_clear_triangle_colors", text="Clear",   icon='BRUSH_DATA')

        layout.separator()

        # --- Select Bad Triangles ---
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Select triangles:", icon='RESTRICT_SELECT_OFF')
        col.prop(scene, "bt_select_mode", text="")
        col.separator()
        row = col.row(align=True)
        row.enabled = is_mesh
        row.scale_y = 1.3
        row.operator("object.dft_select_bad_triangles", text="Select Triangles", icon='FACE_MAPS')

        # --- Результаты ---
        bad_count     = scene.bt_bad_count
        warning_count = scene.bt_warning_count

        if bad_count >= 0:
            layout.separator()
            box = layout.box()
            box.label(text="Last result:", icon='INFO')
            row = box.row()
            row.alert = bad_count > 0
            row.label(text=f"Bad:     {bad_count}", icon='ERROR' if bad_count > 0 else 'CHECKMARK')
            row = box.row()
            row.label(text=f"Warning: {warning_count}", icon='BLANK1')

        if not is_mesh:
            layout.separator()
            layout.label(text="Select a mesh object", icon='ERROR')


# ---------------------------------------------------------------------------
# Export panel (unchanged)
# ---------------------------------------------------------------------------

class DFT_PT_export_panel(bpy.types.Panel):
    bl_idname = "DFT_PT_export_panel"
    bl_label = "Export"
    bl_space_type = 'TOPBAR'
    bl_region_type = 'HEADER'
    bl_category = "DF FN Tools"

    bpy.types.Scene.export_folder = bpy.props.StringProperty(
        name="Path",
        description="Choose a directory to export Mesh(s)",
        maxlen=512,
        default=os.path.join("//", "Export"),
        subtype='DIR_PATH')

    bpy.types.Scene.reset_tramsforms = bpy.props.BoolProperty(
        name="Reset transforms",
        description="Resets transforms on exort",
        default=True)

    bpy.types.Scene.apply_material = bpy.props.BoolProperty(
        name="Apply single material",
        description="Apply one material for all the meshes",
        default=True)

    bpy.types.Scene.material_name = bpy.props.StringProperty(
        name="Material name",
        description="Set material name",
        maxlen=512,
        default="MAT")

    bpy.types.Scene.reassigne_materials = bpy.props.BoolProperty(
        name="Reassigne materials",
        description="Reassigne materials",
        default=False)

    bpy.types.Scene.export_with_related = bpy.props.BoolProperty(
        name="Export with LODs and UCX",
        description="Export with LODs and UCX",
        default=True)

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = self.layout.row()
        folder_path = row.column()
        folder_path.prop(scene, 'export_folder')

        col = self.layout.column()
        col.label(text="Settings:")
        col.prop(scene, 'reset_tramsforms')
        col.prop(scene, 'export_with_related')

        col.prop(scene, 'apply_material')
        col.prop(scene, 'material_name')

        col.prop(scene, 'reassigne_materials')

        if scene.reassigne_materials:
            box = layout.box()
            box.label(text="Reassign Materials:")
            for i in range(4):
                row_from = box.row()
                row_from.prop(scene, f"material_from_{i}", text="From")
                row_to = box.row()
                row_to.prop(scene, f"material_to_{i}", text="To")

        row = self.layout.row()
        row.operator("object.exportfbx_operator", text="Export")


# ---------------------------------------------------------------------------
# Topbar draw functions
# ---------------------------------------------------------------------------

def draw_popover(self, context):
    row = self.layout.row()
    row = row.row(align=True)

    # Export
    row.operator('object.exportfbx_operator', text='DF_FN_Export', icon='EXPORT')
    row.popover(panel='DFT_PT_export_panel', text='')
    row.operator('object.open_folder_operator', text='', icon='FILE_FOLDER')

    row.separator()

    # Bad Triangles
    row.popover(panel='DFT_PT_bad_triangles_panel', text='Bad Tris', icon='MESH_DATA')

    row.separator()

    # Vertex count
    obj = context.view_layer.objects.active
    count = context.scene.get("split_vertex_count", None)

    if obj and obj.type == 'MESH':
        if not any(p.use_smooth for p in obj.data.polygons):
            row.label(text="Set Shade Smooth for correct vertex count", icon='ERROR')
        elif count is not None and count >= 0:
            row.label(text=f" Vertex Count: {count}")
    elif count is not None and count >= 0:
        row.label(text=f" Vertex Count: {count}")
    else:
        row.label(text="Not a mesh")

    row.prop(context.scene, "auto_update_split_vertex_count", text="", icon='FILE_REFRESH', toggle=True)


def draw_object_context_menu(self, context):
    self.layout.operator("object.duplicate_clean_join", text="Clean Join", icon='MODIFIER')
    self.layout.operator("object.rename_uv", text="Rename UVs")
