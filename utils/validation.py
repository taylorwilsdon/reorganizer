# utils/validation.py
import os
from typing import Optional, Tuple, List, TYPE_CHECKING
from textual.widgets import Input, Pretty, Select, Checkbox
from textual.validation import Validator, ValidationResult

# Avoid circular import for type hinting
if TYPE_CHECKING:
    from textual.app import App

# --- Custom Validators ---

class PathValidator(Validator):
    """Validator to check if a path exists and is a directory."""
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("Path cannot be empty.")
        # Check both absolute and relative paths robustly
        abs_path = os.path.abspath(value)
        # Use current working directory for relative path base
        relative_path = os.path.join(os.getcwd(), value)

        check_path = None
        if os.path.exists(abs_path):
            check_path = abs_path
        elif os.path.exists(relative_path):
             check_path = relative_path
        else:
            # Provide specific feedback about which paths were checked if needed
            # return self.failure(f"Path does not exist (checked {abs_path} and {relative_path})")
            return self.failure(f"Path does not exist: {value}")

        if not os.path.isdir(check_path):
            return self.failure(f"Path must be a directory: {value}")

        return self.success()

# Add other custom validators here in the future if needed


# --- Validation Utility Functions ---

def validate_input_widget(widget: Input) -> bool:
    """Validate a single input widget, handling disabled state."""
    if widget.disabled:
        return True
    try:
        result: Optional[ValidationResult] = widget.validate(widget.value)
        # Treat None result (no validators) as valid
        return result is None or result.is_valid
    except Exception:
        # Log exception here if needed
        return False

def update_validation_summary(app: 'App', focused_input: Optional[Input] = None) -> None:
    """Update the validation summary based on the focused input's errors."""
    try:
        summary_widget = app.query_one("#validation-summary", Pretty)
    except Exception:
        # Summary widget might not exist or be queryable yet
        return

    errors = []
    if focused_input and not focused_input.disabled:
        try:
            validation_result: Optional[ValidationResult] = focused_input.validate(focused_input.value)
            if validation_result and not validation_result.is_valid:
                errors.extend(validation_result.failure_descriptions)
        except Exception:
            # Log exception here if needed
            errors.append(f"Validation error for this field.") # User-friendly message

    if errors:
        summary_widget.update("\n".join(errors))
        summary_widget.display = True
    else:
        # Clear summary only if the focused input is valid
        summary_widget.update([])
        summary_widget.display = False

def clear_validation_summary(app: 'App') -> None:
    """Clears the validation summary display."""
    try:
        summary_widget = app.query_one("#validation-summary", Pretty)
        summary_widget.update([])
        summary_widget.display = False
    except Exception:
        # Summary widget might not exist
        pass

def validate_all_app_inputs(app: 'App') -> Tuple[bool, List[str]]:
    """Validate all relevant inputs in the app before submission."""
    errors = []
    is_valid = True

    try:
        all_inputs = app.query(Input)
        # --- Specific Input Checks ---
        scan_path_input = app.query_one("#scan_path", Input)
        llm_url_input = app.query_one("#llm_url", Input)
        openai_key_input = app.query_one("#openai_key", Input)
        use_openai = app.query_one("#openai_api_checkbox", Checkbox).value
        model_select = app.query_one("#model_select", Select)

        # 1. Scan Path
        scan_path_valid = validate_input_widget(scan_path_input)
        if not scan_path_valid:
            is_valid = False
            validation_result = scan_path_input.validate(scan_path_input.value) # Re-validate to get message
            if validation_result and not validation_result.is_valid:
                 errors.extend(validation_result.failure_descriptions)
            elif not scan_path_input.value: # Check empty explicitly
                 errors.append("Scan path cannot be empty.")
            else: # Fallback
                 errors.append("Scan path is invalid.")

        # 2. LLM URL or Key
        if use_openai:
            # Key validation (presence check)
            if not openai_key_input.value.strip():
                is_valid = False
                errors.append("OpenAI API Key is required when 'Use OpenAI API' is checked.")
                openai_key_input.add_class("-invalid")
            else:
                openai_key_input.remove_class("-invalid")
            # URL is disabled, ensure it's not marked invalid
            llm_url_input.remove_class("-invalid")
        else: # Local LLM
            # URL validation
            llm_url_valid = validate_input_widget(llm_url_input)
            if not llm_url_valid:
                is_valid = False
                validation_result = llm_url_input.validate(llm_url_input.value) # Re-validate
                if validation_result and not validation_result.is_valid:
                    errors.extend(validation_result.failure_descriptions)
                elif not llm_url_input.value: # Check empty explicitly
                     errors.append("LLM URL cannot be empty.")
                else: # Fallback
                    errors.append("LLM URL is invalid.")
            # Key is disabled, ensure it's not marked invalid
            openai_key_input.remove_class("-invalid")

        # 3. Model Selection
        if not model_select.disabled and model_select.value is Select.BLANK:
            is_valid = False
            errors.append("An LLM Model must be selected.")
            # Consider adding visual feedback to Select if needed

        # --- Update Summary Display ---
        summary_widget = app.query_one("#validation-summary", Pretty)
        if errors:
            summary_widget.update("\n".join(errors))
            summary_widget.display = True
        else:
            # Clear summary only if all checks passed
            clear_validation_summary(app)

        # --- Add/Remove Invalid Classes for Visual Feedback ---
        # Ensure visual state matches validation state after full check
        for inp in all_inputs:
             # Check if input should be validated based on current app state
             should_validate = False
             if inp.id == "scan_path":
                 should_validate = True
             elif inp.id == "llm_url" and not use_openai and not inp.disabled:
                 should_validate = True
             elif inp.id == "openai_key" and use_openai and not inp.disabled:
                 # Special case for key: just check if non-empty
                 is_inp_valid = bool(inp.value.strip())
                 if not is_inp_valid: inp.add_class("-invalid")
                 else: inp.remove_class("-invalid")
                 continue # Skip generic validation for key

             if should_validate:
                 is_inp_valid = validate_input_widget(inp)
                 if not is_inp_valid: inp.add_class("-invalid")
                 else: inp.remove_class("-invalid")
             else:
                 # Remove invalid class if input is not relevant or disabled
                 inp.remove_class("-invalid")


    except Exception as e:
        # Log error if querying widgets fails during validation
        # Consider adding logging: import logging; logger = logging.getLogger(__name__)
        # logger.exception("Error during validation")
        errors.append(f"Internal validation error: {e}")
        is_valid = False
        # Attempt to display the error in the summary
        try:
            summary_widget = app.query_one("#validation-summary", Pretty)
            summary_widget.update("\n".join(errors))
            summary_widget.display = True
        except Exception:
            pass # Can't display summary if it's missing

    return is_valid, errors