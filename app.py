# config_app.py
import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List, Iterator

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal, Container
from textual.validation import Regex, Validator, ValidationResult
from textual.widgets import (
    Input, Label, Pretty, Checkbox, Select, Button, Header, Footer, LoadingIndicator, DataTable, Static # Add DataTable, Static
)

from utils.list_models import fetch_available_models, ModelFetchError
import cli_config
from styles import TEXTUAL_CSS

from utils.validation import (
    PathValidator,
    validate_all_app_inputs,
    update_validation_summary,
    clear_validation_summary
)
from utils.file_scanner import scan, FileMeta
from utils.analysis import analyze_directory
from utils.organizer import organize_files

# --- Main App ---

class ConfigApp(App[Optional[Dict[str, Any]]]):
    """Textual app for configuring the application."""

    CSS = TEXTUAL_CSS # Use the imported CSS directly

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+s", "save_config", "Save Config"),
        ("ctrl+l", "load_config", "Load Config"),
    ]

    def __init__(self, initial_config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.initial_config = initial_config or {}
        self.model_fetch_worker = None
        self.scan_task = None
        self.organize_task = None # Add this line
        self.final_config: Optional[Dict[str, Any]] = None # Store config after submit
        self._last_scan_results: Optional[Dict[str, Any]] = None # Store analysis results

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="input-form"):
            yield Label("Scan Path:")
            yield Input(
                placeholder="/path/to/your/data or relative/path",
                id="scan_path",
                validators=[PathValidator()]
            )

            yield Label("LLM Configuration:")
            yield Checkbox("Use OpenAI API", id="openai_api_checkbox", value=False)

            with Horizontal():
                with Container(classes="input-group"):
                    yield Label("LLM URL:")
                    yield Input(
                        value="http://localhost:11434",
                        validators=[Regex(cli_config.URL_REGEX, failure_description="Must be a valid URL (http/https)")],
                        id="llm_url",
                    )
                with Container(classes="input-group"):
                    yield Label("OpenAI API Key:")
                    yield Input(
                        placeholder="Enter key if using OpenAI",
                        password=True,
                        id="openai_key",
                        disabled=True # Disabled by default
                    )

            yield Label("LLM Model:")
            yield Select(
                [],
                prompt="Enter URL/Key first...",
                id="model_select",
                allow_blank=True, # Allow blank initially or if fetch fails
                disabled=True
            )

            yield Pretty([], id="validation-summary")

            with Horizontal(id="button-row"):
                yield Button("Save", id="save-button", variant="success")
                yield Button("Load", id="load-button", variant="default")
                yield Button("Submit", id="submit-button", variant="primary")
                yield Button("Quit", id="quit-button", variant="error")

        # Area for results/next steps (initially hidden)
        with Container(id="results-area", classes="hidden"):
             yield LoadingIndicator(id="scan-indicator")
             yield Label("Analysis Results:", classes="hidden") # Changed Label
             yield Static("", id="issue-summary", classes="hidden") # For text summary/errors
             yield DataTable(id="scan-results-table", classes="hidden") # Table for proposed moves
             # Add container for action buttons, initially hidden
             with Horizontal(id="action-buttons", classes="hidden"):
                 yield Button("Organize Files", id="organize-button", variant="success")
                 yield Button("Cancel", id="cancel-scan-button", variant="error")

        yield Footer()


    def on_mount(self) -> None:
        """Load config and fetch initial models on mount."""
        self.load_configuration() # Load first
        # Initial model fetch based on loaded/default config
        self._trigger_model_fetch()

    def _trigger_model_fetch(self) -> None:
        """Initiates model fetching based on current UI state."""
        use_openai = self.query_one("#openai_api_checkbox", Checkbox).value
        llm_url_input = self.query_one("#llm_url", Input)
        openai_key_input = self.query_one("#openai_key", Input)

        url = (llm_url_input.value or '').strip()
        key = (openai_key_input.value or '').strip()

        model_select = self.query_one("#model_select", Select)
        # Don't clear options here, let the worker handle it to avoid flicker
        # model_select.set_options([])
        # model_select.clear()
        model_select.disabled = True # Disable while fetching/checking

        if use_openai:
            if key:
                model_select.prompt = "Fetching OpenAI models..."
                if self.model_fetch_worker: self.model_fetch_worker.cancel()
                self.model_fetch_worker = self.fetch_models_worker(url, key)
            else:
                model_select.prompt = "Enter OpenAI API Key..."
                model_select.set_options([])
                model_select.clear()
        else: # Local LLM
            if url and llm_url_input.is_valid:
                model_select.prompt = "Fetching local models..."
                if self.model_fetch_worker: self.model_fetch_worker.cancel()
                self.model_fetch_worker = self.fetch_models_worker(url)
            elif not url:
                 model_select.prompt = "Enter LLM URL..."
                 model_select.set_options([])
                 model_select.clear()
            else: # Invalid URL
                 model_select.prompt = "Invalid LLM URL"
                 model_select.set_options([])
                 model_select.clear()


    @work(exclusive=True, thread=True)
    def fetch_models_worker(self, base_url: str, api_key: Optional[str] = None) -> None:
        """Worker to fetch models in the background."""
        # Use self.query instead of self.query_one as it's safer in workers
        selects = self.query("#model_select")
        if not selects: return # Widget might not be mounted yet
        model_select = selects.first(Select)

        # Determine previously selected model (from load or previous state)
        intended_model = getattr(self, '_loaded_model', None)

        # Clear options and set prompt via call_from_thread before fetching
        def prepare_select():
            model_select.set_options([])
            model_select.clear()
            model_select.prompt = "Fetching..."
            model_select.disabled = True
        self.call_from_thread(prepare_select)

        try:
            available_models = fetch_available_models(base_url, api_key)
            options = [(model, model) for model in available_models]

            def update_select():
                model_select.set_options(options)
                if options:
                    # Try to restore previous selection or default to first
                    current_value_valid = intended_model and intended_model in available_models
                    if current_value_valid:
                        model_select.value = intended_model
                    elif model_select.value not in available_models: # If current value is invalid, pick first
                         model_select.value = options[0][1]

                    # If still blank after trying to restore/default, set to first
                    if model_select.value is Select.BLANK and options:
                         model_select.value = options[0][1]

                    model_select.prompt = "Select Model..."
                    model_select.disabled = False
                else:
                    model_select.prompt = "No models found"
                    model_select.disabled = True
                # Clear the temporary attribute after attempting to use it
                if hasattr(self, '_loaded_model'):
                    delattr(self, '_loaded_model')

            self.call_from_thread(update_select)

        except ModelFetchError as e:
            def handle_fetch_error():
                model_select.set_options([])
                model_select.clear()
                model_select.prompt = f"Error: {str(e).replace('[', '\\[').replace(']', '\\]')}"
                model_select.disabled = True
                self.notify(f"Error fetching models: {str(e).replace('[', '\\[').replace(']', '\\]')}", severity="error", timeout=6)
            self.call_from_thread(handle_fetch_error)
        except Exception as e:
            def handle_generic_error():
                model_select.set_options([])
                model_select.clear()
                model_select.prompt = "Unexpected Error"
                model_select.disabled = True
                self.notify(f"Unexpected error: {str(e).replace('[', '\\[').replace(']', '\\]')}", severity="error", timeout=6)
            self.call_from_thread(handle_generic_error)


    @on(Checkbox.Changed, "#openai_api_checkbox")
    def update_openai_options(self, event: Checkbox.Changed) -> None:
        """Enable/disable URL/Key inputs based on OpenAI checkbox."""
        llm_url_input = self.query_one("#llm_url", Input)
        openai_key_input = self.query_one("#openai_key", Input)

        if event.value: # Use OpenAI
            # Store current local URL before overwriting
            self._current_local_llm_url = llm_url_input.value
            llm_url_input.value = "https://api.openai.com"
            llm_url_input.disabled = True
            openai_key_input.disabled = False
            openai_key_input.focus()
        else: # Use Local LLM
            # Restore default or previously saved/entered local URL
            restore_url = getattr(self, '_current_local_llm_url', None) or \
                          getattr(self, '_loaded_local_llm_url', "http://localhost:11434")
            llm_url_input.value = restore_url or "" # Ensure value is always a string
            llm_url_input.disabled = False
            # Don't clear the key automatically, user might switch back
            # openai_key_input.value = ""
            openai_key_input.disabled = True
            llm_url_input.focus()

        # Clear validation summary when switching modes
        clear_validation_summary(self)
        # Trigger model fetch for the new mode
        self._trigger_model_fetch()

    @on(Input.Changed)
    def handle_input_change(self, event: Input.Changed) -> None:
        """Validate input and trigger model fetch if URL/Key changes."""
        # Update validation summary for the specific input
        update_validation_summary(self, event.input)

        # Trigger model fetch only if relevant inputs change and are valid (for URL)
        if event.input.id == "llm_url":
             if event.input.is_valid:
                 self._trigger_model_fetch()
             else: # If URL becomes invalid, clear models
                 model_select = self.query_one("#model_select", Select)
                 model_select.set_options([])
                 model_select.clear()
                 model_select.prompt = "Invalid LLM URL"
                 model_select.disabled = True
        elif event.input.id == "openai_key":
             self._trigger_model_fetch() # Fetch models whenever key changes (if OpenAI is selected)


    # Validation helper methods moved to validation_utils.py


    def _collect_config(self) -> Dict[str, Any]:
        """Collects configuration values from the UI."""
        config = {}
        scan_path_input = self.query_one("#scan_path", Input)
        # Store the absolute path for consistency
        config["scan_path"] = os.path.abspath(scan_path_input.value)

        config["use_openai_api"] = self.query_one("#openai_api_checkbox", Checkbox).value
        config["llm_url"] = self.query_one("#llm_url", Input).value
        config["openai_key"] = self.query_one("#openai_key", Input).value
        model_select = self.query_one("#model_select", Select)
        config["model"] = model_select.value if not model_select.disabled and model_select.value is not Select.BLANK else None
        return config

    def action_save_config(self) -> None:
        """Save the current configuration to file."""
        # Validate before saving to ensure a usable config is saved
        is_valid, _ = validate_all_app_inputs(self)
        if not is_valid:
            self.bell()
            self.notify("Cannot save invalid configuration. Please fix errors.", severity="warning", title="Save Blocked")
            return

        config_values = self._collect_config()
        save_notification = cli_config.save_config_to_file(cli_config.CONFIG_FILE, config_values)
        severity = "error" if "Error" in save_notification else "success"
        title = "Save Error" if "Error" in save_notification else "Save Success"
        self.notify(save_notification, severity=severity, title=title)

    def action_load_config(self) -> None:
        """Load configuration from file."""
        self.load_configuration()
        # Model fetch is triggered within load_configuration -> update_openai_options -> _trigger_model_fetch

    def load_configuration(self) -> None:
        """Loads config from file and populates UI."""
        file_config, load_notification = cli_config.load_config_from_file(cli_config.CONFIG_FILE)
        if load_notification:
            severity = "error" if "Error" in load_notification else "information"
            title = "Config Load Error" if "Error" in load_notification else "Config Load"
            self.notify(load_notification, severity=severity, title=title)

        # Merge with initial config if needed (not used much here)
        config_values = cli_config.merge_configs(file_config, self.initial_config)

        # Store loaded values temporarily for logic in event handlers
        self._loaded_model = config_values.get("model")
        # Store the specific local URL loaded, not just a default
        self._loaded_local_llm_url = config_values.get("llm_url") if not config_values.get("use_openai_api") else None


        # Populate UI
        try:
            self.query_one("#scan_path", Input).value = str(config_values.get("scan_path", ""))

            use_openai = config_values.get("use_openai_api", False)
            openai_cb = self.query_one("#openai_api_checkbox", Checkbox)

            # Set checkbox value *without* triggering its Changed event immediately
            # Check current state before toggling to avoid unnecessary events
            if openai_cb.value != use_openai:
                openai_cb.toggle()

            # Manually call the update logic *after* setting checkbox value
            # This ensures URL/Key inputs are set correctly based on the loaded 'use_openai' state
            self.update_openai_options(Checkbox.Changed(openai_cb, use_openai))

            # Set URL and Key *after* checkbox state is handled by update_openai_options
            # If using OpenAI, update_openai_options sets the URL. If not, set it from config.
            if not use_openai:
                 self.query_one("#llm_url", Input).value = str(config_values.get("llm_url", "http://localhost:11434"))
            self.query_one("#openai_key", Input).value = str(config_values.get("openai_key", ""))

            # Trigger validation for loaded values
            for inp in self.query(Input):
                 # Update summary for each input individually after load
                 update_validation_summary(self, inp)
            validate_all_app_inputs(self) # Do a full validation pass after loading

            # Model fetch is triggered by update_openai_options -> _trigger_model_fetch

        except Exception as e:
             self.notify(f"Error applying loaded config: {e}", severity="error", title="UI Populate Error")


    # --- Scan Worker and Callbacks ---

    @work(exclusive=True, thread=True)
    def scan_worker(self, scan_path: str, llm_config: Dict[str, Any]) -> None:
        """Worker to scan files and perform LLM-based analysis."""
        results_area = self.query_one("#results-area")
        scan_indicator = self.query_one("#scan-indicator")
        # results_display = self.query_one("#scan-results-display") # REMOVE THIS LINE
        results_label = results_area.query_one("Label") # Find the label within results

        # Ensure UI updates happen on the main thread
        def show_loading():
            # Get widgets within the thread-safe function
            issue_summary = self.query_one("#issue-summary", Static)
            results_table = self.query_one("#scan-results-table", DataTable)

            results_area.remove_class("hidden")
            scan_indicator.remove_class("hidden")
            results_label.add_class("hidden") # Hide "Analysis Results:" label during loading
            issue_summary.add_class("hidden") # Hide summary area
            issue_summary.update("")          # Clear previous summary
            results_table.add_class("hidden") # Hide table
            results_table.clear()             # Clear previous table data
            # Also hide action buttons during scan
            self.query_one("#action-buttons").add_class("hidden")
        self.call_from_thread(show_loading)

        try:
            # --- Call the external analysis function with LLM config ---
            analysis_results = analyze_directory(scan_path, llm_config)
            # --- End analysis call ---

            # Post results back to the main thread
            self.call_from_thread(self.on_scan_complete, analysis_results)

        except Exception as e:
            # Post error back to the main thread
            self.call_from_thread(self.on_scan_error, e)


    def on_scan_complete(self, results: Dict[str, Any]) -> None:
        """Called when the scan worker finishes successfully."""
        # Store results for the organize button
        self._last_scan_results = results

        results_area = self.query_one("#results-area")
        scan_indicator = self.query_one("#scan-indicator")
        issue_summary = self.query_one("#issue-summary", Static)
        results_table = self.query_one("#scan-results-table", DataTable)
        results_label = results_area.query_one("Label") # The "Analysis Results:" label
        action_buttons = self.query_one("#action-buttons", Horizontal)

        # --- Reset UI State ---
        scan_indicator.add_class("hidden")
        results_label.remove_class("hidden") # Show "Analysis Results:" label
        issue_summary.update("") # Clear previous summary
        issue_summary.remove_class("hidden") # Make summary area visible
        results_table.clear() # Clear previous table data
        results_table.add_class("hidden") # Hide table initially
        action_buttons.add_class("hidden") # Hide buttons initially

        # --- Populate Table Columns (if not already done) ---
        if not results_table.columns:
             results_table.add_columns("Source Path", "Proposed Destination")
             # Adjust column widths if needed
             # results_table.columns["Source Path"].width = 50
             # results_table.columns["Proposed Destination"].width = 50

        # --- Process Results ---
        organization_plan = results.get("organization_plan") # This is now a list of dicts or None
        analysis_error = results.get("error")
        scan_path_name = os.path.basename(results.get("scan_path", "the target directory"))

        if analysis_error:
            # Display the error from the analysis/LLM step
            issue_summary.update(f"Analysis Error in '{scan_path_name}':\n{analysis_error}")
            issue_summary.set_classes("error-text") # Add CSS class for error styling
            self.notify(f"Analysis failed: {analysis_error}", severity="error", title="Analysis Error")
            action_buttons.add_class("hidden") # Hide organize button on error

        elif organization_plan is not None: # Check for None explicitly, [] is valid (no changes)
            if organization_plan:
                # Display textual summary
                issue_summary.update(f"LLM proposed {len(organization_plan)} file move(s) for '{scan_path_name}':")
                issue_summary.set_classes("") # Reset classes if previously error

                # Populate table with the proposed plan
                rows_added = 0
                for move in organization_plan:
                    source = move.get("source", "?")
                    destination = move.get("destination", "?")
                    results_table.add_row(source, destination)
                    rows_added += 1

                if rows_added > 0:
                    results_table.remove_class("hidden") # Show table only if it has rows

                action_buttons.remove_class("hidden") # Show buttons
                self.notify("Analysis complete. Proposed organization plan generated.", title="Analysis Finished")
            else:
                # Empty plan means no changes needed
                issue_summary.update(f"Analysis complete. No organizational changes proposed by the LLM for '{scan_path_name}'.")
                issue_summary.set_classes("") # Reset classes
                results_table.add_class("hidden") # Hide empty table
                action_buttons.add_class("hidden") # Hide organize button
                self.notify("Analysis complete. No changes needed.", title="Analysis Finished")
        else:
            # Should not happen if error is None and plan is None, but handle defensively
            issue_summary.update(f"Analysis completed for '{scan_path_name}', but no plan or error was returned.")
            issue_summary.set_classes("warning-text") # Add CSS class for warning styling
            self.notify("Analysis finished with unexpected result.", severity="warning", title="Analysis Warning")
            action_buttons.add_class("hidden")


    def on_scan_error(self, error: Exception) -> None:
        """Called when the scan worker encounters an error."""
        results_area = self.query_one("#results-area")
        scan_indicator = self.query_one("#scan-indicator")
        issue_summary = self.query_one("#issue-summary", Static)
        results_table = self.query_one("#scan-results-table", DataTable)
        results_label = results_area.query_one("Label")
        action_buttons = self.query_one("#action-buttons", Horizontal)

        scan_indicator.add_class("hidden")
        results_label.remove_class("hidden")
        results_table.add_class("hidden") # Hide table on error
        action_buttons.add_class("hidden") # Hide buttons on error

        issue_summary.update(f"Scan Error:\n{type(error).__name__}: {error}")
        issue_summary.set_classes("error-text") # Use error class
        issue_summary.remove_class("hidden") # Show error in summary area
        self.notify(f"Scan failed: {error}", severity="error", title="Scan Error")


    # --- Organize Worker and Callbacks ---

    @work(exclusive=True, thread=True)
    def organize_files_worker(self, organization_plan: List[Dict[str, str]], scan_path: str) -> None:
        """Worker wrapper to organize files based on the LLM plan."""
        try:
            # --- Call the external organizer function ---
            # Assuming organize_files is updated to take: plan, scan_path
            moved_count, errors = organize_files(organization_plan, scan_path)
            # --- End organizer call ---

            # Post results back to the main thread
            self.call_from_thread(self.on_organize_complete, moved_count, errors) # Pass correct params

        except Exception as e:
            # Post error back to the main thread
            # This catches errors within organize_files if they aren't handled internally,
            # or errors setting up the call.
            self.call_from_thread(self.on_organize_error, e)


    def on_organize_complete(self, moved_count: int, errors: List[str]) -> None: # Updated signature
        """Called when the organize worker finishes."""
        issue_summary = self.query_one("#issue-summary", Static)
        results_table = self.query_one("#scan-results-table", DataTable)

        parts = []
        if moved_count > 0:
            parts.append(f"Moved {moved_count} file(s) based on the plan")

        if not parts and not errors: # Handle case where plan was empty or files already moved/gone
             message = "Organization complete. No files needed moving according to the plan."
             title = "Organize Finished"
             severity = "information"
             issue_summary.set_classes("") # Reset class
        elif not parts and errors: # Handle case where only errors occurred
             message = "Organization failed."
             title = "Organize Failed"
             severity = "error"
             issue_summary.set_classes("error-text")
        else: # Files were moved
            message = "Organization complete. " + " and ".join(parts) + "."
            title = "Organize Finished"
            severity = "success"
            issue_summary.set_classes("") # Reset class

        if errors:
            message += "\nEncountered errors:\n" + "\n".join(f"- {e}" for e in errors)
            # Adjust title and severity if there were errors
            if parts: # If some files moved but there were errors
                 title = "Organize Finished with Errors"
                 severity = "warning"
                 issue_summary.set_classes("warning-text")
            # else: # Only errors case handled above

        self.notify(message, severity=severity, title=title, timeout=10)
        issue_summary.update(message) # Update summary with results
        issue_summary.remove_class("hidden") # Ensure summary is visible
        results_table.add_class("hidden") # Hide table after organization
        # Keep results displayed, buttons remain hidden


    def on_organize_error(self, error: Exception) -> None:
        """Called when the organize worker encounters an error."""
        issue_summary = self.query_one("#issue-summary", Static) # Get issue summary widget
        results_table = self.query_one("#scan-results-table", DataTable) # Get table widget

        issue_summary.update(f"Organization Error:\n{type(error).__name__}: {error}") # Update summary
        issue_summary.set_classes("error-text") # Use error class
        issue_summary.remove_class("hidden") # Ensure summary is visible
        results_table.add_class("hidden") # Hide table on error
        self.notify(f"Organization failed: {error}", severity="error", title="Organize Error")


    # --- Button Handlers ---

    @on(Button.Pressed, "#submit-button")
    def handle_submit(self) -> None:
        """Validate, collect config, start scan."""
        is_valid, _ = validate_all_app_inputs(self)
        if not is_valid:
            self.bell()
            self.notify("Please fix validation errors before submitting.", severity="error", title="Validation Failed")
            return

        self.final_config = self._collect_config()

        # --- Start Scan ---
        # Hide input form, show results area (loading indicator shown by worker)
        self.query_one("#input-form").display = False
        self.query_one("#results-area").remove_class("hidden") # Show area, worker shows indicator

        # Cancel previous scan if running
        if self.scan_task and self.scan_task.is_running:
            self.scan_task.cancel()

        # Start the new scan worker
        scan_path = self.final_config.get("scan_path")
        if scan_path:
            # Pass the full config to the worker
            self.scan_task = self.scan_worker(scan_path, self.final_config)
        else:
            # Handle case where scan_path might be missing (shouldn't happen with validation)
            self.on_scan_error(ValueError("Scan path is missing in the configuration."))


    # --- Action Button Handlers ---

    @on(Button.Pressed, "#organize-button")
    def handle_organize_button(self) -> None:
        """Handle the 'Organize Files' button press."""
        # Need the results from the *scan* worker to pass to organize worker
        scan_results = getattr(self, '_last_scan_results', None)

        if not scan_results or not scan_results.get("scan_path"):
            self.notify("Error: Scan results missing or invalid. Cannot organize.", severity="error")
            return
        # Check for errors first
        if scan_results.get("error"):
             self.notify(f"Cannot organize due to previous analysis error: {scan_results['error']}", severity="warning")
             return
        # Check if a plan exists and is not empty
        organization_plan = scan_results.get("organization_plan")
        if organization_plan is None: # Check for None specifically (indicates an error during plan generation)
             self.notify("Error: Organization plan missing or invalid from scan results.", severity="error")
             return
        if not organization_plan: # Plan is an empty list []
             self.notify("No organizational changes were proposed by the LLM.", severity="information")
             return


        # Hide buttons, update summary, hide table
        self.query_one("#action-buttons").add_class("hidden")
        issue_summary = self.query_one("#issue-summary", Static) # Get issue summary widget
        results_table = self.query_one("#scan-results-table", DataTable) # Get table widget
        issue_summary.update("Starting organization based on LLM plan...") # Update summary area
        issue_summary.set_classes("") # Clear any error/warning classes
        results_table.add_class("hidden") # Hide table during organization
        self.notify("Organization started...", title="Organizing")

        # Cancel previous task if running
        if self.organize_task and self.organize_task.is_running:
            self.organize_task.cancel()

        # Start the worker, passing the plan and scan path
        scan_path = scan_results.get("scan_path") # Already checked this exists above
        self.organize_task = self.organize_files_worker(organization_plan, scan_path)


    @on(Button.Pressed, "#cancel-scan-button")
    def handle_cancel_scan_button(self) -> None:
        """Handle the 'Cancel' button press after scan results."""
        # Reset UI back to the input form
        results_area = self.query_one("#results-area")
        results_area.add_class("hidden") # Hide the whole results container
        # Explicitly hide table and summary
        results_area.query_one("#scan-results-table", DataTable).add_class("hidden")
        results_area.query_one("#issue-summary", Static).add_class("hidden")

        self.query_one("#input-form").display = True
        self.final_config = None # Clear submitted config
        self._last_scan_results = None # Clear stored results
        # Cancel workers if running
        if self.scan_task and self.scan_task.is_running:
            self.scan_task.cancel()
        if self.organize_task and self.organize_task.is_running:
            self.organize_task.cancel()
        self.notify("Organization cancelled.", title="Cancelled")


    # --- Other Button Handlers ---

    @on(Button.Pressed, "#save-button")
    def handle_save_button(self) -> None:
        """Handler for the save button."""
        self.action_save_config()

    @on(Button.Pressed, "#load-button")
    def handle_load_button(self) -> None:
        """Handler for the load button."""
        # If results are displayed, reset the UI before loading
        results_area = self.query_one("#results-area")
        if not results_area.has_class("hidden"):
             # Hide results area (which hides table, summary, buttons)
             results_area.add_class("hidden")
             # Explicitly hide table and summary
             results_area.query_one("#scan-results-table", DataTable).add_class("hidden")
             results_area.query_one("#issue-summary", Static).add_class("hidden")

             self.query_one("#input-form").display = True
             self.final_config = None # Clear submitted config
             self._last_scan_results = None # Clear stored results
             # Cancel workers if running
             if self.scan_task and self.scan_task.is_running:
                 self.scan_task.cancel()
             if self.organize_task and self.organize_task.is_running:
                 self.organize_task.cancel()

        self.action_load_config()

    @on(Button.Pressed, "#quit-button")
    def handle_quit_button(self) -> None:
        """Quit the application."""
        # Cancel workers if running
        if self.model_fetch_worker and self.model_fetch_worker.is_running:
            self.model_fetch_worker.cancel()
        if self.scan_task and self.scan_task.is_running:
            self.scan_task.cancel()
        if self.organize_task and self.organize_task.is_running: # Cancel organize task
            self.organize_task.cancel()
        self.exit(result=self.final_config if self.final_config else None) # Return config if submitted


if __name__ == "__main__":
    # Example of running the app
    # In a real scenario, you might pass initial config from CLI args
    # Ensure necessary files (cli_config.py, utils/list_models.py, styles.py) are present
    if not all([os.path.exists("cli_config.py"),
                os.path.exists("utils/list_models.py"),
                os.path.exists("styles.py"),
                os.path.exists("utils/validation.py"), # Added check
                os.path.exists("utils/file_scanner.py"), # Added check
                os.path.exists("utils/analysis.py"), # Added check
                os.path.exists("utils/organizer.py") # Added check
                ]):
        print("Error: Missing required files (cli_config.py, styles.py, utils/*).")
        print("Please create them based on the example or requirements.")
    else:
        app = ConfigApp()
        final_config = app.run() # Returns config on Quit (if submitted) or None

        print("\n--- App Closed ---")
        if final_config:
            print("Final Configuration:")
            print(json.dumps(final_config, indent=2))
        else:
            print("Configuration process was cancelled or not submitted.")