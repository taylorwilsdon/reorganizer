# styles.py
"""Centralized styling configuration for the application."""

# Simplified Textual CSS based on selenized dark theme elements
# Keeping core elements needed for the config app.
TEXTUAL_CSS = """
Screen {
    background: #0e333d; /* Dark background */
    color: #cad8d9;      /* Light text */
}

/* General Container Styling */
VerticalScroll {
    border: round #4695f7; /* Accent border */
    padding: 1 2;
    margin: 1 2;
}

Container {
    height: auto;
    margin-bottom: 1;
}

/* Input Styling */
Input {
    margin-bottom: 1;
    border: tall #184956; /* Subtle border */
}
Input:focus {
    border: tall #58a3ff; /* Highlight focus */
}
Input.-valid {
    border: tall #22c55e 60%; /* Success indication */
}
Input.-valid:focus {
    border: tall #22c55e;
}
Input.-invalid {
    border: tall #ef4444 60%; /* Error indication */
}
Input.-invalid:focus {
    border: tall #ef4444;
}

/* Label Styling */
Label {
    margin: 1 0 0 0; /* Spacing above labels */
}

/* Select Widget Styling */
Select {
    width: 100%;
    margin-bottom: 1;
}
Select:focus {
    border: tall #58a3ff;
}

/* Checkbox Styling */
Checkbox {
    margin-right: 2;
    width: auto;
}

/* Button Styling */
#button-row {
    height: auto;
    align: center middle; /* Center buttons */
    margin-top: 1;
}
#button-row > Button {
    width: auto;
    margin: 0 1; /* Space between buttons */
}

/* Validation Summary */
Pretty#validation-summary {
    margin-top: 1;
    border: thick #ef4444; /* Error color for border */
    width: 100%;
    height: auto;
    max-height: 8; /* Limit error display height */
    display: none; /* Hide by default */
    color: #ef4444; /* Error text color */
}

/* Specific Layouts */
Horizontal {
    height: auto;
    margin-bottom: 1;
}
.input-group {
    width: 1fr; /* Distribute space */
    margin-right: 2;
    height: auto;
}
.input-group:last-of-type {
    margin-right: 0; /* No margin on the last item */
}

/* Styles moved from app.py */
#input-form {
    /* Styles specific to the input form area if needed */
}
.hidden {
    display: none;
}
#results-area {
    padding: 1;
    border: round $accent;
    /* Add other styles as needed */
}
#scan-indicator {
    margin: 1 0;
}
#action-buttons {
    margin-top: 1;
    align: center middle;
    height: auto;
}
#scan-results-table {
    height: 15; /* Example height, adjust as needed */
    border: round $accent;
    margin-top: 1;
}
#issue-summary {
    margin-top: 1;
    /* Default color is fine, specific classes added below */
}
.error-text {
    color: $error;
}
.warning-text {
     color: $warning;
}
"""
