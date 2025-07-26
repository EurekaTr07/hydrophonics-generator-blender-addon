import os
import sys
import zipfile
import shutil
import platform
import subprocess
import time # Import time for potential delays

def kill_blender_process():
    """
    Kills any running Blender processes on Windows.
    """
    print("Attempting to kill any running Blender processes...")
    if platform.system() == "Windows":
        try:
            # Use taskkill to forcefully terminate blender.exe
            subprocess.run(["taskkill", "/F", "/IM", "blender.exe"], check=False, capture_output=True)
            print("Blender process killed (if running).")
        except Exception as e:
            print(f"Error killing Blender process: {e}")
    else:
        print("Killing Blender process is currently only supported on Windows.")

def find_blender_executable():
    """
    Finds the Blender executable on Windows.
    """
    # Common installation paths for Blender
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    blender_root = os.path.join(program_files, "Blender Foundation")

    if not os.path.exists(blender_root):
        return None

    # Find the latest version of Blender
    latest_version_dir = ""
    for dir_name in sorted(os.listdir(blender_root), reverse=True):
        if "Blender" in dir_name and os.path.isdir(os.path.join(blender_root, dir_name)):
            latest_version_dir = os.path.join(blender_root, dir_name)
            break
    
    if not latest_version_dir:
        return None

    blender_exe = os.path.join(latest_version_dir, "blender.exe")
    if os.path.exists(blender_exe):
        return blender_exe
    
    return None

def get_blender_addon_paths():
    """
    Auto-detects Blender addon directories for the current operating system.
    """
    local_app_data = os.environ.get("APPDATA")
    if not local_app_data:
        return []

    blender_path = os.path.join(local_app_data, "Blender Foundation", "Blender")
    if not os.path.exists(blender_path):
        return []

    addon_paths = []
    for version_dir in os.listdir(blender_path):
        version_path = os.path.join(blender_path, version_dir)
        if os.path.isdir(version_path):
            scripts_path = os.path.join(version_path, "scripts", "addons")
            if os.path.exists(scripts_path):
                addon_paths.append(scripts_path)
    
    return addon_paths

def zip_addon_files(zip_name, files_to_zip):
    """
    Zips the necessary addon files.
    """
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_zip:
            zipf.write(file)
    print(f"Addon zipped to '{zip_name}'")

def install_addon(zip_name, addon_paths, addon_name):
    """
    Installs the addon by unzipping it into the Blender addon directories.
    """
    if not addon_paths:
        print("Could not find Blender addon directories.")
        return

    for path in addon_paths:
        install_path = os.path.join(path, addon_name)
        
        # Remove old version if it exists
        if os.path.exists(install_path):
            print(f"Removing existing addon at '{install_path}'")
            shutil.rmtree(install_path)
            
        print(f"Creating directory '{install_path}'")
        os.makedirs(install_path, exist_ok=True)
        
        try:
            print(f"Extracting '{zip_name}' to '{install_path}'")
            with zipfile.ZipFile(zip_name, 'r') as zip_ref:
                zip_ref.extractall(install_path)
            print(f"Addon successfully installed to '{path}'")
        except Exception as e:
            print(f"Could not install addon to '{path}': {e}")
    
    # Clean up the zip file
    if os.path.exists(zip_name):
        os.remove(zip_name)
        print(f"Removed temporary zip file: '{zip_name}'")

def enable_addon_with_blender(blender_exe, addon_name):
    """
    Uses Blender's command line to enable the addon.
    """
    if not blender_exe:
        print("Blender executable not found. Cannot enable addon automatically.")
        print("Please enable it manually in Blender's preferences.")
        return

    print(f"Found Blender executable: {blender_exe}")
    
    # Create a temporary python script to enable the addon
    script_content = f"""
import bpy
try:
    print(f"Enabling addon: {addon_name}")
    bpy.ops.preferences.addon_enable(module='{addon_name}')
    bpy.ops.wm.save_userpref()
    print("Addon enabled and preferences saved.")
except Exception as e:
    print(f"Failed to enable addon: {{e}}")
"""
    
    script_path = "temp_enable_addon.py"
    with open(script_path, "w") as f:
        f.write(script_content)

    print("Running Blender in background to enable the addon...")
    try:
        subprocess.run([blender_exe, "--background", "--python", script_path], check=True, capture_output=True, text=True)
        print("Blender script executed successfully.")
    except subprocess.CalledProcessError as e:
        print("Error running Blender script:")
        print(e.stdout)
        print(e.stderr)
    except FileNotFoundError:
        print(f"Error: Could not find '{blender_exe}'. Please check the path.")
    finally:
        # Clean up the temporary script
        if os.path.exists(script_path):
            os.remove(script_path)
            print(f"Removed temporary script: '{script_path}'")

def launch_blender_new_project(blender_exe):
    """
    Launches Blender with a new general project.
    """
    if not blender_exe:
        print("Blender executable not found. Cannot launch Blender.")
        return

    print("Launching Blender with a new general project...")
    try:
        # Launch Blender without any specific file to open a new default project
        subprocess.Popen([blender_exe])
        print("Blender launched successfully.")
    except FileNotFoundError:
        print(f"Error: Could not find '{blender_exe}'. Please check the path.")
    except Exception as e:
        print(f"Error launching Blender: {e}")


if __name__ == "__main__":
    # Kill any running Blender processes before installation
    kill_blender_process()
    time.sleep(2) # Give Blender a moment to close

    addon_files = [
        "__init__.py",
        "mesh_creator.py",
        "operators.py",
        "properties.py",
        "ui.py",
    ]
    
    # Get the addon name from the current directory name
    addon_name = os.path.basename(os.path.abspath(os.path.dirname(__file__)))
    zip_name = f"{addon_name}.zip"

    zip_addon_files(zip_name, addon_files)
    
    blender_addon_paths = get_blender_addon_paths()
    install_addon(zip_name, blender_addon_paths, addon_name)

    # Find blender and enable the addon
    blender_executable = find_blender_executable()
    enable_addon_with_blender(blender_executable, addon_name)

    # Launch Blender with a new general project after successful installation
    launch_blender_new_project(blender_executable)
