bl_info = {
    "name": "Hydroponics System Generator (RDWC)",
    "author": "Gemini & AgroFlow",
    "version": (2, 3, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Hydroponics",
    "description": "Creates professional RDWC systems with lighting calculation.",
    "warning": "",
    "doc_url": "",
    "category": "Add Mesh",
}

import bpy
from bpy.props import PointerProperty
import json
import os

from . import properties, mesh_creator, operators, ui

# --- Addon Configuration Loading ---
def load_config():
    """Loads the config.json file from the addon's directory."""
    addon_dir = os.path.dirname(__file__)
    config_path = os.path.join(addon_dir, "config.json")
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Hydroponics Addon: Error reading config.json. File might be corrupted.")
                return None
    else:
        print(f"Hydroponics Addon: config.json not found at {config_path}")
        return None

# Store config globally within the addon
addon_config = load_config()


addon_keymaps = []

def register():
    """Registers the addon with Blender."""
    # Register the other modules first
    properties.register()
    mesh_creator.register()
    operators.register()
    ui.register()
    
    # Pass the loaded config to the scene properties
    bpy.types.Scene.hydroponics_props = PointerProperty(type=properties.HydroponicsSystemProperties)
    
    # Store config in a place accessible by operators/panels
    # This makes it available without passing it around constantly
    bpy.types.Scene.hydroponics_config = addon_config


def unregister():
    """Unregisters the addon from Blender."""
    if hasattr(bpy.types.Scene, 'hydroponics_props'):
        del bpy.types.Scene.hydroponics_props
    if hasattr(bpy.types.Scene, 'hydroponics_config'):
        del bpy.types.Scene.hydroponics_config
        
    # Unregister keymaps and modules
    # (The rest of your unregister function remains the same)
    for km in addon_keymaps:
        bpy.context.window_manager.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()
    
    ui.unregister()
    operators.unregister()
    mesh_creator.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()