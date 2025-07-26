import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    PointerProperty,
    EnumProperty,
)
from bpy.types import PropertyGroup

# =================================================================================================
# ADDON PROPERTIES
# =================================================================================================

class HydroponicsPotProperties(PropertyGroup):
    """Properties for the hydroponic pots."""
    volume: EnumProperty(
        name="Bucket Volume",
        items=[('10.0', "10L", ""), ('19.0', "19L", ""), ('25.0', "25L", "")],
        default='25.0'
    )

class HydroponicsReservoirProperties(PropertyGroup):
    """Properties for the main reservoir."""
    volume: EnumProperty(
        name="Reservoir Volume",
        items=[('50.0', "50L", ""), ('75.0', "75L", ""), ('100.0', "100L", ""), ('150.0', "150L", ""), ('200.0', "200L", "")],
        default='75.0'
    )

def get_pipe_sizes(self, context):
    """Dynamically returns pipe sizes based on the selected standard."""
    if self.pipe_standard == 'TR':
        return [('20', "20mm", ""), ('25', "25mm", ""), ('32', "32mm", ""), ('50', "50mm", "")]
    else:  # METRIC
        return [('15', "15mm", ""), ('20', "20mm", ""), ('25', "25mm", ""), ('40', "40mm", ""), ('50', "50mm", "")]

class HydroponicsPipeProperties(PropertyGroup):
    """Properties for the pipes."""
    pipe_standard: EnumProperty(
        name="Pipe Standard",
        items=[('TR', "Turkish PVC (mm)", ""), ('METRIC', "Metric (mm)", "")],
        default='TR',
        description="Select the pipe standard to use"
    )
    pipe_size: EnumProperty(
        name="Pipe Diameter",
        items=get_pipe_sizes,
        description="Select the pipe diameter based on the chosen standard"
    )

def update_reservoir_volume(self, context):
    """Automatically adjusts reservoir size based on the number of plants."""
    props = context.scene.hydroponics_props
    layout = props.layout_props
    reservoir = props.reservoir_props
    
    num_plants = layout.rows * layout.columns
    # Assuming a requirement of 10 liters per plant
    required_volume = num_plants * 10.0
    
    # Available reservoir sizes (must match the EnumProperty items)
    available_sizes = [50.0, 75.0, 100.0, 150.0, 200.0]
    
    # Find the smallest available size that fits the requirement
    best_size = available_sizes[-1] # Default to largest if none fit
    for size in available_sizes:
        if size >= required_volume:
            best_size = size
            break
    
    # Set the volume property. EnumProperty values are strings.
    # Use f-string to format to one decimal place to match the enum identifiers.
    reservoir.volume = f"{best_size:.1f}"

class HydroponicsLayoutProperties(PropertyGroup):
    """Properties for the system layout."""
    rows: IntProperty(name="Rows", default=2, min=1, max=20, update=update_reservoir_volume)
    columns: IntProperty(name="Columns", default=2, min=1, max=20, update=update_reservoir_volume)
    spacing_x: FloatProperty(name="X Spacing", default=0.6, min=0.2, max=10.0, unit='LENGTH')
    spacing_y: FloatProperty(name="Y Spacing", default=0.6, min=0.2, max=10.0, unit='LENGTH')

class HydroponicsSystemProperties(PropertyGroup):
    """Main property group to hold all system settings."""
    pot_props: PointerProperty(type=HydroponicsPotProperties)
    pipe_props: PointerProperty(type=HydroponicsPipeProperties)
    layout_props: PointerProperty(type=HydroponicsLayoutProperties)
    reservoir_props: PointerProperty(type=HydroponicsReservoirProperties)
    enable_reservoir: BoolProperty(name="Enable Reservoir", default=True)
    create_connections: BoolProperty(name="Join Pipe Connections", default=True)
    optimize_model: BoolProperty(
        name="Optimize Model",
        default=True,
        description="Cleans up geometry and improves performance after generation"
    )

# List of classes to register
classes = (
    HydroponicsPotProperties,
    HydroponicsReservoirProperties,
    HydroponicsPipeProperties,
    HydroponicsLayoutProperties,
    HydroponicsSystemProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
