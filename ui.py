import bpy
import os


from bpy.types import (
    AddonPreferences,
    )

from bpy.props import (
    EnumProperty,
    )


# UI Tab for Export
class DFT_PT_export_panel(bpy.types.Panel):
    bl_idname = "DFT_PT_export_panel"
    bl_label = "Export"
    bl_space_type = 'TOPBAR'
    bl_region_type = 'HEADER'
    bl_category = "DF FN Tools"

    
    # Export path tab
    bpy.types.Scene.export_folder = bpy.props.StringProperty(
        name="Path",
        description="Choose a directory to export Mesh(s)",
        maxlen=512,
        default=os.path.join("//","Export"),
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
        default=("MAT"))
    

    bpy.types.Scene.reassigne_materials = bpy.props.BoolProperty(
        name="Reassigne materials",
        description="Reassigne materials", 
        default=False)
    


    def draw(self, context):
        scene = context.scene
        layout = self.layout
        
        row = self.layout.row()
        folder_path = row.column()
        folder_path.prop(scene, 'export_folder')
        
        col = self.layout.column()
        col.label(text="Settings:")
        col.prop(scene, 'reset_tramsforms')
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


def draw_popover(self, context):
    row = self.layout.row()
    row = row.row(align=True)
    row.operator('object.exportfbx_operator', text='DF_FN_Export', icon='EXPORT')
    row.popover(panel='DFT_PT_export_panel', text='')
    row.operator('object.open_folder_operator', text='', icon='FILE_FOLDER')

    row.separator()
    obj = context.view_layer.objects.active
    count = context.scene.get("split_vertex_count", None)

    if obj and obj.type == 'MESH':
        if not any(p.use_smooth for p in obj.data.polygons):
            row.label(text="Set Shade Smooth for correct vertex count", icon='ERROR')
        elif count >= 0:
            row.label(text=f" Vertex Count: {count}")
    elif count >= 0:
        row.label(text=f" Vertex Count: {count}")
    else:
        row.label(text="Not a mesh")


    row.prop(context.scene, "auto_update_split_vertex_count", text="", icon='FILE_REFRESH', toggle=True)