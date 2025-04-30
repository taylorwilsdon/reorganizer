# utils/organizer.py
"""
Contains logic for organizing files based on an LLM-generated plan.
"""

import os
import shutil # Using shutil for potentially more robust moves later if needed
from typing import List, Dict, Any, Tuple

# Assuming FileMeta is defined in file_scanner and scan is available
try:
    from .file_scanner import FileMeta # Only need FileMeta potentially for type hints if used
except ImportError:
    print("Warning: Could not import FileMeta from relative path.")
    class FileMeta: pass


def organize_files(organization_plan: List[Dict[str, str]], scan_path: str) -> Tuple[int, List[str]]:
    """
    Organizes files in the scan path based on the provided LLM-generated plan.

    Args:
        organization_plan: A list of dictionaries, where each dict has
                           'source': relative path of the file to move,
                           'destination': relative path of the target location.
        scan_path: The absolute path of the directory that was scanned.

    Returns:
        A tuple containing:
        - moved_count (int): Number of files successfully moved.
        - errors (List[str]): A list of error messages encountered during organization.
    """
    if not scan_path or not os.path.isdir(scan_path):
        return 0, [f"Error: Invalid scan path provided: {scan_path}"]
    if not isinstance(organization_plan, list):
         return 0, [f"Error: Invalid organization plan format (expected list, got {type(organization_plan)})"]

    moved_count = 0
    errors = []
    scan_path_norm = os.path.normpath(scan_path)

    # --- Iterate through the plan and Move Files ---
    for move_action in organization_plan:
        if not isinstance(move_action, dict) or "source" not in move_action or "destination" not in move_action:
            errors.append(f"Skipped invalid move action: {move_action}")
            continue

        source_rel_path = move_action["source"]
        dest_rel_path = move_action["destination"]

        if not source_rel_path or not dest_rel_path:
             errors.append(f"Skipped move action with empty source/destination: {move_action}")
             continue

        # Construct absolute paths safely
        # Normalize relative paths to prevent issues like ".." escaping scan_path
        source_rel_path_norm = os.path.normpath(source_rel_path)
        dest_rel_path_norm = os.path.normpath(dest_rel_path)

        # Ensure relative paths don't contain '..' at the start after normalization
        if source_rel_path_norm.startswith("..") or dest_rel_path_norm.startswith(".."):
             errors.append(f"Skipped potentially unsafe move action (uses '..'): {move_action}")
             continue

        source_abs_path = os.path.join(scan_path_norm, source_rel_path_norm)
        dest_abs_path = os.path.join(scan_path_norm, dest_rel_path_norm)

        # Basic sanity checks
        if source_abs_path == dest_abs_path:
            # errors.append(f"Skipped moving '{source_rel_path}': Source and destination are the same.")
            continue # No error, just nothing to do

        if not os.path.exists(source_abs_path):
            # File might have been moved already or deleted
            errors.append(f"Skipped moving '{source_rel_path}': Source file not found at '{source_abs_path}'.")
            continue

        if os.path.isdir(source_abs_path):
             errors.append(f"Skipped moving '{source_rel_path}': Source is a directory (only files are moved).")
             continue

        # --- Perform the move ---
        try:
            # Create destination directory if it doesn't exist
            dest_dir = os.path.dirname(dest_abs_path)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            elif not os.path.isdir(dest_dir):
                 errors.append(f"Skipped moving '{source_rel_path}': Destination parent path '{dest_dir}' exists but is not a directory.")
                 continue # Cannot create subdir if parent is a file

            # Check if destination file already exists
            if os.path.exists(dest_abs_path):
                errors.append(f"Skipped moving '{source_rel_path}': Destination '{dest_rel_path}' already exists.")
            else:
                # Move the file
                shutil.move(source_abs_path, dest_abs_path)
                # os.rename(source_abs_path, dest_abs_path) # os.rename is generally faster but less flexible
                moved_count += 1

        except OSError as e:
            errors.append(f"Error moving file '{source_rel_path}' to '{dest_rel_path}': {e}")
        except Exception as e:
            errors.append(f"Unexpected error moving file '{source_rel_path}': {e}")

    return moved_count, errors