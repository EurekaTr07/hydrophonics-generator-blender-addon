bl_info = {
    "name": "Hydroponics System Generator (RDWC)",
    "author": "Gemini & AgroFlow",
    "version": (2, 2, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Hydroponics",
    "description": "Creates professional RDWC systems with high-detail fittings and precise snap logic.",
    "warning": "",
    "doc_url": "https://github.com/your_repo_link_here",  # Optional: Add your documentation link
    "category": "Add Mesh",
}

from . import properties, mesh_creator, operators, ui

import bpy
from bpy.props import PointerProperty

addon_keymaps = []

def register():
    """Registers the addon with Blender."""
    # Register the other modules first
    properties.register()
    mesh_creator.register()
    operators.register()
    ui.register()
    
    # Add the main properties to the scene
    bpy.types.Scene.hydroponics_props = PointerProperty(type=properties.HydroponicsSystemProperties)

    # Add keymap for Ctrl+K
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='Window', space_type='WINDOW')
        kmi = km.keymap_items.new('wm.hydroponics_generator', type='K', ctrl=True, shift=False, alt=False)
        addon_keymaps.append(km)

def unregister():
    """Unregisters the addon from Blender."""
    # Delete the main properties from the scene
    if hasattr(bpy.types.Scene, 'hydroponics_props'):
        del bpy.types.Scene.hydroponics_props
        
    # Unregister keymaps
    wm = bpy.context.window_manager
    for km in addon_keymaps:
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

    # Unregister modules in reverse order
    ui.unregister()
    operators.unregister()
    mesh_creator.unregister()
    properties.unregister()

if __name__ == "__main__":
    register()
