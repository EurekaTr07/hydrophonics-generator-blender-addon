# AgroFlow RDWC System Generator - Blender Addon

This Blender addon, developed for AgroFlow, enables users to quickly and easily create 3D models of Recirculating Deep Water Culture (RDWC) hydroponic systems. The addon is designed to produce clean, optimized, and parametric models suitable for 3D printing.

## Uses Blender 4.4 => always keep the code compitable to this.
**Note:** The user interface of this addon is in Turkish.

---

## ✨ Key Features

- **Parametric Design:** Easily configure system parameters such as the number of rows and columns, pot spacing, bucket volume, and pipe diameter through a user-friendly interface.
- **Realistic Manifold System:** Generates a professional manifold system with a central balance tank for water distribution and collection, ensuring equal flow to each pot.
- **High-Detail Parts:** The system includes realistic T-pieces and 90° elbows with nut and socket designs, not just simple pipes.
- **Precise "Snap" Logic:** All pipes and fittings are designed to snap together perfectly, resulting in a geometrically accurate and seamless model.
- **Standardized Components:**
  - **Bucket Volume:** Choose from standard bucket sizes (e.g., 10L, 19L, 25L).
  - **Pipe Diameter:** Select from common PVC and metric pipe diameters.
- **Automatic Optimization:** A one-click option to reduce the polygon count of the model, improving performance and providing a smoother appearance.

---

## 🚀 Installation

Since the addon is structured with multiple files, it must be installed from a `.zip` archive.

1.  **Prepare the Folder:** Ensure all addon files (`__init__.py`, `mesh_creator.py`, `properties.py`, `operators.py`, `ui.py`) are inside a folder named `hydrophonics_generator`.
2.  **Create a ZIP Archive:** Compress the `hydrophonics_generator` folder into a `.zip` file.
3.  **Install in Blender:**
    - Open Blender and navigate to `Edit > Preferences > Add-ons`.
    - Click the **Install...** button and select the `.zip` file you created.
    - The addon will appear in the list as "Hydroponics System Generator (RDWC)". Enable it by checking the box.

---

## 📋 How to Use

1.  **Open the Panel:** In the 3D Viewport, press the `N` key to open the side panel.
2.  **Find the Tab:** A new tab named "Hydroponics" will be available in the side panel.
3.  **Adjust Parameters:**
    - **System Layout:** Set the number of rows and columns and the distance between pots.
    - **Pot Properties:** Choose a standard bucket volume.
    - **Pipe Properties:** Select the pipe standard (Turkish PVC / Metric) and diameter.
    - **Main Reservoir:** Optionally, enable and configure the main reservoir.
4.  **Generation Options:**
    - **Join Pipe Connections:** Merge all components into a single, unified model.
    - **Optimize Model:** Clean the geometry and improve performance (recommended).
5.  **Generate the System:** After configuring the settings, click the **Generate System** button. The model will be created in your scene.
