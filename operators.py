import bpy
import math
from mathutils import Vector, Euler

from . import mesh_creator
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
        collection_names = ["Pots", "Pipes", "Fittings", "System", "Reservoir", "BalanceBucket"]
        for col_name in collection_names:
            if col_name in bpy.data.collections:
                collection = bpy.data.collections[col_name]
                for obj in list(collection.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)
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
        elbow_gen = mesh_creator.ElbowFittingMesh(scene_props)
        bucket_gen = mesh_creator.BalanceBucketMesh(scene_props)
        
        # Create collections
        pots_collection = pot_gen._create_collection("Pots")
        pipes_collection = pipe_gen._create_collection("Pipes")
        fittings_collection = tee_gen._create_collection("Fittings")
        system_collection = pot_gen._create_collection("System")
        bucket_collection = bucket_gen._create_collection("BalanceBucket")

        # --- Calculate Dimensions ---
        pot_volume = float(scene_props.pot_props.volume)
        _, pot_height, pot_radius = pot_gen.create("temp_pot", (0,0,0), pot_volume)
        bpy.data.objects.remove(bpy.data.objects['temp_pot'])

        pipe_z = pot_height * 0.15
        pipe_diameter = tee_gen.get_diameter()
        
        tee_arm_core_length = pipe_diameter * 0.8
        tee_socket_length = pipe_diameter * 0.6
        pipe_insertion_depth = tee_socket_length * 0.4 
        tee_arm_total_length = tee_arm_core_length + tee_socket_length

        # --- Create Balance Bucket ---
        bb_x = -layout.spacing_x * 1.2
        bb_y = ((layout.rows - 1) * layout.spacing_y) / 2.0
        bb_loc = Vector((bb_x, bb_y, pot_height / 2.0))
        balance_bucket, _, bb_rad = bucket_gen.create("BalanceBucket", bb_loc, pot_volume)
        bucket_gen._link_to_collection(balance_bucket, bucket_collection)

        # Manifold Y positions
        manifold_y_in = (layout.rows - 1) * layout.spacing_y + layout.spacing_y * 0.8
        manifold_y_out = -layout.spacing_y * 0.8
        
        # --- Create Manifolds ---
        for c in range(layout.columns):
            loc_x = c * layout.spacing_x
            tee_in_loc = Vector((loc_x, manifold_y_in, pipe_z))
            tee_out_loc = Vector((loc_x, manifold_y_out, pipe_z))
            
            tee_in = tee_gen.create(f"Tee_Inlet_{c}", tee_in_loc, (0, 0, math.radians(180)))
            tee_out = tee_gen.create(f"Tee_Outlet_{c}", tee_out_loc, (0, 0, 0))
            
            tee_gen._link_to_collection(tee_in, fittings_collection)
            tee_gen._link_to_collection(tee_out, fittings_collection)

            if c > 0:
                prev_loc_x = (c - 1) * layout.spacing_x
                pipe_start_x = prev_loc_x + tee_arm_total_length - pipe_insertion_depth
                pipe_end_x = loc_x - tee_arm_total_length + pipe_insertion_depth
                inlet_pipe = pipe_gen.create(f"Manifold_Pipe_In_{c-1}", Vector((pipe_start_x, manifold_y_in, pipe_z)), Vector((pipe_end_x, manifold_y_in, pipe_z)))
                outlet_pipe = pipe_gen.create(f"Manifold_Pipe_Out_{c-1}", Vector((pipe_start_x, manifold_y_out, pipe_z)), Vector((pipe_end_x, manifold_y_out, pipe_z)))
                if inlet_pipe: pipe_gen._link_to_collection(inlet_pipe, pipes_collection)
                if outlet_pipe: pipe_gen._link_to_collection(outlet_pipe, pipes_collection)

        # --- Create Pots and Connect them in Series per Column ---
        for c in range(layout.columns):
            loc_x = c * layout.spacing_x
            
            # Get the manifold connection points for this column from the T-fittings
            manifold_in_connect_point = Vector((loc_x, manifold_y_in - tee_arm_total_length + pipe_insertion_depth, pipe_z))
            manifold_out_connect_point = Vector((loc_x, manifold_y_out + tee_arm_total_length - pipe_insertion_depth, pipe_z))

            # Keep track of the previous pot's bottom connection point to chain them together
            prev_pot_out_connect_point = None

            for r in range(layout.rows):
                loc_y = r * layout.spacing_y
                pot_loc = Vector((loc_x, loc_y, pot_height / 2.0))
                
                pot_obj, _, pot_rad = pot_gen.create(f"Pot_{r}_{c}", pot_loc, pot_volume)
                pot_gen._link_to_collection(pot_obj, pots_collection)

                # Define connection points for the current pot (+Y is top, -Y is bottom)
                current_pot_in_connect_point = Vector((loc_x, loc_y + pot_rad, pipe_z))
                current_pot_out_connect_point = Vector((loc_x, loc_y - pot_rad, pipe_z))

                if r == 0:
                    # First pot in the column: connect from inlet manifold to top of the pot
                    inlet_pipe = pipe_gen.create(f"Column_Pipe_In_{c}", manifold_in_connect_point, current_pot_in_connect_point)
                    if inlet_pipe: pipe_gen._link_to_collection(inlet_pipe, pipes_collection)
                else:
                    # Subsequent pots: connect from bottom of previous pot to top of current pot
                    inter_pot_pipe = pipe_gen.create(f"Inter_Pot_Pipe_{r-1}_{c}", prev_pot_out_connect_point, current_pot_in_connect_point)
                    if inter_pot_pipe: pipe_gen._link_to_collection(inter_pot_pipe, pipes_collection)

                # Update the connection point for the next pot in the chain
                prev_pot_out_connect_point = current_pot_out_connect_point

                if r == layout.rows - 1:
                    # Last pot in the column: connect from bottom of the pot to outlet manifold
                    outlet_pipe = pipe_gen.create(f"Column_Pipe_Out_{c}", current_pot_out_connect_point, manifold_out_connect_point)
                    if outlet_pipe: pipe_gen._link_to_collection(outlet_pipe, pipes_collection)

        # --- Connect Manifolds to Balance Bucket ---
        # This logic creates the 'H' shaped connection from the drawing
        
        # 1. Define the central X-coordinate for the connection
        # Place it in the middle of the grid
        if layout.columns > 1:
            connect_x = (layout.columns - 1) * layout.spacing_x / 2.0
        else:
            connect_x = 0

        # 2. Create T-fittings on the main manifolds that will branch towards the balance bucket
        # Inlet manifold T-fitting, branch pointing down (-Y)
        tee_bb_in_loc = Vector((connect_x, manifold_y_in, pipe_z))
        tee_bb_in = tee_gen.create("Tee_BB_In", tee_bb_in_loc, (0, 0, math.radians(180)))
        tee_gen._link_to_collection(tee_bb_in, fittings_collection)
        
        # Outlet manifold T-fitting, branch pointing up (+Y)
        tee_bb_out_loc = Vector((connect_x, manifold_y_out, pipe_z))
        tee_bb_out = tee_gen.create("Tee_BB_Out", tee_bb_out_loc, (0, 0, 0))
        tee_gen._link_to_collection(tee_bb_out, fittings_collection)

        # 3. Create the central T-fitting that joins the branches from the manifolds
        central_tee_y = (manifold_y_in + manifold_y_out) / 2.0
        central_tee_loc = Vector((connect_x, central_tee_y, pipe_z))
        # This tee's main line is vertical (Y-axis), branch points left (-X) to the bucket
        central_tee = tee_gen.create("Tee_Central_Connector", central_tee_loc, (0, 0, math.radians(-90)))
        tee_gen._link_to_collection(central_tee, fittings_collection)

        # 4. Connect the manifold tees to the central tee
        # Pipe from inlet manifold tee to central tee
        pipe_in_to_central = pipe_gen.create("Pipe_In_to_Central", 
                                             tee_bb_in_loc + Vector((0, -pipe_insertion_depth, 0)), 
                                             central_tee_loc + Vector((0, tee_arm_total_length - pipe_insertion_depth, 0)))
        if pipe_in_to_central: pipe_gen._link_to_collection(pipe_in_to_central, pipes_collection)

        # Pipe from outlet manifold tee to central tee
        pipe_out_to_central = pipe_gen.create("Pipe_Out_to_Central",
                                               tee_bb_out_loc + Vector((0, pipe_insertion_depth, 0)),
                                               central_tee_loc - Vector((0, tee_arm_total_length - pipe_insertion_depth, 0)))
        if pipe_out_to_central: pipe_gen._link_to_collection(pipe_out_to_central, pipes_collection)

        # 5. Connect the central tee to the balance bucket
        pipe_central_to_bb = pipe_gen.create("Pipe_Central_to_BB",
                                             central_tee_loc - Vector((tee_arm_total_length - pipe_insertion_depth, 0, 0)),
                                             Vector((bb_loc.x + bb_rad, central_tee_y, pipe_z)))
        if pipe_central_to_bb: pipe_gen._link_to_collection(pipe_central_to_bb, pipes_collection)


        # --- Create Reservoir and Connect to Balance Bucket ---
        res_obj = None
        if scene_props.enable_reservoir:
            reservoir_gen = mesh_creator.ReservoirMesh(scene_props)
            reservoir_volume = float(scene_props.reservoir_props.volume)
            
            # Place reservoir to the left of the balance bucket
            reservoir_x = bb_loc.x - layout.spacing_x
            reservoir_y = bb_loc.y
            
            res_obj, res_height, res_rad = reservoir_gen.create("Reservoir", (0,0,0), reservoir_volume)
            res_obj.location = Vector((reservoir_x, reservoir_y, res_height / 2.0))
            
            reservoir_collection = reservoir_gen._create_collection("Reservoir")
            reservoir_gen._link_to_collection(res_obj, reservoir_collection)

            # Connect Reservoir to the side of the Balance Bucket
            res_connect_point = Vector((reservoir_x + res_rad, reservoir_y, pipe_z))
            bb_res_connect_point = Vector((bb_loc.x - bb_rad, bb_loc.y, pipe_z))
            pipe_res_to_bb = pipe_gen.create("Pipe_Res_to_BB", res_connect_point, bb_res_connect_point)
            if pipe_res_to_bb: pipe_gen._link_to_collection(pipe_res_to_bb, pipes_collection)

        # --- Finalize Model ---
        if scene_props.create_connections:
            all_objects = list(pots_collection.objects) + list(pipes_collection.objects) + list(fittings_collection.objects) + list(bucket_collection.objects)
            if res_obj:
                all_objects.append(res_obj)
            
            if not all_objects:
                return {'FINISHED'}
            
            for obj in fittings_collection.objects:
                bpy.context.view_layer.objects.active = obj
                for mod in list(obj.modifiers):
                     bpy.ops.object.modifier_apply(modifier=mod.name)

            bpy.ops.object.select_all(action='DESELECT')
            for obj in all_objects:
                obj.select_set(True)

            if bpy.context.selected_objects:
                bpy.context.view_layer.objects.active = all_objects[0]
                bpy.ops.object.join()
                
                final_system = bpy.context.active_object
                final_system.name = "RDWC_System"
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles(threshold=0.001) 
                bpy.ops.mesh.normals_make_consistent(inside=False)
                bpy.ops.object.mode_set(mode='OBJECT')

                if scene_props.optimize_model:
                    bpy.context.view_layer.objects.active = final_system
                    bpy.ops.object.shade_smooth()
                    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))

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