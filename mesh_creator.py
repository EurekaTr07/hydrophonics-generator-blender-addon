import bpy
import bmesh
import math
from mathutils import Vector, Matrix

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
        # Unlink from all other collections
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        # Link to the target collection
        if obj.name not in collection.objects:
            collection.objects.link(obj)

class PotMesh(MeshGenerator):
    """Creates a single DWC pot/bucket."""
    def create(self, name, location, volume_liters):
        """
        Creates a pot mesh with a specified volume.

        Args:
            name (str): The name of the pot object.
            location (Vector): The location to create the pot at.
            volume_liters (float): The volume of the pot in liters.

        Returns:
            tuple: A tuple containing the pot object, its height, and its radius.
        """
        # Calculate dimensions from volume
        volume_m3 = volume_liters / 1000.0
        radius = (volume_m3 / (2.5 * math.pi)) ** (1 / 3)
        height = 2.5 * radius

        # Create a cylinder using bmesh (using create_cone for cylinder shape)
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            radius1=radius,
            radius2=radius,
            depth=height,
            segments=64
        )
        # The 'create_cone' operator modifies the bmesh 'bm' in place,
        # so there's no need to capture its return value for subsequent operations on 'bm'.

        # Remove the top face
        top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
        bmesh.ops.delete(bm, geom=[top_face], context='FACES')

        # Create the pot object
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        pot = bpy.data.objects.new(name, mesh)
        pot.location = location
        bpy.context.collection.objects.link(pot)

        # Add solidify modifier for wall thickness
        solidify = pot.modifiers.new(name="WallThickness", type='SOLIDIFY')
        solidify.thickness = 0.003
        solidify.offset = 1
        
        # Create the top rim
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

class PipeMesh(MeshGenerator):
    """Creates a straight pipe between two points."""
    def create(self, name, start_loc, end_loc):
        """
        Creates a pipe mesh between two locations.

        Args:
            name (str): The name of the pipe object.
            start_loc (Vector): The starting location of the pipe.
            end_loc (Vector): The ending location of the pipe.

        Returns:
            bpy.types.Object: The created pipe object.
        """
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
        """Returns the pipe diameter from the addon's properties."""
        pipe_props = self.props.pipe_props
        return float(pipe_props.pipe_size) / 1000.0

class TeeFittingMesh(FittingMesh):
    """Creates a high-detail T-fitting with sockets (main along X, branch along Y)."""
    def create(self, name, location, rotation=(0, 0, 0)):
        """
        Creates a T-fitting mesh with sockets.

        Args:
            name (str): The name of the fitting object.
            location (Vector): The location to create the fitting at.
            rotation (tuple): The rotation of the fitting.

        Returns:
            bpy.types.Object: The created T-fitting object.
        """
        diameter = self.get_diameter()
        radius = diameter / 2
        
        socket_outer_radius = radius * 1.2
        socket_length = diameter * 1.2 * 0.2
        
        arm_core_length = diameter * 0.75 # Core length of the arm before socket

        bm = bmesh.new()

        # Create main body mesh (horizontal pipe along X)
        bmesh.ops.create_cone(bm, radius1=radius, radius2=radius, depth=arm_core_length * 2, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'Y'))
        
        # Create branch body mesh (vertical pipe along Y)
        bmesh.ops.create_cone(bm, radius1=radius, radius2=radius, depth=arm_core_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation(Vector((0, arm_core_length / 2, 0))))

        # Create sockets for each of the three outlets
        # Socket 1: Negative X direction
        bmesh.ops.create_cone(bm, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation(Vector((-arm_core_length - socket_length / 2, 0, 0))))

        # Socket 2: Positive X direction
        bmesh.ops.create_cone(bm, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation(Vector((arm_core_length + socket_length / 2, 0, 0))))

        # Socket 3: Positive Y direction (branch)
        bmesh.ops.create_cone(bm, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation(Vector((0, arm_core_length + socket_length / 2, 0))))

        # Create the final object
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        
        fitting_obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(fitting_obj)

        # Set final object properties
        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation
        
        return fitting_obj

class ElbowFittingMesh(FittingMesh):
    """Creates a 90-degree elbow fitting with sockets (connects along +X and +Y)."""
    def create(self, name, location, rotation=(0, 0, 0)):
        """
        Creates a 90-degree elbow fitting mesh with sockets.

        Args:
            name (str): The name of the fitting object.
            location (Vector): The location to create the fitting at.
            rotation (tuple): The rotation of the fitting.

        Returns:
            bpy.types.Object: The created Elbow fitting object.
        """
        diameter = self.get_diameter()
        radius = diameter / 2
        
        socket_outer_radius = radius * 1.2
        socket_length = diameter * 1.2 * 0.2
        
        arm_core_length = diameter * 0.75 # Core length of the arm before socket
        
        bm = bmesh.new()

        # Create first arm (along X)
        bmesh.ops.create_cone(bm, radius1=radius, radius2=radius, depth=arm_core_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation(Vector((arm_core_length / 2, 0, 0))))
        
        # Create second arm (along Y)
        bmesh.ops.create_cone(bm, radius1=radius, radius2=radius, depth=arm_core_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation(Vector((0, arm_core_length / 2, 0))))

        # Create sockets
        # Socket 1: for Arm 1 (along +X)
        bmesh.ops.create_cone(bm, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'Y') @ Matrix.Translation(Vector((arm_core_length + socket_length / 2, 0, 0))))

        # Socket 2: for Arm 2 (along +Y)
        bmesh.ops.create_cone(bm, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32, matrix=Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation(Vector((0, arm_core_length + socket_length / 2, 0))))

        # Create the final object
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        
        fitting_obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(fitting_obj)

        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation
        
        return fitting_obj

class ElbowFittingMesh(FittingMesh):
    """Creates a 90-degree elbow fitting with sockets (connects along +X and +Y)."""
    def create(self, name, location, rotation=(0, 0, 0)):
        """
        Creates a 90-degree elbow fitting mesh with sockets.

        Args:
            name (str): The name of the fitting object.
            location (Vector): The location to create the fitting at.
            rotation (tuple): The rotation of the fitting.

        Returns:
            bpy.types.Object: The created Elbow fitting object.
        """
        diameter = self.get_diameter()
        radius = diameter / 2
        
        socket_outer_radius = radius * 1.2
        socket_length = diameter * 1.2 * 0.2
        
        arm_core_length = diameter * 0.75 # Core length of the arm before socket
        
        # Create first arm (along X)
        bm_arm1 = bmesh.new()
        bmesh.ops.create_cone(bm_arm1, radius1=radius, radius2=radius, depth=arm_core_length, segments=32)
        bmesh.ops.rotate(bm_arm1, cent=Vector((0,0,0)), matrix=Matrix.Rotation(math.radians(90), 3, 'Y'), verts=bm_arm1.verts)
        bmesh.ops.translate(bm_arm1, vec=Vector((arm_core_length / 2, 0, 0)), verts=bm_arm1.verts) # Position it along +X
        
        # Create second arm (along Y)
        bm_arm2 = bmesh.new()
        bmesh.ops.create_cone(bm_arm2, radius1=radius, radius2=radius, depth=arm_core_length, segments=32)
        bmesh.ops.rotate(bm_arm2, cent=Vector((0,0,0)), matrix=Matrix.Rotation(math.radians(90), 3, 'X'), verts=bm_arm2.verts) # Rotate to be along Y
        bmesh.ops.translate(bm_arm2, vec=Vector((0, arm_core_length / 2, 0)), verts=bm_arm2.verts) # Position it along +Y

        # Create sockets
        # Socket 1: for Arm 1 (along +X)
        bm_socket1 = bmesh.new()
        bmesh.ops.create_cone(bm_socket1, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32)
        bmesh.ops.rotate(bm_socket1, cent=Vector((0,0,0)), matrix=Matrix.Rotation(math.radians(90), 3, 'Y'), verts=bm_socket1.verts)
        bmesh.ops.translate(bm_socket1, vec=Vector((arm_core_length + socket_length / 2, 0, 0)), verts=bm_socket1.verts)

        # Socket 2: for Arm 2 (along +Y)
        bm_socket2 = bmesh.new()
        bmesh.ops.create_cone(bm_socket2, radius1=socket_outer_radius, radius2=socket_outer_radius, depth=socket_length, segments=32)
        bmesh.ops.rotate(bm_socket2, cent=Vector((0,0,0)), matrix=Matrix.Rotation(math.radians(90), 3, 'X'), verts=bm_socket2.verts)
        bmesh.ops.translate(bm_socket2, vec=Vector((0, arm_core_length + socket_length / 2, 0)), verts=bm_socket2.verts)

        # Combine all bmeshes into one final bmesh using bmesh.ops.join_geometry
        bm_final = bmesh.new()
        
        # Add geometry from each component bmesh to the final bmesh
        bmesh.ops.join_geometry(bm_final,
                                objects=[bm_arm1, bm_arm2, bm_socket1, bm_socket2],
                                discard_original=True) # Discard original bmeshes after joining

        # Free the original bmeshes (they are discarded by join_geometry, but good practice)
        bm_arm1.free()
        bm_arm2.free()
        bm_socket1.free()
        bm_socket2.free()

        # Create the final object
        mesh = bpy.data.meshes.new(name)
        bm_final.to_mesh(mesh)
        bm_final.free()
        
        fitting_obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(fitting_obj)

        fitting_obj.location = location
        fitting_obj.rotation_euler = rotation
        
        return fitting_obj

def register():
    """This file does not need to register any classes."""
    pass

def unregister():
    """This file does not need to unregister any classes."""
    pass
