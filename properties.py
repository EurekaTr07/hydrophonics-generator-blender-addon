import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    PointerProperty,
    EnumProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

# =================================================================================================
# DYNAMIC ENUM FUNCTIONS
# =================================================================================================

def get_led_panel_items(self, context):
    """Dynamically creates EnumProperty items from the config file."""
    if hasattr(context.scene, 'hydroponics_config') and context.scene.hydroponics_config:
        panels = context.scene.hydroponics_config.get('led_panels', [])
        return [(str(i), panel['name'], "") for i, panel in enumerate(panels)]
    return [('0', "Default LED Panel", "")]

def get_pipe_sizes(self, context):
    """Dynamically returns pipe sizes based on the selected standard."""
    if self.pipe_standard == 'TR':
        return [('20', "20mm", ""), ('25', "25mm", ""), ('32', "32mm", ""), ('50', "50mm", "")]
    else:  # METRIC
        return [('15', "15mm", ""), ('20', "20mm", ""), ('25', "25mm", ""), ('40', "40mm", ""), ('50', "50mm", "")]

# =================================================================================================
# ADDON PROPERTIES
# =================================================================================================

class HydroponicsPotProperties(PropertyGroup):
    """Properties for the hydroponic pots/buckets."""
    # Volume selection
    volume_type: EnumProperty(
        name="Volume Type",
        items=[
            ('STANDARD', "Standard", "Use standard sizes"),
            ('CUSTOM', "Custom", "Custom volume")
        ],
        default='STANDARD',
        description="Choose between standard or custom pot volumes"
    )
    
    # Standard volumes
    volume: EnumProperty(
        name="Bucket Volume",
        items=[
            ('10.0', "10L", "Small bucket"),
            ('19.0', "19L", "Medium bucket"),
            ('25.0', "25L", "Large bucket"),
            ('30.0', "30L", "Extra large bucket")
        ],
        default='25.0',
        description="Select standard bucket volume"
    )
    
    # Custom volume
    custom_volume: FloatProperty(
        name="Custom Volume (L)",
        default=30.0,
        min=5.0,
        max=200.0,
        description="Set custom bucket volume in liters"
    )
    
    # Net pot configuration
    net_pot_diameter: FloatProperty(
        name="Net Pot Diameter (cm)",
        default=15.0,
        min=5.0,
        max=30.0,
        description="Diameter of net pot holder"
    )
    
    add_net_pot: BoolProperty(
        name="Add Net Pot Holder",
        default=True,
        description="Include net pot holder in bucket lid"
    )
    
    # Pot shape
    pot_shape: EnumProperty(
        name="Pot Shape",
        items=[
            ('ROUND', "Round", "Cylindrical bucket"),
            ('SQUARE', "Square", "Square bucket"),
            ('RECTANGULAR', "Rectangular", "Rectangular container")
        ],
        default='ROUND',
        description="Shape of the growing container"
    )


class HydroponicsReservoirProperties(PropertyGroup):
    """Properties for the main reservoir."""
    # Volume selection
    volume_type: EnumProperty(
        name="Volume Type",
        items=[
            ('STANDARD', "Standard", "Use standard sizes"),
            ('CUSTOM', "Custom", "Custom volume")
        ],
        default='STANDARD'
    )
    
    volume: EnumProperty(
        name="Reservoir Volume",
        items=[
            ('50.0', "50L", "Small reservoir"),
            ('75.0', "75L", "Medium reservoir"),
            ('100.0', "100L", "Large reservoir"),
            ('150.0', "150L", "Extra large reservoir"),
            ('200.0', "200L", "Industrial reservoir")
        ],
        default='100.0'
    )
    
    custom_volume: FloatProperty(
        name="Custom Volume (L)",
        default=100.0,
        min=25.0,
        max=1000.0
    )
    
    # Reservoir features
    add_lid: BoolProperty(
        name="Add Lid",
        default=True,
        description="Include removable lid on reservoir"
    )
    
    add_sight_glass: BoolProperty(
        name="Add Sight Glass",
        default=False,
        description="Include water level sight glass"
    )
    
    add_drain_port: BoolProperty(
        name="Add Drain Port",
        default=True,
        description="Include bottom drain port"
    )


class HydroponicsPipeProperties(PropertyGroup):
    """Properties for the piping system."""
    pipe_standard: EnumProperty(
        name="Pipe Standard",
        items=[
            ('TR', "Turkish PVC (mm)", "Turkish standard PVC sizes"),
            ('METRIC', "Metric (mm)", "Metric pipe sizes"),
            ('IMPERIAL', "Imperial (inches)", "US standard sizes")
        ],
        default='METRIC',
        description="Select the pipe standard to use"
    )
    
    pipe_size: EnumProperty(
        name="Pipe Diameter",
        items=get_pipe_sizes,
        description="Select the pipe diameter based on the chosen standard"
    )
    
    pipe_height_ratio: FloatProperty(
        name="Pipe Height %",
        default=15.0,
        min=5.0,
        max=50.0,
        description="Height of pipes as % of pot height"
    )
    
    pipe_slope: FloatProperty(
        name="Pipe Slope (degrees)",
        default=1.0,
        min=-5.0,
        max=5.0,
        description="Slope for gravity flow (positive = downward)"
    )
    
    manifold_type: EnumProperty(
        name="Manifold Type",
        items=[
            ('PARALLEL', "Parallel", "Traditional parallel inlet/outlet manifolds"),
            ('LOOP', "Loop", "Continuous loop system"),
            ('RDWC', "RDWC", "Recirculating DWC with manifolds"),
            ('HYBRID', "Hybrid", "Custom combination design")
        ],
        default='RDWC'
    )
    
    use_elbows: BoolProperty(
        name="Use Elbow Fittings",
        default=True,
        description="Use elbow fittings for cleaner pipe routing"
    )
    
    pipe_material: EnumProperty(
        name="Pipe Material",
        items=[
            ('PVC', "PVC", "Polyvinyl chloride"),
            ('ABS', "ABS", "Acrylonitrile butadiene styrene"),
            ('PP', "PP", "Polypropylene"),
            ('PE', "PE", "Polyethylene")
        ],
        default='PVC',
        description="Pipe material for cost calculation"
    )


class HydroponicsLayoutProperties(PropertyGroup):
    """Properties for the system layout."""
    layout_type: EnumProperty(
        name="Layout Type",
        items=[
            ('GRID', "Grid", "Standard grid layout"),
            ('LINEAR', "Linear", "Single row layout"),
            ('CIRCULAR', "Circular", "Pots arranged in circle"),
            ('STAGGERED', "Staggered", "Offset grid pattern"),
            ('CUSTOM', "Custom", "Custom pot positions")
        ],
        default='GRID'
    )
    
    # Grid properties
    rows: IntProperty(
        name="Rows",
        default=2,
        min=1,
        max=20,
        description="Number of rows in grid"
    )
    
    columns: IntProperty(
        name="Columns",
        default=2,
        min=1,
        max=20,
        description="Number of columns in grid"
    )
    
    spacing_x: FloatProperty(
        name="X Spacing",
        default=0.6,
        min=0.2,
        max=10.0,
        unit='LENGTH',
        description="Distance between pot centers (X axis)"
    )
    
    spacing_y: FloatProperty(
        name="Y Spacing",
        default=0.6,
        min=0.2,
        max=10.0,
        unit='LENGTH',
        description="Distance between pot centers (Y axis)"
    )
    
    # Circular layout properties
    circle_radius: FloatProperty(
        name="Circle Radius",
        default=1.5,
        min=0.5,
        max=10.0,
        unit='LENGTH',
        description="Radius of circular arrangement"
    )
    
    # Staggered layout
    stagger_offset: FloatProperty(
        name="Stagger Offset %",
        default=50.0,
        min=0.0,
        max=100.0,
        description="Offset percentage for staggered rows"
    )


class HydroponicsComponentProperties(PropertyGroup):
    """Properties for system components."""
    # Pump configuration
    pump_count: IntProperty(
        name="Number of Pumps",
        default=1,
        min=1,
        max=4,
        description="Total number of water pumps"
    )
    
    pump_type: EnumProperty(
        name="Pump Type",
        items=[
            ('SUBMERSIBLE', "Submersible", "Submersible water pump"),
            ('INLINE', "Inline", "External inline pump"),
            ('BOTH', "Mixed", "Both types")
        ],
        default='SUBMERSIBLE'
    )
    
    pump_flow_rate: FloatProperty(
        name="Pump Flow Rate (L/h)",
        default=1000.0,
        min=100.0,
        max=10000.0,
        description="Pump flow rate in liters per hour"
    )
    
    # Aeration system
    enable_aeration: BoolProperty(
        name="Enable Aeration System",
        default=True,
        description="Include air pump and air stones"
    )
    
    air_pump_outlets: IntProperty(
        name="Air Pump Outlets",
        default=4,
        min=1,
        max=12,
        description="Number of air pump outlets"
    )
    
    air_stones_per_pot: IntProperty(
        name="Air Stones per Pot",
        default=1,
        min=0,
        max=4,
        description="Number of air stones in each pot"
    )
    
    air_stone_type: EnumProperty(
        name="Air Stone Type",
        items=[
            ('CYLINDER', "Cylinder", "Cylindrical air stone"),
            ('DISK', "Disk", "Flat disk air stone"),
            ('BALL', "Ball", "Spherical air stone"),
            ('BAR', "Bar", "Long bar air stone")
        ],
        default='CYLINDER'
    )
    
    # Valves and controls
    add_drain_valves: BoolProperty(
        name="Add Drain Valves",
        default=True,
        description="Add valves for draining pots"
    )
    
    add_check_valves: BoolProperty(
        name="Add Check Valves",
        default=False,
        description="Add one-way check valves"
    )
    
    add_flow_indicators: BoolProperty(
        name="Add Flow Meters",
        default=False,
        description="Add flow rate indicators"
    )
    
    add_water_level_sensors: BoolProperty(
        name="Add Water Level Sensors",
        default=True,
        description="Add water level monitoring"
    )
    
    # Connections
    use_unions: BoolProperty(
        name="Use Union Fittings",
        default=False,
        description="Add unions for easy disassembly"
    )
    
    use_quick_connects: BoolProperty(
        name="Use Quick Connects",
        default=False,
        description="Use quick-connect fittings"
    )
    
    # Monitoring
    add_probe_holders: BoolProperty(
        name="Add Probe Holders",
        default=True,
        description="Include pH/EC probe holders"
    )
    
    probe_count: IntProperty(
        name="Number of Probes",
        default=2,
        min=1,
        max=6,
        description="Number of monitoring probes"
    )


class HydroponicsModularProperties(PropertyGroup):
    """Properties for modular system design."""
    enable_modular: BoolProperty(
        name="Enable Modular Design",
        default=False,
        description="Design system as connected modules"
    )
    
    module_size: IntProperty(
        name="Pots per Module",
        default=4,
        min=2,
        max=8,
        description="Number of pots in each module"
    )
    
    module_connection: EnumProperty(
        name="Module Connection",
        items=[
            ('UNION', "Union Fitting", "Threaded union connections"),
            ('FLANGE', "Flange", "Bolted flange connections"),
            ('QUICK', "Quick Connect", "Quick-disconnect couplings"),
            ('FLEXIBLE', "Flexible", "Flexible hose connections")
        ],
        default='UNION'
    )
    
    independent_modules: BoolProperty(
        name="Independent Modules",
        default=False,
        description="Each module can operate independently"
    )


class HydroponicsLightingProperties(PropertyGroup):
    """Properties for the lighting system."""
    enable_lighting: BoolProperty(
        name="Generate Lighting System",
        default=True,
        description="Include LED lighting panels"
    )
    
    light_type: EnumProperty(
        name="Light Type",
        items=[
            ('LED_PANEL', "LED Panel", "Flat LED panels"),
            ('LED_BAR', "LED Bar", "Linear LED bars"),
            ('LED_COB', "COB LED", "Chip-on-board LEDs"),
            ('HPS', "HPS", "High pressure sodium"),
            ('CMH', "CMH", "Ceramic metal halide")
        ],
        default='LED_PANEL'
    )
    
    plant_stage: EnumProperty(
        name="Growth Stage",
        items=[
            ('seedling', "Seedling", "Young seedlings"),
            ('vegetative', "Vegetative", "Vegetative growth"),
            ('flowering', "Flowering", "Flowering/fruiting"),
            ('mother', "Mother Plant", "Mother plants")
        ],
        default='vegetative',
        description="Plant growth stage for light calculation"
    )
    
    led_panel_type: EnumProperty(
        name="LED Panel Model",
        items=get_led_panel_items,
        description="Select LED panel from config"
    )
    
    light_height: FloatProperty(
        name="Height Above Canopy",
        default=0.6,
        min=0.1,
        max=3.0,
        unit='LENGTH',
        description="Distance from canopy to lights"
    )
    
    light_coverage: FloatProperty(
        name="Coverage Overlap %",
        default=10.0,
        min=0.0,
        max=50.0,
        description="Light coverage overlap percentage"
    )
    
    add_light_movers: BoolProperty(
        name="Add Light Movers",
        default=False,
        description="Include light moving rails"
    )
    
    add_reflectors: BoolProperty(
        name="Add Reflectors",
        default=False,
        description="Include reflective walls/surfaces"
    )


class HydroponicsAdvancedProperties(PropertyGroup):
    """Advanced system properties."""
    # Climate control
    add_fans: BoolProperty(
        name="Add Ventilation Fans",
        default=False,
        description="Include circulation fans"
    )
    
    fan_count: IntProperty(
        name="Number of Fans",
        default=2,
        min=1,
        max=10
    )
    
    # Automation
    add_dosing_pumps: BoolProperty(
        name="Add Dosing Pumps",
        default=False,
        description="Include nutrient dosing pumps"
    )
    
    dosing_pump_count: IntProperty(
        name="Dosing Pump Count",
        default=3,
        min=1,
        max=8
    )
    
    # Support structures
    add_support_frame: BoolProperty(
        name="Add Support Frame",
        default=False,
        description="Include structural support frame"
    )
    
    frame_material: EnumProperty(
        name="Frame Material",
        items=[
            ('ALUMINUM', "Aluminum", "Aluminum extrusion"),
            ('STEEL', "Steel", "Steel tubing"),
            ('PVC', "PVC", "PVC frame")
        ],
        default='ALUMINUM'
    )
    
    # Extras
    add_drain_table: BoolProperty(
        name="Add Drain Table",
        default=False,
        description="Include drainage collection table"
    )
    
    add_work_reservoir: BoolProperty(
        name="Add Work Reservoir",
        default=False,
        description="Include separate mixing reservoir"
    )


class HydroponicsSystemProperties(PropertyGroup):
    """Main property group holding all system settings."""
    # Sub-property groups
    pot_props: PointerProperty(type=HydroponicsPotProperties)
    pipe_props: PointerProperty(type=HydroponicsPipeProperties)
    layout_props: PointerProperty(type=HydroponicsLayoutProperties)
    reservoir_props: PointerProperty(type=HydroponicsReservoirProperties)
    component_props: PointerProperty(type=HydroponicsComponentProperties)
    modular_props: PointerProperty(type=HydroponicsModularProperties)
    lighting_props: PointerProperty(type=HydroponicsLightingProperties)
    advanced_props: PointerProperty(type=HydroponicsAdvancedProperties)
    
    # Main system toggles
    enable_reservoir: BoolProperty(
        name="Enable Main Reservoir",
        default=True,
        description="Include main water reservoir"
    )
    
    enable_balance_tank: BoolProperty(
        name="Enable Balance Tank",
        default=True,
        description="Include balance/buffer tank"
    )
    
    create_connections: BoolProperty(
        name="Join Pipe Connections",
        default=True,
        description="Merge pipes into single object"
    )
    
    optimize_model: BoolProperty(
        name="Optimize Model",
        default=True,
        description="Clean and optimize final geometry"
    )
    
    # System type presets
    system_preset: EnumProperty(
        name="System Preset",
        items=[
            ('CUSTOM', "Custom", "Manual configuration"),
            ('HOBBY', "Hobby", "Small hobby system"),
            ('COMMERCIAL', "Commercial", "Commercial setup"),
            ('RESEARCH', "Research", "Research configuration")
        ],
        default='CUSTOM',
        description="Load predefined system configuration"
    )
    
    # Export settings
    export_stats: BoolProperty(
        name="Generate Statistics",
        default=False,
        description="Calculate system statistics"
    )
    
    export_bom: BoolProperty(
        name="Generate BOM",
        default=False,
        description="Generate bill of materials"
    )


# List of classes to register
classes = (
    HydroponicsPotProperties,
    HydroponicsReservoirProperties,
    HydroponicsPipeProperties,
    HydroponicsLayoutProperties,
    HydroponicsComponentProperties,
    HydroponicsModularProperties,
    HydroponicsLightingProperties,
    HydroponicsAdvancedProperties,
    HydroponicsSystemProperties,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)