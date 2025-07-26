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
    # bpy.ops.object.transform_apply(location=True, rotation=False, scale=False) # Apply location
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
    """Creates a single DWC pot/bucket."""
    # This class remains unchanged from your original file.
    def create(self, name, location, volume_liters):
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
    """Creates a simple cylindrical reservoir tank."""
    def create(self, name, location, volume_liters):
        # Convert volume from liters to cubic meters
        volume_m3 = volume_liters / 1000.0
        
        # Define a standard height-to-radius ratio for the reservoir (e.g., 1.5)
        # V = pi * r^2 * h = pi * r^2 * (1.5 * 2r) = 3 * pi * r^3  (assuming h = 1.5 * diameter)
        # So, r = (V / (3 * pi))^(1/3)
        radius = (volume_m3 / (3 * math.pi))**(1/3)
        height = 1.5 * (2 * radius)

        # Create a simple cylinder for the reservoir
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64,
            radius=radius,
            depth=height,
            location=location,
            rotation=(0, 0, 0)
        )
        reservoir = bpy.context.active_object
        reservoir.name = name
        
        # Apply a solidify modifier for wall thickness
        solidify = reservoir.modifiers.new(name="WallThickness", type='SOLIDIFY')
        solidify.thickness = 0.005  # A bit thicker for a larger tank
        solidify.offset = 1
        
        bpy.context.view_layer.objects.active = reservoir
        bpy.ops.object.modifier_apply(modifier=solidify.name)
        
        # Remove the top face to make it a tank
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(reservoir.data)
        bm.faces.ensure_lookup_table()
        top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
        top_face.select = True
        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')

        return reservoir, height, radius


class BalanceBucketMesh(MeshGenerator):
    """Creates the central balance bucket, similar to a standard pot."""
    def create(self, name, location, volume_liters):
        # This is essentially the same as a standard pot for now
        pot_mesh_gen = PotMesh(self.props)
        return pot_mesh_gen.create(name, location, volume_liters)



class PipeMesh(MeshGenerator):
    """Creates a straight pipe between two points."""
    # This class remains unchanged.
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
        # --- Dimensions ---
        diameter = self.get_diameter()
        radius = diameter / 2
        wall_thickness = self.get_wall_thickness()
        inner_radius = radius - wall_thickness
        socket_outer_radius = radius * 1.25
        socket_length = diameter * 0.6
        arm_core_length = diameter * 0.8

        # --- Create Outer Shell ---
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

        # --- Create Inner Cutter for Hollowing ---
        cutter_len = (arm_core_length + socket_length) * 2.5
        main_cutter = _create_and_transform_cylinder(inner_radius, cutter_len, 48, (0,0,0), (0, math.radians(90), 0))
        branch_cutter = _create_and_transform_cylinder(inner_radius, cutter_len/2, 48, (0, cutter_len/4, 0), (math.radians(90), 0, 0))
        _apply_boolean(main_cutter, branch_cutter, 'UNION')

        # --- Perform Difference to Hollow Out ---
        _apply_boolean(outer_shell, main_cutter, 'DIFFERENCE')
        
        fitting_obj = outer_shell
        fitting_obj.name = name
        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation

        # --- Final Polish ---
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
        # --- Dimensions ---
        diameter = self.get_diameter()
        radius = diameter / 2
        wall_thickness = self.get_wall_thickness()
        inner_radius = radius - wall_thickness
        socket_outer_radius = radius * 1.25
        socket_length = diameter * 0.6
        arm_core_length = diameter * 0.8

        # --- Create Outer Shell ---
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

        # --- Create Inner Cutter for Hollowing ---
        cutter_len = (arm_core_length + socket_length) * 2.5
        cutter_x = _create_and_transform_cylinder(inner_radius, cutter_len, 48, (cutter_len/2, 0, 0), (0, math.radians(90), 0))
        cutter_y = _create_and_transform_cylinder(inner_radius, cutter_len, 48, (0, cutter_len/2, 0), (math.radians(90), 0, 0))
        _apply_boolean(cutter_x, cutter_y, 'UNION')

        # --- Perform Difference to Hollow Out ---
        _apply_boolean(outer_shell, cutter_x, 'DIFFERENCE')
        
        fitting_obj = outer_shell
        fitting_obj.name = name
        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation

        # --- Final Polish ---
        bpy.context.view_layer.objects.active = fitting_obj
        bpy.ops.object.shade_smooth()
        mod_bevel = fitting_obj.modifiers.new(name='Bevel', type='BEVEL')
        mod_bevel.width = wall_thickness * 0.2
        mod_bevel.segments = 2
        mod_bevel.angle_limit = math.radians(30)

        return fitting_obj


def register():
    pass

def unregister():
    pass