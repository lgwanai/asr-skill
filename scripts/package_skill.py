#!/usr/bin/env python3
import os
import zipfile
import datetime
import shutil

def package_skill():
    """
    Packages the 'skills/asr' directory into a zip file with date-based versioning.
    The output zip is saved to the 'dist' directory.
    """
    # Configuration
    # Assumes script is located in /scripts/ relative to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(project_root, "skills", "asr")
    dist_dir = os.path.join(project_root, "dist")
    
    # Generate versioned filename (e.g., asr-skill-20240314.zip)
    today = datetime.datetime.now().strftime("%Y%m%d")
    zip_filename = f"asr-skill-{today}.zip"
    zip_filepath = os.path.join(dist_dir, zip_filename)

    # Create dist directory if it doesn't exist
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
        print(f"Created directory: {dist_dir}")

    # Files/Directories to ignore
    ignore_patterns = {
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        ".git",
        ".gitignore",
        ".idea",
        ".vscode"
    }

    print(f"Packaging {source_dir} into {zip_filepath}...")

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through the source directory
            for root, dirs, files in os.walk(source_dir):
                # Modify dirs in-place to skip ignored directories
                dirs[:] = [d for d in dirs if d not in ignore_patterns]
                
                for file in files:
                    if file in ignore_patterns or file.endswith('.pyc') or file == ".DS_Store":
                        continue
                        
                    file_path = os.path.join(root, file)
                    # Calculate arcname (relative path inside the zip)
                    # We want the zip to contain the 'asr' folder at the root
                    # relpath(skills/asr/foo.py, skills) -> asr/foo.py
                    rel_path = os.path.relpath(file_path, os.path.dirname(source_dir))
                    
                    print(f"Adding: {rel_path}")
                    zipf.write(file_path, rel_path)
        
        print(f"\nSuccess! Package created at:\n{zip_filepath}")
        
    except Exception as e:
        print(f"\nError: Failed to create package. {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    package_skill()
