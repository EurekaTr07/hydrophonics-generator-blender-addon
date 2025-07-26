import bpy
import math
from mathutils import Vector, Euler

from . import mesh_creator
from .mesh_creator import ElbowFittingMesh # Import the new ElbowFittingMesh

from bpy.types import Operator

# =================================================================================================
# OPERATOR
# =================================================================================================

class WM_OT_hydroponics_generator(Operator):
    """Main operator to generate the hydroponic system."""
    bl_idname = "wm.hydroponics_generator"
    bl_label = "Generate System"
    bl_options = {'REGISTER', 'UNDO'}

    def _clear_previous(self):
        """Removes any previously generated system objects and collections."""
        for col_name in ["Pots", "Pipes", "System"]:
            if col_name in bpy.data.collections:
                collection = bpy.data.collections[col_name]
                for obj in list(collection.objects): bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(collection)

    def execute(self, context):
        """Generates the entire RDWC system based on scene properties."""
        scene_props = context.scene.hydroponics_props
        layout = scene_props.layout_props
        self._clear_previous()

        # Initialize mesh generators
        pot_gen = mesh_creator.PotMesh(scene_props)
        pipe_gen = mesh_creator.PipeMesh(scene_props)
        tee_gen = mesh_creator.TeeFittingMesh(scene_props)
        elbow_gen = mesh_creator.ElbowFittingMesh(scene_props) # Initialize ElbowFittingMesh
        
        # Create collections to organize objects
        pots_collection = pot_gen._create_collection("Pots")
        pipes_collection = pipe_gen._create_collection("Pipes")
        system_collection = pot_gen._create_collection("System")

        # Get pot dimensions by creating a temporary pot
        pot_volume = float(scene_props.pot_props.volume)
        _, pot_height, pot_radius = pot_gen.create("temp_pot", (0,0,0), pot_volume)
        bpy.data.objects.remove(bpy.data.objects['temp_pot'])

        # --- Calculate critical dimensions and offsets ---
        pipe_z = pot_height * 0.1  # Pipe height relative to pot height
        grid_width = (layout.columns - 1) * layout.spacing_x
        pipe_diameter = tee_gen.get_diameter()
        tee_arm_core_length = pipe_diameter * 0.75
        tee_socket_length = pipe_diameter * 1.2 * 0.2
        pipe_insertion_depth = tee_socket_length / 2 # How deep the pipe goes into the socket

        # Manifold Y positions
        manifold_y_in = (layout.rows - 1) * layout.spacing_y + layout.spacing_y / 2
        manifold_y_out = -layout.spacing_y / 2
        
        # --- Create Manifold Pipes ---
        # The manifold pipes connect between T-fittings.
        # The length of the pipe segment should account for the tee's arm core length and half of the socket length on each side.
        # So, the pipe starts after the first tee's socket and ends before the next tee's socket.
        
        # The x_start and x_end for manifold pipes need to be adjusted to connect to the inner part of the tee sockets.
        # The tee is centered at c * layout.spacing_x.
        # The socket extends from tee_arm_core_length to tee_arm_core_length + tee_socket_length.
        # The pipe should connect at tee_arm_core_length + pipe_insertion_depth.

        for c in range(layout.columns - 1):
            # For the inlet manifold
            # Start from the end of the previous tee's socket (or start of the first tee's socket)
            # End at the beginning of the next tee's socket (or end of the last tee's socket)
            
            # The tee at c * layout.spacing_x has its right arm at c * layout.spacing_x + tee_arm_core_length + pipe_insertion_depth
            # The tee at (c+1) * layout.spacing_x has its left arm at (c+1) * layout.spacing_x - (tee_arm_core_length + pipe_insertion_depth)
            
            x_start_manifold = c * layout.spacing_x + tee_arm_core_length + pipe_insertion_depth
            x_end_manifold = (c + 1) * layout.spacing_x - (tee_arm_core_length + pipe_insertion_depth)

            inlet_segment = pipe_gen.create(f"Manifold_Inlet_{c}", Vector((x_start_manifold, manifold_y_in, pipe_z)), Vector((x_end_manifold, manifold_y_in, pipe_z)))
            outlet_segment = pipe_gen.create(f"Manifold_Outlet_{c}", Vector((x_start_manifold, manifold_y_out, pipe_z)), Vector((x_end_manifold, manifold_y_out, pipe_z)))
            pipe_gen._link_to_collection(inlet_segment, pipes_collection)
            pipe_gen._link_to_collection(outlet_segment, pipes_collection)

        # --- Create Pots and Connecting Pipes ---
        for r in range(layout.rows):
            for c in range(layout.columns):
                loc_x = c * layout.spacing_x
                loc_y = r * layout.spacing_y
                pot_loc = Vector((loc_x, loc_y, pot_height / 2.0))
                pot_obj, _, pot_rad = pot_gen.create(f"Pot_{r}_{c}", pot_loc, pot_volume)
                pot_gen._link_to_collection(pot_obj, pots_collection)

                # Inlet pipe from manifold to pot (using Elbow)
                elbow_in_loc = Vector((loc_x, manifold_y_in, pipe_z))
                # The elbow connects +X and +Y. For inlet, we need it to connect from manifold (along X) to pot (along -Y).
                # So, rotate it by -90 degrees around Z to align +Y with -Y.
                elbow_in = elbow_gen.create(f"Elbow_Inlet_{r}_{c}", elbow_in_loc, (0,0,math.radians(-90)))
                
                # Pipe starts from the elbow's -Y socket (which is now aligned with manifold_y_in)
                # and connects to the pot.
                pipe_start_loc_in = elbow_in_loc + Vector((0, -(tee_arm_core_length + pipe_insertion_depth), 0))
                pipe_end_loc_in = pot_loc + Vector((0, -pot_rad, 0))
                pipe_end_loc_in.z = pipe_z # Ensure pipe is at the correct Z height
                pipe_in = pipe_gen.create(f"Pipe_Inlet_{r}_{c}", pipe_start_loc_in, pipe_end_loc_in)
                elbow_gen._link_to_collection(elbow_in, pipes_collection)
                pipe_gen._link_to_collection(pipe_in, pipes_collection)
                
                # Outlet pipe from pot to manifold (using Elbow)
                elbow_out_loc = Vector((loc_x, manifold_y_out, pipe_z))
                # The elbow connects +X and +Y. For outlet, we need it to connect from pot (along +Y) to manifold (along X).
                # So, rotate it by 90 degrees around Z to align +Y with +Y.
                elbow_out = elbow_gen.create(f"Elbow_Outlet_{r}_{c}", elbow_out_loc, (0,0,math.radians(90)))
                
                # Pipe starts from the pot and connects to the elbow's +Y socket
                pipe_start_loc_out = pot_loc + Vector((0, pot_rad, 0))
                pipe_start_loc_out.z = pipe_z # Ensure pipe is at the correct Z height
                pipe_end_loc_out = elbow_out_loc + Vector((0, (tee_arm_core_length + pipe_insertion_depth), 0))
                pipe_out = pipe_gen.create(f"Pipe_Outlet_{r}_{c}", pipe_start_loc_out, pipe_end_loc_out)
                elbow_gen._link_to_collection(elbow_out, pipes_collection)
                pipe_gen._link_to_collection(pipe_out, pipes_collection)

        # --- Create Balance Tank ---
        center_x = grid_width / 2.0
        balance_y = manifold_y_out - layout.spacing_y
        balance_loc = Vector((center_x, balance_y, pot_height / 2.0))
        balance_tank, _, _ = pot_gen.create("Balance_Tank", balance_loc, pot_volume)
        pot_gen._link_to_collection(balance_tank, pots_collection)

        # Connect manifolds to the balance tank location
        pipe_in_to_balance = pipe_gen.create("Pipe_ManifoldInlet_Balance", Vector((center_x, manifold_y_in, pipe_z)), balance_loc.xy.to_3d() + Vector((0,0,pipe_z)))
        pipe_out_from_balance = pipe_gen.create("Pipe_ManifoldOutlet_Balance", balance_loc.xy.to_3d() + Vector((0,0,pipe_z)), Vector((center_x, manifold_y_out, pipe_z)))
        pipe_gen._link_to_collection(pipe_in_to_balance, pipes_collection)
        pipe_gen._link_to_collection(pipe_out_from_balance, pipes_collection)

        # --- Create Main Reservoir (Optional) ---
        if scene_props.enable_reservoir:
            reservoir_volume = float(scene_props.reservoir_props.volume)
            reservoir_loc = Vector((center_x, balance_y - layout.spacing_y, 0))
            reservoir, res_h, _ = pot_gen.create("Main_Reservoir", reservoir_loc, reservoir_volume)
            reservoir.location.z = res_h / 2.0
            pot_gen._link_to_collection(reservoir, pots_collection)

            # These pipes are illustrative; real system would have pumps
            pipe_res_to_balance = pipe_gen.create("Pipe_Reservoir_Inlet", reservoir.location, balance_tank.location)
            pipe_balance_to_res = pipe_gen.create("Pipe_Reservoir_Outlet", balance_tank.location, reservoir.location)
            pipe_gen._link_to_collection(pipe_res_to_balance, pipes_collection)
            pipe_gen._link_to_collection(pipe_balance_to_res, pipes_collection)

        # --- Finalize Model: Join and Optimize ---
        if scene_props.create_connections:
            all_objects = [obj for obj in list(pots_collection.objects) + list(pipes_collection.objects) if obj is not None]
            if not all_objects:
                return {'FINISHED'}
            
            # Apply all modifiers before joining
            for obj in all_objects:
                if obj.type == 'MESH' and obj.modifiers:
                    bpy.context.view_layer.objects.active = obj
                    for mod in list(obj.modifiers):
                        bpy.ops.object.modifier_apply(modifier=mod.name)

            # Select all objects and join them
            bpy.ops.object.select_all(action='DESELECT')
            for obj in all_objects:
                obj.select_set(True)

            if bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = all_objects[0]
                bpy.ops.object.join()
                
                final_system = bpy.context.active_object
                
                # Clean up geometry
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles(threshold=0.001)
                bpy.ops.object.mode_set(mode='OBJECT')

                # Optimize final mesh appearance
                if scene_props.optimize_model:
                    bpy.context.view_layer.objects.active = final_system
                    bpy.ops.object.shade_smooth()

                # Move the final joined object to the 'System' collection
                pot_gen._link_to_collection(final_system, system_collection)

        self.report({'INFO'}, "RDWC Manifold System Generated")
        return {'FINISHED'}

classes = (
    WM_OT_hydroponics_generator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
