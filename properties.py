import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    PointerProperty,
    EnumProperty,
)
from bpy.types import PropertyGroup

# --- Dynamic Enum Functions ---
def get_led_panel_items(self, context):
    """Dynamically creates EnumProperty items from the config file."""
    if hasattr(context.scene, 'hydroponics_config') and context.scene.hydroponics_config:
        panels = context.scene.hydroponics_config.get('led_panels', [])
        return [(str(i), panel['name'], "") for i, panel in enumerate(panels)]
    return []

# =================================================================================================
# ADDON PROPERTIES
# =================================================================================================
# (Your existing HydroponicsPotProperties, HydroponicsReservoirProperties, 
# HydroponicsPipeProperties, and HydroponicsLayoutProperties classes remain here, unchanged)

# Allow custom pot volumes
class HydroponicsPotProperties(PropertyGroup):
    volume_type: EnumProperty(
        name="Volume Type",
        items=[
            ('STANDARD', "Standard", "Use standard sizes"),
            ('CUSTOM', "Custom", "Custom volume")
        ],
        default='STANDARD'
    )
    
    custom_volume: FloatProperty(
        name="Custom Volume (L)",
        default=30.0,
        min=5.0,
        max=200.0
    )
    
    # Net pot size
    net_pot_diameter: FloatProperty(
        name="Net Pot Diameter (cm)",
        default=15.0,
        min=5.0,
        max=30.0
    )

class HydroponicsReservoirProperties(PropertyGroup):
    """Properties for the main reservoir."""
    volume: EnumProperty(
        name="Reservoir Volume",
        items=[('50.0', "50L", ""), ('75.0', "75L", ""), ('100.0', "100L", "")],
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
    pipe_height_ratio: FloatProperty(
        name="Pipe Height %",
        default=10.0,
        min=5.0,
        max=50.0,
        description="Height of pipes as % of pot height"
    )
    
    pipe_slope: FloatProperty(
        name="Pipe Slope (degrees)",
        default=0.0,
        min=-5.0,
        max=5.0,
        description="Slope for gravity flow"
    )
    
    manifold_type: EnumProperty(
        name="Manifold Type",
        items=[
            ('PARALLEL', "Parallel", "Traditional parallel manifolds"),
            ('LOOP', "Loop", "Continuous loop system"),
            ('HYBRID', "Hybrid", "Combination design")
        ],
        default='PARALLEL'
    )

class HydroponicsLayoutProperties(PropertyGroup):
    """Properties for the system layout."""
    rows: IntProperty(name="Rows", default=2, min=1, max=20)
    columns: IntProperty(name="Columns", default=2, min=1, max=20)
    spacing_x: FloatProperty(name="X Spacing", default=0.6, min=0.2, max=10.0, unit='LENGTH')
    spacing_y: FloatProperty(name="Y Spacing", default=0.6, min=0.2, max=10.0, unit='LENGTH')
    layout_type: EnumProperty(
        name="Layout Type",
        items=[
            ('GRID', "Grid", "Standard grid layout"),
            ('LINEAR', "Linear", "Single row layout"),
            ('CIRCULAR', "Circular", "Pots arranged in circle"),
            ('CUSTOM', "Custom", "Custom pot positions")
        ],
        default='GRID'
    )
    
    # For circular layouts
    circle_radius: FloatProperty(
        name="Circle Radius", 
        default=1.5, 
        min=0.5, 
        max=10.0
    )
class HydroponicsLightingProperties(PropertyGroup):
    """Properties for the lighting setup."""
    enable_lighting: BoolProperty(
        name="Generate Lighting System", 
        default=True,
        description="Enable or disable the generation of LED lighting panels"
    )
    plant_stage: EnumProperty(
        name="Growth Stage",
        items=[('vegetative', "Vegetative", ""), ('flowering', "Flowering", "")],
        default='flowering',
        description="Select the growth stage to calculate light requirements"
    )
    led_panel_type: EnumProperty(
        name="LED Panel",
        items=get_led_panel_items,
        description="Select the type of LED panel to use from the config file"
    )
    light_height: FloatProperty(
        name="Height From Canopy",
        default=0.4,
        min=0.1,
        max=3.0,
        unit='LENGTH',
        description="The vertical distance from the top of the pots to the lights"
    )

class HydroponicsSystemProperties(PropertyGroup):
    """Main property group to hold all system settings."""
    pot_props: PointerProperty(type=HydroponicsPotProperties)
    pipe_props: PointerProperty(type=HydroponicsPipeProperties)
    layout_props: PointerProperty(type=HydroponicsLayoutProperties)
    reservoir_props: PointerProperty(type=HydroponicsReservoirProperties)
    lighting_props: PointerProperty(type=HydroponicsLightingProperties) # Add this
    
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
    HydroponicsLightingProperties, # Add this
    HydroponicsSystemProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

class HydroponicsComponentProperties(PropertyGroup):
    # Pump configuration
    pump_count: IntProperty(
        name="Number of Pumps",
        default=1,
        min=1,
        max=4
    )
    
    pump_location: EnumProperty(
        name="Pump Location",
        items=[
            ('RESERVOIR', "In Reservoir", ""),
            ('INLINE', "Inline", ""),
            ('BOTH', "Both", "")
        ],
        default='RESERVOIR'
    )
    
    # Aeration
    air_stones_per_pot: IntProperty(
        name="Air Stones per Pot",
        default=1,
        min=0,
        max=4
    )
    
    # Valves and controls
    add_drain_valves: BoolProperty(
        name="Add Drain Valves",
        default=True
    )
    
    add_flow_indicators: BoolProperty(
        name="Add Flow Indicators",
        default=False
    )
    
    add_water_level_sensors: BoolProperty(
        name="Add Water Level Sensors",
        default=False
    )
    
class HydroponicsModularProperties(PropertyGroup):
    module_size: IntProperty(
        name="Pots per Module",
        default=4,
        min=2,
        max=8,
        description="Number of pots in each module"
    )
    
    connection_type: EnumProperty(
        name="Module Connection",
        items=[
            ('UNION', "Union Fitting", ""),
            ('FLANGE', "Flange", ""),
            ('QUICK', "Quick Connect", "")
        ],
        default='UNION'
    )