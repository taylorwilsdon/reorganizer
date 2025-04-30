# utils/analysis.py
"""
Contains logic for analyzing directory contents using an LLM.
"""

import os
import re
import json # Added for JSON handling
import requests # Added for HTTP requests
from typing import List, Dict, Any, Optional, Union, Tuple

# Assuming FileMeta is defined in file_scanner and scan is available
try:
    from .file_scanner import scan, FileMeta
except ImportError:
    # Handle potential direct execution or different import structure if needed
    print("Warning: Could not import scan/FileMeta from relative path.")
    # Define dummy types if needed for standalone testing, though not ideal
    class FileMeta: pass
    def scan(path, follow_symlinks=False): yield FileMeta()


def analyze_directory(scan_path: str, llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scans the given path and uses an LLM to propose an organization plan.

    Args:
        scan_path: The absolute path to the directory to scan.
        llm_config: Dictionary containing LLM connection details ('llm_url', 'model', 'openai_key', 'use_openai_api').

    Returns:
        A dictionary containing analysis results, including:
        - organization_plan (Optional[List[Dict[str, str]]]): Proposed file movements (e.g., [{'source': 'file.txt', 'destination': 'Docs/file.txt'}]) or None if error/no plan.
        - all_scanned_files_meta (List[FileMeta]): Metadata for all files found during the scan.
        - scan_path (str): The original scan path.
        - is_desktop (bool): Whether the scan path was identified as the Desktop.
        - error (Optional[str]): Error message if analysis failed.
    """
    # --- Analysis Setup ---
    analysis_results = {
        "organization_plan": None,
        "all_scanned_files_meta": [], # Store all scanned files
        "scan_path": scan_path,
        "is_desktop": False,
        "error": None # Added error field
    }

    # Determine Desktop Path (Platform specific might be better)
    desktop_path = None
    try:
        # Works on macOS, Linux, and usually Windows
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        if not os.path.isdir(desktop_path): # Fallback for case sensitivity/language
             alt_desktop = os.path.join(os.path.expanduser('~'), 'desktop')
             if os.path.isdir(alt_desktop):
                 desktop_path = alt_desktop
             else:
                 desktop_path = None # Couldn't find it reliably
    except Exception:
        desktop_path = None # Error finding home dir etc.

    is_desktop_scan = False
    if desktop_path and os.path.normpath(scan_path) == os.path.normpath(desktop_path):
        is_desktop_scan = True
        analysis_results["is_desktop"] = True

    # --- Scan Files ---
    all_files_meta: List[FileMeta] = []
    try:
        for meta in scan(scan_path):
            all_files_meta.append(meta)
    except Exception as e:
        analysis_results["error"] = f"Error during file scanning: {e}"
        return analysis_results

    analysis_results["all_scanned_files_meta"] = all_files_meta

    # --- Get LLM Organization Plan ---
    if not all_files_meta:
        # No files found, return empty plan and no error
        analysis_results["organization_plan"] = []
        return analysis_results

    try:
        plan, llm_error = get_llm_organization_plan(
            scan_path=scan_path,
            file_meta_list=all_files_meta,
            llm_config=llm_config
        )
        if llm_error:
            analysis_results["error"] = llm_error
        analysis_results["organization_plan"] = plan # Will be None if error occurred in LLM call

    except Exception as e:
        analysis_results["error"] = f"Unexpected error getting LLM plan: {e}"
        # Ensure plan is None if an exception occurs here
        analysis_results["organization_plan"] = None

    # --- End LLM Interaction ---

    # --- Return Results ---
    return analysis_results


# --- LLM Interaction ---

def get_llm_organization_plan(
    scan_path: str,
    file_meta_list: List[FileMeta],
    llm_config: Dict[str, Any]
) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
    """
    Contacts the configured LLM to get a proposed file organization plan.

    Args:
        scan_path: The root path that was scanned.
        file_meta_list: List of FileMeta objects for files found.
        llm_config: Dictionary with LLM connection details.

    Returns:
        A tuple containing:
        - The organization plan (List of {'source': rel_path, 'destination': rel_path}) or None.
        - An error message string if an error occurred, otherwise None.
    """
    api_url = llm_config.get("llm_url")
    model = llm_config.get("model")
    api_key = llm_config.get("openai_key")
    use_openai = llm_config.get("use_openai_api", False)

    if not api_url or not model:
        return None, "LLM URL or Model not configured."
    if use_openai and not api_key:
        return None, "OpenAI API Key not provided."

    # --- Prepare File List for Prompt ---
    # Send relative paths to the LLM for clarity and context
    try:
        # Filter out directories from the list sent to LLM, focus on files
        file_paths_relative = [os.path.relpath(meta.path, scan_path) for meta in file_meta_list if not meta.is_dir]
    except ValueError as e:
        # This can happen if scan_path is not a prefix of meta.path,
        # which might indicate an issue with symlinks or scan logic.
        return None, f"Error creating relative paths: {e}. Check scan path and file paths."

    if not file_paths_relative:
        return [], None # No files to organize, return empty plan successfully

    # Limit the number of files sent to avoid huge prompts (optional, adjust as needed)
    MAX_FILES_IN_PROMPT = 500
    if len(file_paths_relative) > MAX_FILES_IN_PROMPT:
        # Potentially add logic here to summarize or sample if too many files
        # For now, just truncate and warn
        file_paths_for_prompt = file_paths_relative[:MAX_FILES_IN_PROMPT]
        warning = f" (Warning: Truncated file list from {len(file_paths_relative)} to {MAX_FILES_IN_PROMPT})"
    else:
        file_paths_for_prompt = file_paths_relative
        warning = ""

    file_list_str = "\n".join(file_paths_for_prompt)

# Log the file list being sent to the LLM
    try:
        with open("app.log", "a") as log_file:
            log_file.write(f"DEBUG: File list string sent to LLM:\n---\n{file_list_str}\n---\n")
    except Exception as log_e:
        print(f"Warning: Failed to write file list to app.log: {log_e}") # Fallback print
    # --- Construct Prompt ---
    # Base prompt asking for a JSON list of move operations
    prompt = f"""Analyze the following list of files found within the directory '{os.path.basename(scan_path)}'.
Propose a reorganization plan to improve the structure. Focus on common patterns like grouping similar file types (documents, images, code), moving desktop clutter (like screenshots) into appropriate folders, etc.

File List:{warning}
{file_list_str}

Your response MUST be a valid JSON list of objects, where each object represents a single file move operation.
Each object must have two keys: 'source' and 'destination'.
The 'source' value must be the original relative path of the file from the list above.
The 'destination' value must be the new relative path where the file should be moved (including the filename).
Create new subdirectories in the 'destination' path as needed (e.g., 'Docs/report.pdf', 'Images/Screenshots/screenshot1.png').
If a file should not be moved, do not include it in the list.
Return an empty JSON list [] if no reorganization is needed.

JSON Response:
"""

    # --- Make API Call ---
    headers = {"Content-Type": "application/json"}
    data = {"model": model, "prompt": prompt, "stream": False} # Ensure stream is false for single response

    if use_openai:
        # Adjust for OpenAI API format (Chat Completions is preferred)
        # Assuming v1 endpoint structure
        openai_url = api_url.rstrip('/') + "/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, # Lower temperature for more deterministic JSON output
            "response_format": {"type": "json_object"} # Request JSON output if supported
        }
        # Remove unsupported keys for OpenAI
        data.pop("prompt", None)
        data.pop("stream", None)
    else:
        # Assume Ollama-like API endpoint
        ollama_url = api_url.rstrip('/') + "/api/generate"
        # Add format parameter for Ollama if supported (check Ollama docs)
        data["format"] = "json" # Request JSON output

    try:
        target_url = openai_url if use_openai else ollama_url
        response = requests.post(target_url, headers=headers, json=data, timeout=120) # Increased timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        response_data = response.json()

        # --- Parse Response ---
        if use_openai:
            # Extract content from OpenAI response structure
            if not response_data.get("choices") or not response_data["choices"][0].get("message"):
                 return None, f"Invalid OpenAI response structure: {response_data}"
            content = response_data["choices"][0]["message"].get("content", "").strip()
        else:
            # Extract content from Ollama-like response structure
            content = response_data.get("response", "").strip()

        if not content:
            # Consider empty response as "no changes needed"
            return [], None

        # The LLM should return *only* the JSON list as requested
        # Sometimes models add markdown backticks or explanations, try to strip them
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Handle empty string after stripping markdown as "no changes needed"
        if not content:
            return [], None

        try:
            # Log raw content to app.log for debugging TUI apps
            try:
                with open("app.log", "a") as log_file:
                    log_file.write(f"DEBUG: Raw content before JSON parsing: >>>{content}<<<\n")
            except Exception as log_e:
                print(f"Warning: Failed to write to app.log: {log_e}") # Fallback print
            organization_plan = json.loads(content)

            # Handle cases where LLM returns a single object instead of a list
            if isinstance(organization_plan, dict):
                # Check if it looks like a valid plan item before wrapping
                if "source" in organization_plan and "destination" in organization_plan:
                    organization_plan = [organization_plan]
                else:
                    # If it's a dict but not a valid plan item, raise error
                    raise ValueError("Response is a JSON object but not a valid plan item.")

            # Basic validation of the plan structure (now works for original lists and wrapped objects)
            if not isinstance(organization_plan, list):
                 # This error should ideally not be hit now if parsing succeeded, but keep as safeguard
                raise ValueError("Response is not a JSON list or a single valid plan object.")
            for item in organization_plan:
                if not isinstance(item, dict) or "source" not in item or "destination" not in item:
                    raise ValueError("Invalid item structure in the list. Missing 'source' or 'destination'.")
                if not isinstance(item["source"], str) or not isinstance(item["destination"], str):
                     raise ValueError("Source/Destination values must be strings.")
                # Ensure source path exists in the original list (sanity check)
                if item["source"] not in file_paths_relative:
                    # Log this potential issue but don't necessarily fail the whole plan
                    print(f"Warning: LLM proposed moving source file '{item['source']}' which was not in the input list.")

            return organization_plan, None # Success

        except json.JSONDecodeError as e:
            return None, f"Failed to decode LLM response as JSON: {e}\nResponse received:\n{content}"
        except ValueError as e:
             return None, f"Invalid JSON structure from LLM: {e}\nResponse received:\n{content}"

    except requests.exceptions.RequestException as e:
        return None, f"API request failed: {e}"
    except Exception as e:
        # Catch-all for unexpected errors during API call or parsing
        return None, f"An unexpected error occurred during LLM communication: {e}"


# --- End LLM Interaction ---