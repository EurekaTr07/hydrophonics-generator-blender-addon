import bpy
import bmesh
import math
from mathutils import Vector, Matrix

# =================================================================================================
# HELPER FUNCTIONS
# =================================================================================================

def _apply_boolean(base_obj, cutter_obj, operation='UNION', keep_cutter=False):
    """Applies a boolean modifier to the base object and handles object removal."""
    bpy.context.view_layer.objects.active = base_obj
    mod = base_obj.modifiers.new(name='Boolean', type='BOOLEAN')
    mod.object = cutter_obj
    mod.operation = operation
    mod.solver = 'FAST'  # Use 'FAST' for better performance and reliability
    try:
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except RuntimeError as e:
        print(f"Boolean operation failed: {e}")
        base_obj.modifiers.remove(mod) # Clean up failed modifier

    if not keep_cutter:
        bpy.data.objects.remove(cutter_obj, do_unlink=True)


def _create_and_transform_cylinder(radius, depth, vertices, location, rotation):
    """Creates a cylinder and applies specified location and rotation."""
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=vertices, location=(0,0,0), rotation=(0,0,0))
    obj = bpy.context.active_object
    obj.location = location
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True) # Apply rotation
    return obj


# =================================================================================================
# MESH CREATION CLASSES
# =================================================================================================

class MeshGenerator:
    """Base class for mesh generation."""
    def __init__(self, props):
        self.props = props

    def _create_collection(self, collection_name):
        """Creates a new collection or returns an existing one."""
        if collection_name not in bpy.data.collections:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)
        else:
            collection = bpy.data.collections[collection_name]
        return collection

    def _link_to_collection(self, obj, collection):
        """Links an object to a specified collection, ensuring it's not in others."""
        if not obj:
            return
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        if obj.name not in collection.objects:
            collection.objects.link(obj)

class PotMesh(MeshGenerator):
    """Creates a single DWC pot/bucket with net pot holder."""
    def create(self, name, location, volume_liters, add_net_pot=True):
        volume_m3 = volume_liters / 1000.0
        radius = (volume_m3 / (2.5 * math.pi)) ** (1 / 3)
        height = 2.5 * radius
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, radius1=radius, radius2=radius, depth=height, segments=64)
        top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
        bmesh.ops.delete(bm, geom=[top_face], context='FACES')
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        pot = bpy.data.objects.new(name, mesh)
        pot.location = location
        bpy.context.collection.objects.link(pot)
        solidify = pot.modifiers.new(name="WallThickness", type='SOLIDIFY')
        solidify.thickness = 0.003
        solidify.offset = 1
        bpy.context.view_layer.objects.active = pot
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Create net pot holder if requested
        if add_net_pot:
            # Create a circular cutout for net pot
            net_pot_radius = min(radius * 0.4, 0.075)  # 15cm max diameter
            bpy.ops.mesh.primitive_cylinder_add(
                radius=net_pot_radius,
                depth=0.1,
                location=(location.x, location.y, location.z + height/2)
            )
            cutter = bpy.context.active_object
            _apply_boolean(pot, cutter, 'DIFFERENCE')
        
        # Create rim
        bpy.context.view_layer.objects.active = pot
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(pot.data)
        bm.edges.ensure_lookup_table()
        top_edges = [e for e in bm.edges if e.is_boundary]
        for edge in top_edges:
            edge.select = True
        bpy.ops.mesh.extrude_region_move()
        bpy.ops.transform.resize(value=(1.1, 1.1, 1.0))
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, -0.02)})
        bpy.ops.object.mode_set(mode='OBJECT')
        return pot, height, radius


class ReservoirMesh(MeshGenerator):
    """Creates a reservoir tank with ports for pumps and sensors."""
    def create(self, name, location, volume_liters, add_ports=True):
        volume_m3 = volume_liters / 1000.0
        radius = (volume_m3 / (3 * math.pi))**(1/3)
        height = 1.5 * (2 * radius)

        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=radius,
            depth=height,
            location=location,
            rotation=(0, 0, 0)
        )
        reservoir = bpy.context.active_object
        reservoir.name = name
        
        solidify = reservoir.modifiers.new(name="WallThickness", type='SOLIDIFY')
        solidify.thickness = 0.005
        solidify.offset = 1
        
        bpy.context.view_layer.objects.active = reservoir
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Remove the top face
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(reservoir.data)
        bm.faces.ensure_lookup_table()
        top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
        top_face.select = True
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Add ports if requested
        if add_ports:
            # Pump outlet port (bottom)
            port_radius = 0.025
            bpy.ops.mesh.primitive_cylinder_add(
                radius=port_radius,
                depth=0.1,
                location=(location.x + radius * 0.7, location.y, location.z - height/2 + 0.05),
                rotation=(0, 0, 0)
            )
            port = bpy.context.active_object
            _apply_boolean(reservoir, port, 'UNION')

        return reservoir, height, radius


class BalanceTankMesh(MeshGenerator):
    """Creates a balance tank with multiple inlet/outlet ports."""
    def create(self, name, location, volume_liters):
        # Similar to reservoir but shorter and wider
        volume_m3 = volume_liters / 1000.0
        radius = (volume_m3 / (1.5 * math.pi))**(1/3)
        height = 0.75 * (2 * radius)
        
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=radius,
            depth=height,
            location=location
        )
        tank = bpy.context.active_object
        tank.name = name
        
        # Wall thickness
        solidify = tank.modifiers.new(name="WallThickness", type='SOLIDIFY')
        solidify.thickness = 0.004
        solidify.offset = 1
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Remove top
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(tank.data)
        bm.faces.ensure_lookup_table()
        top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
        top_face.select = True
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        return tank, height, radius


class PipeMesh(MeshGenerator):
    """Creates a straight pipe between two points."""
    def create(self, name, start_loc, end_loc):
        pipe_props = self.props.pipe_props
        diameter = float(pipe_props.pipe_size) / 1000.0
        diff = end_loc - start_loc
        length = diff.length
        if length < 0.0001:
            return None
        location = start_loc + (diff / 2.0)
        rotation = diff.to_track_quat('Z', 'Y').to_euler()
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32,
            radius=diameter / 2,
            depth=length,
            location=location,
            rotation=rotation
        )
        pipe = bpy.context.active_object
        pipe.name = name
        return pipe


class FittingMesh(MeshGenerator):
    """Base class for pipe fittings."""
    def get_diameter(self):
        pipe_props = self.props.pipe_props
        return float(pipe_props.pipe_size) / 1000.0
    
    def get_wall_thickness(self):
        """Returns a realistic wall thickness."""
        return self.get_diameter() * 0.15


class TeeFittingMesh(FittingMesh):
    """Creates a high-detail, hollow T-fitting with sockets using boolean operations."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        wall_thickness = self.get_wall_thickness()
        inner_radius = radius - wall_thickness
        socket_outer_radius = radius * 1.25
        socket_length = diameter * 0.6
        arm_core_length = diameter * 0.8

        # Create Outer Shell
        main_cyl = _create_and_transform_cylinder(radius, arm_core_length * 2, 64, (0,0,0), (0, math.radians(90), 0))
        branch_cyl = _create_and_transform_cylinder(radius, arm_core_length, 64, (0, arm_core_length/2, 0), (math.radians(90), 0, 0))
        _apply_boolean(main_cyl, branch_cyl, 'UNION')

        # Sockets
        socket_px = _create_and_transform_cylinder(socket_outer_radius, socket_length, 64, (arm_core_length + socket_length / 2, 0, 0), (0, math.radians(90), 0))
        _apply_boolean(main_cyl, socket_px, 'UNION')
        socket_nx = _create_and_transform_cylinder(socket_outer_radius, socket_length, 64, (-arm_core_length - socket_length / 2, 0, 0), (0, math.radians(90), 0))
        _apply_boolean(main_cyl, socket_nx, 'UNION')
        socket_py = _create_and_transform_cylinder(socket_outer_radius, socket_length, 64, (0, arm_core_length + socket_length / 2, 0), (math.radians(90), 0, 0))
        _apply_boolean(main_cyl, socket_py, 'UNION')
        
        outer_shell = main_cyl
        outer_shell.name = f"{name}_outer"

        # Create Inner Cutter for Hollowing
        cutter_len = (arm_core_length + socket_length) * 2.5
        main_cutter = _create_and_transform_cylinder(inner_radius, cutter_len, 48, (0,0,0), (0, math.radians(90), 0))
        branch_cutter = _create_and_transform_cylinder(inner_radius, cutter_len/2, 48, (0, cutter_len/4, 0), (math.radians(90), 0, 0))
        _apply_boolean(main_cutter, branch_cutter, 'UNION')

        # Perform Difference to Hollow Out
        _apply_boolean(outer_shell, main_cutter, 'DIFFERENCE')
        
        fitting_obj = outer_shell
        fitting_obj.name = name
        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation

        # Final Polish
        bpy.context.view_layer.objects.active = fitting_obj
        bpy.ops.object.shade_smooth()
        mod_bevel = fitting_obj.modifiers.new(name='Bevel', type='BEVEL')
        mod_bevel.width = wall_thickness * 0.2
        mod_bevel.segments = 2
        mod_bevel.angle_limit = math.radians(30)
        
        return fitting_obj


class ElbowFittingMesh(FittingMesh):
    """Creates a high-detail, hollow 90-degree elbow fitting with sockets."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        wall_thickness = self.get_wall_thickness()
        inner_radius = radius - wall_thickness
        socket_outer_radius = radius * 1.25
        socket_length = diameter * 0.6
        arm_core_length = diameter * 0.8

        # Create Outer Shell
        arm_x = _create_and_transform_cylinder(radius, arm_core_length, 64, (arm_core_length/2, 0, 0), (0, math.radians(90), 0))
        arm_y = _create_and_transform_cylinder(radius, arm_core_length, 64, (0, arm_core_length/2, 0), (math.radians(90), 0, 0))
        _apply_boolean(arm_x, arm_y, 'UNION')

        # Sockets
        socket_px = _create_and_transform_cylinder(socket_outer_radius, socket_length, 64, (arm_core_length + socket_length / 2, 0, 0), (0, math.radians(90), 0))
        _apply_boolean(arm_x, socket_px, 'UNION')
        socket_py = _create_and_transform_cylinder(socket_outer_radius, socket_length, 64, (0, arm_core_length + socket_length / 2, 0), (math.radians(90), 0, 0))
        _apply_boolean(arm_x, socket_py, 'UNION')
        
        outer_shell = arm_x
        outer_shell.name = f"{name}_outer"

        # Create Inner Cutter for Hollowing
        cutter_len = (arm_core_length + socket_length) * 2.5
        cutter_x = _create_and_transform_cylinder(inner_radius, cutter_len, 48, (cutter_len/2, 0, 0), (0, math.radians(90), 0))
        cutter_y = _create_and_transform_cylinder(inner_radius, cutter_len, 48, (0, cutter_len/2, 0), (math.radians(90), 0, 0))
        _apply_boolean(cutter_x, cutter_y, 'UNION')

        # Perform Difference to Hollow Out
        _apply_boolean(outer_shell, cutter_x, 'DIFFERENCE')
        
        fitting_obj = outer_shell
        fitting_obj.name = name
        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation

        # Final Polish
        bpy.context.view_layer.objects.active = fitting_obj
        bpy.ops.object.shade_smooth()
        mod_bevel = fitting_obj.modifiers.new(name='Bevel', type='BEVEL')
        mod_bevel.width = wall_thickness * 0.2
        mod_bevel.segments = 2
        mod_bevel.angle_limit = math.radians(30)

        return fitting_obj


class UnionFittingMesh(FittingMesh):
    """Creates a union/coupling fitting for joining pipes."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        socket_outer_radius = radius * 1.3
        socket_length = diameter * 0.8
        total_length = socket_length * 2
        
        # Create main body
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=socket_outer_radius,
            depth=total_length,
            location=location,
            rotation=rotation
        )
        union = bpy.context.active_object
        union.name = name
        
        # Create inner hollow
        wall_thickness = self.get_wall_thickness()
        inner_radius = radius - wall_thickness
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=48,
            radius=inner_radius,
            depth=total_length * 1.1,
            location=location,
            rotation=rotation
        )
        cutter = bpy.context.active_object
        _apply_boolean(union, cutter, 'DIFFERENCE')
        
        # Add center ridge
        bpy.ops.mesh.primitive_torus_add(
            major_radius=socket_outer_radius,
            minor_radius=wall_thickness * 0.5,
            location=location,
            rotation=rotation
        )
        ridge = bpy.context.active_object
        _apply_boolean(union, ridge, 'UNION')
        
        return union


class BallValveMesh(FittingMesh):
    """Creates a ball valve for flow control."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        body_radius = radius * 1.5
        body_length = diameter * 2
        
        # Create valve body
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=body_radius,
            depth=body_length,
            location=location,
            rotation=(0, math.radians(90), 0)
        )
        valve_body = bpy.context.active_object
        
        # Add sockets on both ends
        socket_radius = radius * 1.25
        socket_length = diameter * 0.5
        
        for x_offset in [-body_length/2 - socket_length/2, body_length/2 + socket_length/2]:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=64,
                radius=socket_radius,
                depth=socket_length,
                location=(location.x + x_offset, location.y, location.z),
                rotation=(0, math.radians(90), 0)
            )
            socket = bpy.context.active_object
            _apply_boolean(valve_body, socket, 'UNION')
        
        # Create handle mount
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32,
            radius=radius * 0.5,
            depth=radius,
            location=(location.x, location.y, location.z + body_radius),
            rotation=(0, 0, 0)
        )
        mount = bpy.context.active_object
        _apply_boolean(valve_body, mount, 'UNION')
        
        # Create handle
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(location.x, location.y, location.z + body_radius + radius/2)
        )
        handle = bpy.context.active_object
        handle.scale = (diameter * 1.5, radius * 0.3, radius * 0.2)
        bpy.ops.object.transform_apply(scale=True)
        _apply_boolean(valve_body, handle, 'UNION')
        
        valve_body.name = name
        valve_body.rotation_euler = rotation
        
        return valve_body


class CheckValveMesh(FittingMesh):
    """Creates a one-way check valve."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        body_length = diameter * 2.5
        
        # Create tapered body
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            radius1=radius * 1.2,
            radius2=radius * 1.4,
            depth=body_length,
            segments=64
        )
        
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        
        valve = bpy.data.objects.new(name, mesh)
        valve.location = location
        valve.rotation_euler = (0, math.radians(90), 0)
        bpy.context.collection.objects.link(valve)
        
        # Add directional arrow
        bpy.ops.mesh.primitive_cone_add(
            vertices=3,
            radius1=radius * 0.5,
            radius2=0,
            depth=radius * 0.5,
            location=(location.x + body_length/4, location.y, location.z + radius * 1.3),
            rotation=(0, math.radians(-90), 0)
        )
        arrow = bpy.context.active_object
        _apply_boolean(valve, arrow, 'UNION')
        
        valve.rotation_euler = rotation
        return valve


class PumpMesh(MeshGenerator):
    """Creates a submersible water pump."""
    def create(self, name, location, pump_type='submersible'):
        if pump_type == 'submersible':
            # Create cylindrical body
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=64,
                radius=0.05,
                depth=0.15,
                location=location
            )
            pump = bpy.context.active_object
            pump.name = name
            
            # Add intake grille
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.055,
                depth=0.03,
                location=(location.x, location.y, location.z - 0.06)
            )
            intake = bpy.context.active_object
            _apply_boolean(pump, intake, 'UNION')
            
            # Add outlet port
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.015,
                depth=0.05,
                location=(location.x + 0.05, location.y, location.z + 0.05),
                rotation=(0, math.radians(90), 0)
            )
            outlet = bpy.context.active_object
            _apply_boolean(pump, outlet, 'UNION')
            
            return pump
        
        elif pump_type == 'inline':
            # Create inline pump body
            bpy.ops.mesh.primitive_cube_add(
                size=1,
                location=location
            )
            pump = bpy.context.active_object
            pump.scale = (0.12, 0.08, 0.08)
            bpy.ops.object.transform_apply(scale=True)
            pump.name = name
            
            # Add inlet/outlet ports
            for x_offset in [-0.06, 0.06]:
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=32,
                    radius=0.02,
                    depth=0.04,
                    location=(location.x + x_offset, location.y, location.z),
                    rotation=(0, math.radians(90), 0)
                )
                port = bpy.context.active_object
                _apply_boolean(pump, port, 'UNION')
            
            return pump


class AirStoneMesh(MeshGenerator):
    """Creates an air stone for oxygenation."""
    def create(self, name, location, stone_type='cylinder'):
        if stone_type == 'cylinder':
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.015,
                depth=0.05,
                location=location
            )
        elif stone_type == 'disk':
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=64,
                radius=0.04,
                depth=0.01,
                location=location
            )
        elif stone_type == 'ball':
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=32,
                ring_count=16,
                radius=0.025,
                location=location
            )
        
        stone = bpy.context.active_object
        stone.name = name
        
        # Add porous texture via displacement
        bpy.ops.object.shade_smooth()
        subdiv = stone.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv.levels = 2
        
        displace = stone.modifiers.new(name="Porous", type='DISPLACE')
        displace.strength = 0.002
        
        return stone


class FlowMeterMesh(FittingMesh):
    """Creates a flow meter for monitoring water flow."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        body_length = diameter * 2
        
        # Create main body
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=radius * 1.3,
            depth=body_length,
            location=location,
            rotation=(0, math.radians(90), 0)
        )
        meter = bpy.context.active_object
        meter.name = name
        
        # Add display housing
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32,
            radius=radius * 0.8,
            depth=radius * 0.5,
            location=(location.x, location.y, location.z + radius * 1.3),
            rotation=(math.radians(45), 0, 0)
        )
        display = bpy.context.active_object
        _apply_boolean(meter, display, 'UNION')
        
        # Add inlet/outlet connections
        for x_offset in [-body_length/2, body_length/2]:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=radius * 1.1,
                depth=diameter * 0.4,
                location=(location.x + x_offset, location.y, location.z),
                rotation=(0, math.radians(90), 0)
            )
            connection = bpy.context.active_object
            _apply_boolean(meter, connection, 'UNION')
        
        meter.rotation_euler = rotation
        return meter


class WaterLevelSensorMesh(MeshGenerator):
    """Creates a water level sensor/float switch."""
    def create(self, name, location, sensor_type='float'):
        if sensor_type == 'float':
            # Create float body
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.02,
                depth=0.08,
                location=location
            )
            sensor = bpy.context.active_object
            sensor.name = name
            
            # Add float
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=32,
                ring_count=16,
                radius=0.025,
                location=(location.x, location.y, location.z - 0.05)
            )
            float_ball = bpy.context.active_object
            
            # Add wire guide
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16,
                radius=0.003,
                depth=0.12,
                location=(location.x, location.y + 0.01, location.z)
            )
            wire = bpy.context.active_object
            
            # Join all parts
            bpy.ops.object.select_all(action='DESELECT')
            sensor.select_set(True)
            float_ball.select_set(True)
            wire.select_set(True)
            bpy.context.view_layer.objects.active = sensor
            bpy.ops.object.join()
            
            return sensor
        
        elif sensor_type == 'ultrasonic':
            # Create ultrasonic sensor housing
            bpy.ops.mesh.primitive_cube_add(
                size=1,
                location=location
            )
            sensor = bpy.context.active_object
            sensor.scale = (0.04, 0.03, 0.02)
            bpy.ops.object.transform_apply(scale=True)
            sensor.name = name
            
            # Add sensor eyes
            for y_offset in [-0.01, 0.01]:
                bpy.ops.mesh.primitive_cylinder_add(
                    vertices=32,
                    radius=0.008,
                    depth=0.005,
                    location=(location.x, location.y + y_offset, location.z - 0.01),
                    rotation=(math.radians(90), 0, 0)
                )
                eye = bpy.context.active_object
                _apply_boolean(sensor, eye, 'UNION')
            
            return sensor


class ProbeHolderMesh(MeshGenerator):
    """Creates a holder for pH/EC probes."""
    def create(self, name, location, num_slots=2):
        # Create base plate
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=location
        )
        holder = bpy.context.active_object
        holder.scale = (0.08, 0.04, 0.01)
        bpy.ops.object.transform_apply(scale=True)
        holder.name = name
        
        # Add probe slots
        slot_spacing = 0.025
        start_x = -(num_slots - 1) * slot_spacing / 2
        
        for i in range(num_slots):
            slot_x = start_x + i * slot_spacing
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.008,
                depth=0.02,
                location=(location.x + slot_x, location.y, location.z)
            )
            slot = bpy.context.active_object
            _apply_boolean(holder, slot, 'DIFFERENCE')
        
        # Add mounting tabs
        for x_offset in [-0.04, 0.04]:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.006,
                depth=0.012,
                location=(location.x + x_offset, location.y, location.z)
            )
            tab = bpy.context.active_object
            _apply_boolean(holder, tab, 'UNION')
            
            # Add screw holes
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16,
                radius=0.003,
                depth=0.015,
                location=(location.x + x_offset, location.y, location.z)
            )
            hole = bpy.context.active_object
            _apply_boolean(holder, hole, 'DIFFERENCE')
        
        return holder


class BulkheadFittingMesh(FittingMesh):
    """Creates a bulkhead fitting for tank connections."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        flange_radius = radius * 2
        flange_thickness = 0.005
        
        # Create threaded body
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=radius * 1.1,
            depth=0.05,
            location=location
        )
        fitting = bpy.context.active_object
        fitting.name = name
        
        # Add flange
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=flange_radius,
            depth=flange_thickness,
            location=(location.x, location.y, location.z + 0.025)
        )
        flange = bpy.context.active_object
        _apply_boolean(fitting, flange, 'UNION')
        
        # Add inner hole
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=48,
            radius=radius * 0.9,
            depth=0.06,
            location=location
        )
        hole = bpy.context.active_object
        _apply_boolean(fitting, hole, 'DIFFERENCE')
        
        # Add gasket groove
        bpy.ops.mesh.primitive_torus_add(
            major_radius=radius * 1.5,
            minor_radius=0.002,
            location=(location.x, location.y, location.z + 0.023)
        )
        groove = bpy.context.active_object
        _apply_boolean(fitting, groove, 'DIFFERENCE')
        
        fitting.rotation_euler = rotation
        return fitting


class EndCapMesh(FittingMesh):
    """Creates an end cap for sealing pipes."""
    def create(self, name, location, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        socket_radius = radius * 1.25
        cap_length = diameter * 0.8
        
        # Create main cap body
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=socket_radius,
            depth=cap_length,
            location=location,
            rotation=rotation
        )
        cap = bpy.context.active_object
        cap.name = name
        
        # Create inner hollow for pipe insertion
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=48,
            radius=radius,
            depth=cap_length * 0.8,
            location=(location.x, location.y, location.z - cap_length * 0.1),
            rotation=rotation
        )
        hollow = bpy.context.active_object
        _apply_boolean(cap, hollow, 'DIFFERENCE')
        
        # Add grip ridges
        for i in range(3):
            z_offset = -cap_length/3 + i * cap_length/6
            bpy.ops.mesh.primitive_torus_add(
                major_radius=socket_radius,
                minor_radius=0.001,
                location=(location.x, location.y, location.z + z_offset),
                rotation=rotation
            )
            ridge = bpy.context.active_object
            _apply_boolean(cap, ridge, 'UNION')
        
        return cap


class ManifoldBlockMesh(FittingMesh):
    """Creates a manifold block with multiple outlets."""
    def create(self, name, location, num_outlets=4, rotation=(0, 0, 0)):
        diameter = self.get_diameter()
        radius = diameter / 2
        block_length = num_outlets * diameter * 1.5
        block_height = diameter * 2
        
        # Create main block
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=location
        )
        manifold = bpy.context.active_object
        manifold.scale = (block_length/2, diameter, block_height/2)
        bpy.ops.object.transform_apply(scale=True)
        manifold.name = name
        
        # Create main channel
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=48,
            radius=radius * 0.9,
            depth=block_length * 1.1,
            location=location,
            rotation=(0, math.radians(90), 0)
        )
        channel = bpy.context.active_object
        _apply_boolean(manifold, channel, 'DIFFERENCE')
        
        # Add outlet ports
        outlet_spacing = block_length / (num_outlets + 1)
        start_x = -block_length/2 + outlet_spacing
        
        for i in range(num_outlets):
            outlet_x = start_x + i * outlet_spacing
            # Outlet hole
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=radius * 0.8,
                depth=block_height,
                location=(location.x + outlet_x, location.y, location.z)
            )
            outlet = bpy.context.active_object
            _apply_boolean(manifold, outlet, 'DIFFERENCE')
            
            # Outlet socket
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=radius * 1.1,
                depth=diameter * 0.5,
                location=(location.x + outlet_x, location.y, location.z - block_height/2 - diameter * 0.25)
            )
            socket = bpy.context.active_object
            _apply_boolean(manifold, socket, 'UNION')
        
        # Add inlet/outlet ports on ends
        for x_offset, y_offset in [(-block_length/2, 0), (block_length/2, 0)]:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=radius * 1.2,
                depth=diameter * 0.6,
                location=(location.x + x_offset + (y_offset * 0.3), location.y, location.z),
                rotation=(0, math.radians(90), 0)
            )
            end_port = bpy.context.active_object
            _apply_boolean(manifold, end_port, 'UNION')
        
        manifold.rotation_euler = rotation
        return manifold


class DripEmitterMesh(MeshGenerator):
    """Creates a drip emitter for drip irrigation systems."""
    def create(self, name, location, emitter_type='button'):
        if emitter_type == 'button':
            # Create button dripper
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.01,
                depth=0.008,
                location=location
            )
            emitter = bpy.context.active_object
            emitter.name = name
            
            # Add barb connector
            bpy.ops.mesh.primitive_cone_add(
                vertices=16,
                radius1=0.005,
                radius2=0.003,
                depth=0.015,
                location=(location.x, location.y, location.z - 0.0115)
            )
            barb = bpy.context.active_object
            _apply_boolean(emitter, barb, 'UNION')
            
        elif emitter_type == 'stake':
            # Create stake dripper
            bpy.ops.mesh.primitive_cone_add(
                vertices=32,
                radius1=0.008,
                radius2=0.002,
                depth=0.08,
                location=location
            )
            emitter = bpy.context.active_object
            emitter.name = name
            
            # Add dripper head
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=32,
                radius=0.012,
                depth=0.01,
                location=(location.x, location.y, location.z + 0.045)
            )
            head = bpy.context.active_object
            _apply_boolean(emitter, head, 'UNION')
        
        return emitter


class LightPanelMesh(MeshGenerator):
    """Creates LED light panel with heat sink details."""
    def create(self, name, location, size_x, size_y):
        # Create the panel body
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        panel = bpy.context.active_object
        panel.name = name
        
        # Set dimensions
        panel.dimensions = (size_x, size_y, 0.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        # Add heat sink fins
        fin_count = int(size_x / 0.02)
        fin_spacing = size_x / fin_count
        
        for i in range(fin_count):
            x_offset = -size_x/2 + fin_spacing/2 + i * fin_spacing
            bpy.ops.mesh.primitive_cube_add(
                size=1,
                location=(location.x + x_offset, location.y, location.z + 0.03)
            )
            fin = bpy.context.active_object
            fin.scale = (0.002, size_y * 0.9, 0.01)
            bpy.ops.object.transform_apply(scale=True)
            _apply_boolean(panel, fin, 'UNION')
        
        # Add mounting brackets
        for x, y in [(-size_x/2 + 0.05, -size_y/2 + 0.05), 
                     (size_x/2 - 0.05, -size_y/2 + 0.05),
                     (-size_x/2 + 0.05, size_y/2 - 0.05),
                     (size_x/2 - 0.05, size_y/2 - 0.05)]:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16,
                radius=0.01,
                depth=0.02,
                location=(location.x + x, location.y + y, location.z + 0.035)
            )
            bracket = bpy.context.active_object
            _apply_boolean(panel, bracket, 'UNION')
            
            # Add mounting holes
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16,
                radius=0.004,
                depth=0.03,
                location=(location.x + x, location.y + y, location.z + 0.035)
            )
            hole = bpy.context.active_object
            _apply_boolean(panel, hole, 'DIFFERENCE')

        # Add LED emitter surface material
        mat = bpy.data.materials.new(name=f"{name}_Material")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Emission'].default_value = (1.0, 0.95, 0.8, 1.0)  # Warm white
        bsdf.inputs['Emission Strength'].default_value = 5.0
        panel.data.materials.append(mat)
        
        return panel


class AirPumpMesh(MeshGenerator):
    """Creates an air pump for oxygenation system."""
    def create(self, name, location):
        # Create pump body
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=location
        )
        pump = bpy.context.active_object
        pump.scale = (0.15, 0.10, 0.08)
        bpy.ops.object.transform_apply(scale=True)
        pump.name = name
        
        # Round the edges
        bpy.ops.object.modifier_add(type='BEVEL')
        pump.modifiers["Bevel"].width = 0.01
        pump.modifiers["Bevel"].segments = 3
        
        # Add air outlets
        for i in range(2):
            x_offset = -0.05 + i * 0.1
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16,
                radius=0.008,
                depth=0.03,
                location=(location.x + x_offset, location.y - 0.05, location.z),
                rotation=(math.radians(90), 0, 0)
            )
            outlet = bpy.context.active_object
            _apply_boolean(pump, outlet, 'UNION')
        
        # Add rubber feet
        for x, y in [(-0.06, -0.04), (0.06, -0.04), (-0.06, 0.04), (0.06, 0.04)]:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=16,
                radius=0.01,
                depth=0.005,
                location=(location.x + x, location.y + y, location.z - 0.0425)
            )
            foot = bpy.context.active_object
            _apply_boolean(pump, foot, 'UNION')
        
        return pump


def register():
    pass

def unregister():
    pass