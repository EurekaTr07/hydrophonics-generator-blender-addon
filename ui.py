import bpy
from bpy.types import Panel

# =================================================================================================
# UI PANEL
# =================================================================================================

class VIEW3D_PT_hydroponics_generator(Panel):
    """Creates the main panel in the 3D Viewport."""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hydroponics"
    bl_label = "RDWC System Generator"

    def draw(self, context):
        layout = self.layout
        props = context.scene.hydroponics_props
        layout_props = props.layout_props
        pipe_props = props.pipe_props
        lighting_props = props.lighting_props # Add this

        # System Layout Box
        box = layout.box()
        box.label(text="System Layout", icon='GRID')
        row = box.row()
        row.prop(layout_props, "rows")
        row.prop(layout_props, "columns")
        box.prop(layout_props, "spacing_x")
        box.prop(layout_props, "spacing_y")

        # Pot Properties Box
        box = layout.box()
        box.label(text="Pot Properties", icon='CUBE')
        box.prop(props.pot_props, "volume")

        # Pipe Properties Box
        box = layout.box()
        box.label(text="Pipe Properties", icon='MOD_CURVE')
        box.prop(pipe_props, "pipe_standard")
        box.prop(pipe_props, "pipe_size")
        
        # --- NEW: Lighting System Box ---
        box = layout.box()
        box.label(text="Lighting System", icon='LIGHT')
        box.prop(lighting_props, "enable_lighting")
        
        if lighting_props.enable_lighting:
            box.prop(lighting_props, "plant_stage")
            box.prop(lighting_props, "led_panel_type")
            box.prop(lighting_props, "light_height")

        # Main Reservoir Box
        box = layout.box()
        box.label(text="Main Reservoir", icon='MOD_FLUID')
        box.prop(props, "enable_reservoir")
        if props.enable_reservoir:
            box.prop(props.reservoir_props, "volume")

        layout.separator()
        box = layout.box()
        box.label(text="Generation Options", icon='SETTINGS')
        box.prop(props, "create_connections")
        if props.create_connections:
            box.prop(props, "optimize_model")

        layout.separator()
        layout.operator("wm.hydroponics_generator", text="Generate System", icon='MOD_BUILD')

classes = (
    VIEW3D_PT_hydroponics_generator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)