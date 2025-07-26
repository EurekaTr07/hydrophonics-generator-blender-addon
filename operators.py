import bpy
import math
from math import ceil, sin, cos
from mathutils import Vector, Matrix
from . import mesh_creator
from bpy.types import Operator

def get_total_bounding_box(objects):
    """
    Calculates the combined bounding box of multiple objects to determine the overall system size.
    """
    if not objects:
        return None, None

    min_coord = Vector((float('inf'), float('inf'), float('inf')))
    max_coord = Vector((float('-inf'), float('-inf'), float('-inf')))

    for obj in objects:
        bpy.context.view_layer.update()
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            min_coord.x = min(min_coord.x, world_corner.x)
            min_coord.y = min(min_coord.y, world_corner.y)
            min_coord.z = min(min_coord.z, world_corner.z)
            max_coord.x = max(max_coord.x, world_corner.x)
            max_coord.y = max(max_coord.y, world_corner.y)
            max_coord.z = max(max_coord.z, world_corner.z)
    
    return min_coord, max_coord

class WM_OT_hydroponics_generator(Operator):
    """Main operator to generate the entire RDWC system with all components."""
    bl_idname = "wm.hydroponics_generator"
    bl_label = "Generate System"
    bl_options = {'REGISTER', 'UNDO'}

    def _clear_previous(self):
        """Removes all previously generated objects and collections to start fresh."""
        collection_names = ["Pots", "Pipes", "Fittings", "System", "Lighting", "Components", 
                          "Pumps", "Aeration", "Sensors", "Valves"]
        for col_name in collection_names:
            if col_name in bpy.data.collections:
                collection = bpy.data.collections[col_name]
                for obj in list(collection.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(collection)

    def _calculate_pot_positions(self, layout):
        """Calculate pot positions based on layout type."""
        positions = []
        
        if layout.layout_type == 'GRID':
            for r in range(layout.rows):
                for c in range(layout.columns):
                    positions.append(Vector((c * layout.spacing_x, r * layout.spacing_y, 0)))
                    
        elif layout.layout_type == 'LINEAR':
            for i in range(layout.columns):
                positions.append(Vector((i * layout.spacing_x, 0, 0)))
                
        elif layout.layout_type == 'CIRCULAR':
            num_pots = layout.rows * layout.columns  # Total pots
            angle_step = 2 * math.pi / num_pots
            for i in range(num_pots):
                angle = i * angle_step
                x = layout.circle_radius * cos(angle)
                y = layout.circle_radius * sin(angle)
                positions.append(Vector((x, y, 0)))
                
        return positions

    def _calculate_pipe_height(self, base_height, pipe_props, distance_from_center=0):
        """Calculate pipe Z position with optional slope."""
        z = base_height * (pipe_props.pipe_height_ratio / 100.0)
        
        # Apply slope if specified
        if hasattr(pipe_props, 'pipe_slope') and pipe_props.pipe_slope != 0:
            slope_rad = math.radians(pipe_props.pipe_slope)
            z += distance_from_center * math.tan(slope_rad)
            
        return z

    def _generate_grid_manifold(self, context, generators, collections, dimensions):
        """Generates manifold system for grid layout with proper fittings."""
        layout = context.scene.hydroponics_props.layout_props
        pipe_props = context.scene.hydroponics_props.pipe_props
        pot_gen, pipe_gen, tee_gen, elbow_gen, valve_gen, union_gen = generators[:6]
        pots_collection, pipes_collection, fittings_collection, valves_collection = collections[:4]
        pot_volume, pot_height, pot_radius, base_pipe_z, tee_arm_total_length, pipe_insertion_depth, manifold_y_in, manifold_y_out = dimensions

        pot_objects = []  # Store pot objects for air stone placement later

        # Generate manifold T-fittings and connecting pipes
        for c in range(layout.columns):
            loc_x = c * layout.spacing_x
            pipe_z = self._calculate_pipe_height(pot_height, pipe_props, loc_x - (layout.columns-1)*layout.spacing_x/2)
            
            # Create T-fittings for inlet and outlet manifolds
            tee_in = tee_gen.create(f"Tee_Inlet_{c}", Vector((loc_x, manifold_y_in, pipe_z)), (0, 0, math.radians(180)))
            tee_out = tee_gen.create(f"Tee_Outlet_{c}", Vector((loc_x, manifold_y_out, pipe_z)), (0, 0, 0))
            tee_gen._link_to_collection(tee_in, fittings_collection)
            tee_gen._link_to_collection(tee_out, fittings_collection)
            
            # Connect manifold segments between T-fittings
            if c > 0:
                prev_loc_x = (c - 1) * layout.spacing_x
                prev_pipe_z = self._calculate_pipe_height(pot_height, pipe_props, prev_loc_x - (layout.columns-1)*layout.spacing_x/2)
                
                pipe_start_x = prev_loc_x + tee_arm_total_length - pipe_insertion_depth
                pipe_end_x = loc_x - tee_arm_total_length + pipe_insertion_depth
                
                # Add unions at mid-points for modular connections
                if hasattr(context.scene.hydroponics_props, 'component_props') and context.scene.hydroponics_props.component_props.use_unions:
                    mid_x = (pipe_start_x + pipe_end_x) / 2
                    mid_z = (prev_pipe_z + pipe_z) / 2
                    
                    # Inlet manifold union
                    union_in = union_gen.create(f"Union_In_{c-1}", Vector((mid_x, manifold_y_in, mid_z)), (0, math.radians(90), 0))
                    union_gen._link_to_collection(union_in, fittings_collection)
                    
                    # Split pipe into two segments
                    pipe_in1 = pipe_gen.create(f"Manifold_Pipe_In_{c-1}_1", 
                        Vector((pipe_start_x, manifold_y_in, prev_pipe_z)), 
                        Vector((mid_x - 0.02, manifold_y_in, mid_z)))
                    pipe_in2 = pipe_gen.create(f"Manifold_Pipe_In_{c-1}_2", 
                        Vector((mid_x + 0.02, manifold_y_in, mid_z)), 
                        Vector((pipe_end_x, manifold_y_in, pipe_z)))
                    
                    # Outlet manifold union
                    union_out = union_gen.create(f"Union_Out_{c-1}", Vector((mid_x, manifold_y_out, mid_z)), (0, math.radians(90), 0))
                    union_gen._link_to_collection(union_out, fittings_collection)
                    
                    pipe_out1 = pipe_gen.create(f"Manifold_Pipe_Out_{c-1}_1", 
                        Vector((pipe_start_x, manifold_y_out, prev_pipe_z)), 
                        Vector((mid_x - 0.02, manifold_y_out, mid_z)))
                    pipe_out2 = pipe_gen.create(f"Manifold_Pipe_Out_{c-1}_2", 
                        Vector((mid_x + 0.02, manifold_y_out, mid_z)), 
                        Vector((pipe_end_x, manifold_y_out, pipe_z)))
                else:
                    # Single continuous pipes
                    pipe_in1 = pipe_gen.create(f"Manifold_Pipe_In_{c-1}", 
                        Vector((pipe_start_x, manifold_y_in, prev_pipe_z)), 
                        Vector((pipe_end_x, manifold_y_in, pipe_z)))
                    pipe_out1 = pipe_gen.create(f"Manifold_Pipe_Out_{c-1}", 
                        Vector((pipe_start_x, manifold_y_out, prev_pipe_z)), 
                        Vector((pipe_end_x, manifold_y_out, pipe_z)))
                    pipe_in2 = pipe_out2 = None
                
                for pipe in [pipe_in1, pipe_in2, pipe_out1, pipe_out2]:
                    if pipe:
                        pipe_gen._link_to_collection(pipe, pipes_collection)

        # Generate pots and connect them
        for r in range(layout.rows):
            for c in range(layout.columns):
                loc_x, loc_y = c * layout.spacing_x, r * layout.spacing_y
                pipe_z = self._calculate_pipe_height(pot_height, pipe_props, loc_x - (layout.columns-1)*layout.spacing_x/2)
                
                # Create pot with net pot holder
                pot_obj, _, pot_rad_actual = pot_gen.create(
                    f"Pot_{r}_{c}", 
                    Vector((loc_x, loc_y, pot_height / 2.0)), 
                    pot_volume,
                    add_net_pot=True
                )
                pot_gen._link_to_collection(pot_obj, pots_collection)
                pot_objects.append((pot_obj, loc_x, loc_y, pot_height, pot_rad_actual))
                
                # Add valves at pot connections if enabled
                if hasattr(context.scene.hydroponics_props, 'component_props') and context.scene.hydroponics_props.component_props.add_drain_valves:
                    # Inlet valve
                    valve_in_loc = Vector((loc_x, manifold_y_in - tee_arm_total_length + pipe_insertion_depth - 0.05, pipe_z))
                    valve_in = valve_gen.create(f"Valve_In_{r}_{c}", valve_in_loc, (0, 0, 0))
                    valve_gen._link_to_collection(valve_in, valves_collection)
                    
                    # Pipes around valve
                    pipe_to_valve = pipe_gen.create(f"Pipe_to_valve_in_{r}_{c}",
                        Vector((loc_x, manifold_y_in - tee_arm_total_length + pipe_insertion_depth, pipe_z)),
                        valve_in_loc + Vector((0, -0.04, 0)))
                    pipe_from_valve = pipe_gen.create(f"Pipe_from_valve_in_{r}_{c}",
                        valve_in_loc + Vector((0, 0.04, 0)),
                        Vector((loc_x, loc_y + pot_rad_actual, pipe_z)))
                else:
                    # Direct pipe connection
                    pipe_to_valve = pipe_gen.create(f"Pot_Pipe_In_{r}_{c}",
                        Vector((loc_x, manifold_y_in - tee_arm_total_length + pipe_insertion_depth, pipe_z)),
                        Vector((loc_x, loc_y + pot_rad_actual, pipe_z)))
                    pipe_from_valve = None
                
                # Outlet pipe (always direct for now)
                pipe_out = pipe_gen.create(f"Pot_Pipe_Out_{r}_{c}",
                    Vector((loc_x, loc_y - pot_rad_actual, pipe_z)),
                    Vector((loc_x, manifold_y_out + tee_arm_total_length - pipe_insertion_depth, pipe_z)))
                
                for pipe in [pipe_to_valve, pipe_from_valve, pipe_out]:
                    if pipe:
                        pipe_gen._link_to_collection(pipe, pipes_collection)

        return pot_objects

    def _generate_circular_layout(self, context, generators, collections, dimensions):
        """Generates circular layout with central manifold."""
        layout = context.scene.hydroponics_props.layout_props
        pipe_props = context.scene.hydroponics_props.pipe_props
        pot_gen, pipe_gen, tee_gen, elbow_gen, valve_gen = generators[:5]
        pots_collection, pipes_collection, fittings_collection = collections[:3]
        pot_volume, pot_height, pot_radius, base_pipe_z, _, _, _, _ = dimensions
        
        positions = self._calculate_pot_positions(layout)
        pipe_z = self._calculate_pipe_height(pot_height, pipe_props)
        pot_objects = []
        
        # Create central manifold using custom manifold block
        if hasattr(mesh_creator, 'ManifoldBlockMesh'):
            manifold_gen = mesh_creator.ManifoldBlockMesh(context.scene.hydroponics_props)
            central_manifold = manifold_gen.create(
                "Central_Manifold", 
                Vector((0, 0, pipe_z)), 
                num_outlets=len(positions)
            )
            manifold_gen._link_to_collection(central_manifold, fittings_collection)
        
        # Generate pots and radial connections
        for i, pos in enumerate(positions):
            # Create pot
            pot_obj, _, pot_rad_actual = pot_gen.create(
                f"Pot_circular_{i}",
                pos + Vector((0, 0, pot_height / 2.0)),
                pot_volume,
                add_net_pot=True
            )
            pot_gen._link_to_collection(pot_obj, pots_collection)
            pot_objects.append((pot_obj, pos.x, pos.y, pot_height, pot_rad_actual))
            
            # Calculate connection angle
            angle = math.atan2(pos.y, pos.x)
            
            # Create elbow at pot for clean connection
            elbow_pos = pos + Vector((cos(angle) * pot_rad_actual, sin(angle) * pot_rad_actual, pipe_z))
            elbow = elbow_gen.create(f"Elbow_circular_{i}", elbow_pos, (0, 0, angle))
            elbow_gen._link_to_collection(elbow, fittings_collection)
            
            # Create radial pipe from center to pot
            pipe_radial = pipe_gen.create(
                f"Pipe_radial_{i}",
                Vector((0, 0, pipe_z)),
                elbow_pos
            )
            pipe_gen._link_to_collection(pipe_radial, pipes_collection)
        
        return pot_objects

    def _generate_reservoir_system(self, context, generators, collections, dimensions):
        """Generates the main reservoir with pump and related components."""
        scene_props = context.scene.hydroponics_props
        layout = scene_props.layout_props
        pipe_props = scene_props.pipe_props
        pot_gen, pipe_gen, _, _, valve_gen, _, pump_gen, bulkhead_gen = generators[:8]
        pots_collection, pipes_collection, _, _, pumps_collection, sensors_collection = collections[:6]
        _, pot_height, _, _, _, _, manifold_y_in, manifold_y_out = dimensions
        
        reservoir_volume = float(scene_props.reservoir_props.volume)
        
        # Position reservoir based on layout type
        if layout.layout_type == 'CIRCULAR':
            reservoir_loc = Vector((0, -layout.circle_radius * 1.5, 0))
        else:
            grid_width = (layout.columns - 1) * layout.spacing_x
            reservoir_loc = Vector((grid_width / 2.0, manifold_y_out - layout.spacing_y * 1.5, 0))
        
        # Create reservoir with ports
        reservoir_gen = mesh_creator.ReservoirMesh(scene_props)
        res_obj, res_h, res_rad = reservoir_gen.create("Main_Reservoir", reservoir_loc, reservoir_volume, add_ports=True)
        res_obj.location.z = res_h / 2.0
        reservoir_gen._link_to_collection(res_obj, pots_collection)
        
        # Add submersible pump inside reservoir
        pump_loc = reservoir_loc + Vector((0, 0, -res_h/2 + 0.1))
        pump = pump_gen.create("Main_Pump", pump_loc, pump_type='submersible')
        pump_gen._link_to_collection(pump, pumps_collection)
        
        # Add bulkhead fitting for pump outlet
        bulkhead_loc = reservoir_loc + Vector((res_rad * 0.7, 0, -res_h/4))
        bulkhead = bulkhead_gen.create("Pump_Bulkhead", bulkhead_loc, (0, math.radians(90), 0))
        bulkhead_gen._link_to_collection(bulkhead, fittings_collection)
        
        # Connect pump to system
        pipe_z = self._calculate_pipe_height(pot_height, pipe_props)
        if layout.layout_type == 'GRID':
            # Connect to inlet manifold
            target_point = Vector(((layout.columns - 1) * layout.spacing_x / 2, manifold_y_in, pipe_z))
            
            # Pipe from pump bulkhead up
            pipe_up = pipe_gen.create("Pipe_Pump_Up",
                bulkhead_loc + Vector((0.05, 0, 0)),
                Vector((bulkhead_loc.x + 0.05, bulkhead_loc.y, pipe_z)))
            
            # Horizontal pipe to system
            pipe_to_system = pipe_gen.create("Pipe_Pump_To_System",
                Vector((bulkhead_loc.x + 0.05, bulkhead_loc.y, pipe_z)),
                target_point)
                
            for pipe in [pipe_up, pipe_to_system]:
                pipe_gen._link_to_collection(pipe, pipes_collection)
        
        # Add water level sensors
        if hasattr(context.scene.hydroponics_props, 'component_props') and context.scene.hydroponics_props.component_props.add_water_level_sensors:
            sensor_gen = mesh_creator.WaterLevelSensorMesh(scene_props)
            
            # High level sensor
            high_sensor_loc = reservoir_loc + Vector((res_rad * 0.5, 0, res_h/2 - 0.1))
            high_sensor = sensor_gen.create("Water_Level_High", high_sensor_loc, sensor_type='float')
            sensor_gen._link_to_collection(high_sensor, sensors_collection)
            
            # Low level sensor
            low_sensor_loc = reservoir_loc + Vector((res_rad * 0.5, 0, -res_h/2 + 0.2))
            low_sensor = sensor_gen.create("Water_Level_Low", low_sensor_loc, sensor_type='float')
            sensor_gen._link_to_collection(low_sensor, sensors_collection)
        
        # Add probe holder
        probe_holder_gen = mesh_creator.ProbeHolderMesh(scene_props)
        probe_loc = reservoir_loc + Vector((-res_rad + 0.1, 0, res_h/2))
        probe_holder = probe_holder_gen.create("Probe_Holder", probe_loc, num_slots=3)
        probe_holder_gen._link_to_collection(probe_holder, sensors_collection)
        
        return res_obj, reservoir_loc, res_h, res_rad

    def _generate_aeration_system(self, context, pot_objects, reservoir_info, collections):
        """Generates air pump, air lines, and air stones for each pot."""
        scene_props = context.scene.hydroponics_props
        
        if not hasattr(scene_props, 'component_props') or not scene_props.component_props.air_stones_per_pot:
            return
            
        _, _, aeration_collection = collections[4:7]
        
        # Create air pump
        air_pump_gen = mesh_creator.AirPumpMesh(scene_props)
        if reservoir_info:
            res_obj, res_loc, res_h, res_rad = reservoir_info
            pump_loc = res_loc + Vector((res_rad + 0.3, 0, res_h/2))
        else:
            pump_loc = Vector((0, -2, 0.5))
        
        air_pump = air_pump_gen.create("Air_Pump", pump_loc)
        air_pump_gen._link_to_collection(air_pump, aeration_collection)
        
        # Create air stones in each pot
        air_stone_gen = mesh_creator.AirStoneMesh(scene_props)
        for pot_obj, x, y, height, radius in pot_objects:
            num_stones = scene_props.component_props.air_stones_per_pot
            
            if num_stones == 1:
                # Single centered air stone
                stone_loc = Vector((x, y, height * 0.15))
                stone = air_stone_gen.create(f"Air_Stone_{pot_obj.name}", stone_loc, stone_type='cylinder')
                air_stone_gen._link_to_collection(stone, aeration_collection)
            else:
                # Multiple air stones arranged in circle
                stone_radius = radius * 0.5
                angle_step = 2 * math.pi / num_stones
                for i in range(num_stones):
                    angle = i * angle_step
                    stone_x = x + stone_radius * cos(angle)
                    stone_y = y + stone_radius * sin(angle)
                    stone_loc = Vector((stone_x, stone_y, height * 0.15))
                    stone = air_stone_gen.create(f"Air_Stone_{pot_obj.name}_{i}", stone_loc, stone_type='cylinder')
                    air_stone_gen._link_to_collection(stone, aeration_collection)
        
        # Note: In a real implementation, you'd add air tubing connections here

    def _generate_balance_system(self, context, generators, collections, dimensions):
        """Generates balance tank with proper connections."""
        scene_props = context.scene.hydroponics_props
        layout = scene_props.layout_props
        pipe_props = scene_props.pipe_props
        
        balance_gen = mesh_creator.BalanceTankMesh(scene_props)
        pipe_gen = generators[1]
        pots_collection, pipes_collection = collections[:2]
        _, pot_height, _, _, _, _, manifold_y_in, manifold_y_out = dimensions
        
        # Position balance tank
        if layout.layout_type == 'CIRCULAR':
            balance_loc = Vector((0, 0, 0))  # Center for circular
        else:
            grid_width = (layout.columns - 1) * layout.spacing_x
            balance_loc = Vector((grid_width / 2.0, manifold_y_out - layout.spacing_y * 0.75, 0))
        
        # Create balance tank
        balance_volume = float(scene_props.pot_props.volume) * 1.5  # 1.5x pot volume
        balance_obj, balance_h, balance_rad = balance_gen.create("Balance_Tank", balance_loc, balance_volume)
        balance_obj.location.z = balance_h / 2.0
        balance_gen._link_to_collection(balance_obj, pots_collection)
        
        # Connect to manifolds if grid layout
        if layout.layout_type == 'GRID':
            pipe_z = self._calculate_pipe_height(pot_height, pipe_props)
            
            # From outlet manifold to balance tank
            manifold_center = Vector(((layout.columns - 1) * layout.spacing_x / 2, manifold_y_out, pipe_z))
            balance_in_point = balance_loc + Vector((0, balance_rad, pipe_z))
            
            pipe_to_balance = pipe_gen.create("Pipe_To_Balance",
                manifold_center,
                balance_in_point)
            pipe_gen._link_to_collection(pipe_to_balance, pipes_collection)
        
        return balance_obj, balance_loc, balance_h, balance_rad

    def _generate_flow_indicators(self, context, generators, collections):
        """Add flow meters at strategic points."""
        if not hasattr(context.scene.hydroponics_props, 'component_props'):
            return
            
        comp_props = context.scene.hydroponics_props.component_props
        if not comp_props.add_flow_indicators:
            return
            
        flow_meter_gen = mesh_creator.FlowMeterMesh(context.scene.hydroponics_props)
        _, _, _, _, _, sensors_collection = collections[:6]
        
        # Add flow meter after main pump
        # Position would depend on actual pipe routing
        # This is a placeholder implementation

    def _generate_lighting(self, context, system_bounds_min, system_bounds_max):
        """Calculates required lighting and places LED panels."""
        props = context.scene.hydroponics_props.lighting_props
        
        if not hasattr(props, 'enable_lighting') or not props.enable_lighting:
            return
            
        # Skip config-based calculations if not available
        # Use simple coverage-based approach
        panel_gen = mesh_creator.LightPanelMesh(context.scene.hydroponics_props)
        lighting_collection = panel_gen._create_collection("Lighting")
        
        system_width = system_bounds_max.x - system_bounds_min.x
        system_depth = system_bounds_max.y - system_bounds_min.y
        
        # Default panel size
        panel_width = 0.6
        panel_depth = 0.6
        
        # Calculate number of panels needed
        panels_x = max(1, int(system_width / panel_width) + 1)
        panels_y = max(1, int(system_depth / panel_depth) + 1)
        
        # Calculate spacing
        spacing_x = system_width / panels_x if panels_x > 1 else 0
        spacing_y = system_depth / panels_y if panels_y > 1 else 0
        
        # Light height above system
        light_height = 0.6
        if hasattr(props, 'light_height'):
            light_height = props.light_height
            
        light_z = system_bounds_max.z + light_height
        
        # Place panels
        start_x = system_bounds_min.x + spacing_x / 2
        start_y = system_bounds_min.y + spacing_y / 2
        
        panel_count = 0
        for i in range(panels_x):
            for j in range(panels_y):
                loc = Vector((
                    start_x + i * spacing_x,
                    start_y + j * spacing_y,
                    light_z
                ))
                panel = panel_gen.create(f"LED_Panel_{panel_count}", loc, panel_width, panel_depth)
                panel_gen._link_to_collection(panel, lighting_collection)
                panel_count += 1
        
        self.report({'INFO'}, f"Created {panel_count} LED panels for coverage")

    def _finalize_system(self, context, collections):
        """Joins all generated parts into a single object and optimizes it."""
        scene_props = context.scene.hydroponics_props
        pots_collection, pipes_collection, fittings_collection, system_collection = collections[:4]
        pot_gen = mesh_creator.PotMesh(scene_props)

        # Don't join components that should remain separate
        rdwc_objects = []
        
        # Only join pipes and basic fittings
        for obj in list(pipes_collection.objects):
            if obj and obj.name in bpy.data.objects:
                rdwc_objects.append(obj)
                
        for obj in list(fittings_collection.objects):
            if obj and obj.name in bpy.data.objects:
                # Skip valves and complex fittings
                if not any(x in obj.name.lower() for x in ['valve', 'pump', 'sensor', 'meter']):
                    rdwc_objects.append(obj)
        
        if not rdwc_objects:
            return

        # Apply modifiers before joining
        for obj in rdwc_objects:
            bpy.context.view_layer.objects.active = obj
            for mod in list(obj.modifiers):
                try:
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                except:
                    pass
        
        # Select and join
        bpy.ops.object.select_all(action='DESELECT')
        for obj in rdwc_objects:
            obj.select_set(True)
        
        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            bpy.ops.object.join()
            final_system = bpy.context.active_object
            final_system.name = "RDWC_Piping_System"
            
            if scene_props.optimize_model:
                # Clean up geometry
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles(threshold=0.001)
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # Smooth shading
                bpy.ops.object.shade_smooth()
                
                # Add edge split for better shading
                edge_split = final_system.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
                edge_split.split_angle = math.radians(30)
                
            pot_gen._link_to_collection(final_system, system_collection)

    def execute(self, context):
        """Main execution function that orchestrates the system generation."""
        # 1. SETUP
        self._clear_previous()
        scene_props = context.scene.hydroponics_props
        layout = scene_props.layout_props
        
        # Initialize all generators
        pot_gen = mesh_creator.PotMesh(scene_props)
        pipe_gen = mesh_creator.PipeMesh(scene_props)
        tee_gen = mesh_creator.TeeFittingMesh(scene_props)
        elbow_gen = mesh_creator.ElbowFittingMesh(scene_props)
        valve_gen = mesh_creator.BallValveMesh(scene_props)
        union_gen = mesh_creator.UnionFittingMesh(scene_props)
        pump_gen = mesh_creator.PumpMesh(scene_props)
        bulkhead_gen = mesh_creator.BulkheadFittingMesh(scene_props)
        check_valve_gen = mesh_creator.CheckValveMesh(scene_props)
        flow_meter_gen = mesh_creator.FlowMeterMesh(scene_props)
        
        generators = (pot_gen, pipe_gen, tee_gen, elbow_gen, valve_gen, union_gen, 
                     pump_gen, bulkhead_gen, check_valve_gen, flow_meter_gen)

        # Create collections
        pots_collection = pot_gen._create_collection("Pots")
        pipes_collection = pipe_gen._create_collection("Pipes")
        fittings_collection = tee_gen._create_collection("Fittings")
        system_collection = pot_gen._create_collection("System")
        pumps_collection = pump_gen._create_collection("Pumps")
        sensors_collection = pot_gen._create_collection("Sensors")
        aeration_collection = pot_gen._create_collection("Aeration")
        valves_collection = valve_gen._create_collection("Valves")
        
        collections = (pots_collection, pipes_collection, fittings_collection, system_collection,
                      pumps_collection, sensors_collection, aeration_collection, valves_collection)

        # Calculate dimensions
        pot_volume = float(scene_props.pot_props.volume)
        _, pot_height, pot_radius = pot_gen.create("temp_pot", (0,0,0), pot_volume)
        bpy.data.objects.remove(bpy.data.objects['temp_pot'])
        
        pipe_z = pot_height * 0.15  # Base pipe height
        tee_arm_total_length = (tee_gen.get_diameter() * 0.8) + (tee_gen.get_diameter() * 0.6)
        pipe_insertion_depth = (tee_gen.get_diameter() * 0.6) * 0.4
        
        # Calculate manifold positions for grid layout
        manifold_y_in = (layout.rows - 1) * layout.spacing_y + layout.spacing_y * 0.8
        manifold_y_out = -layout.spacing_y * 0.8
        
        dimensions = (pot_volume, pot_height, pot_radius, pipe_z, tee_arm_total_length, 
                     pipe_insertion_depth, manifold_y_in, manifold_y_out)

        # 2. GENERATE MAIN SYSTEM BASED ON LAYOUT TYPE
        pot_objects = []
        if layout.layout_type == 'GRID':
            pot_objects = self._generate_grid_manifold(context, generators, collections, dimensions)
        elif layout.layout_type == 'CIRCULAR':
            pot_objects = self._generate_circular_layout(context, generators, collections, dimensions)
        elif layout.layout_type == 'LINEAR':
            # Simplified linear layout (single row grid)
            temp_rows = layout.rows
            layout.rows = 1
            pot_objects = self._generate_grid_manifold(context, generators, collections, dimensions)
            layout.rows = temp_rows
        
        # 3. GENERATE SUPPORTING SYSTEMS
        reservoir_info = None
        if scene_props.enable_reservoir:
            reservoir_info = self._generate_reservoir_system(context, generators, collections, dimensions)
        
        # Generate balance tank
        balance_info = self._generate_balance_system(context, generators, collections, dimensions)
        
        # Generate aeration system
        self._generate_aeration_system(context, pot_objects, reservoir_info, collections)
        
        # Generate flow indicators
        self._generate_flow_indicators(context, generators, collections)

        # 4. GENERATE LIGHTING
        all_objects = []
        for collection in collections[:3]:  # Pots, Pipes, Fittings
            all_objects.extend(list(collection.objects))
            
        min_bounds, max_bounds = get_total_bounding_box(all_objects)
        if min_bounds and max_bounds:
            self._generate_lighting(context, min_bounds, max_bounds)

        # 5. FINALIZE
        if scene_props.create_connections:
            self._finalize_system(context, collections)
        
        self.report({'INFO'}, f"RDWC System Generation Complete - Layout: {layout.layout_type}")
        return {'FINISHED'}

# Registration functions
classes = (WM_OT_hydroponics_generator,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)