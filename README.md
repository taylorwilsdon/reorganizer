# Reorganizer

Reorganizer is a command line application designed to help you analyze and organize files within a specified directory using the power of Large Language Models (LLMs). It can connect to local LLMs (like Ollama) or the OpenAI API to understand file contents and suggest an organizational structure.

## Features

*   **TUI Interface:** Provides an interactive terminal interface built with Textual.
*   **LLM Integration:** Connects to either a local LLM endpoint or the OpenAI API.
*   **Directory Scanning:** Scans a specified directory to identify files.
*   **LLM-Powered Analysis:** Sends file information to the configured LLM for analysis and organization suggestions.
*   **Proposed Organization Review:** Displays a table of proposed file movements for review before execution.
*   **File Organization:** Executes the proposed file movements.
*   **Configuration Management:** Allows saving and loading of connection and path settings to `config.json`.

## Requirements

*   Python 3.12+
*   Dependencies listed in `pyproject.toml`:
    *   `textual>=3.1.1`
    *   `requests>=2.32.3`

## Installation

It is highly recommended to use a virtual environment.

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <your-repo-url>
    cd reorganizer
    ```

2.  **Create and activate a virtual environment:**
    *   Using `venv`:
        ```bash
        python -m venv .venv
        source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
        ```
    *   Using `uv` (if installed):
        ```bash
        uv venv
        source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
        ```

3.  **Install dependencies:**
    *   Using `pip`:
        ```bash
        pip install .
        ```
    *   Using `uv`:
        ```bash
        uv pip install .
        ```

## Usage

Run the application using the Textual runner:

```bash
textual run app.py
```

This will launch the TUI. Follow these steps within the application:

1.  **Configure Settings:**
    *   Enter the **Scan Path** for the directory you want to organize.
    *   Choose between a local LLM or OpenAI:
        *   **Local LLM:** Enter the **LLM URL** (e.g., `http://localhost:11434` for Ollama).
        *   **OpenAI:** Check the "Use OpenAI API" box, ensure the URL is correct (`https://api.openai.com`), and enter your **OpenAI API Key**.
    *   Select the desired **LLM Model** from the dropdown (models are fetched automatically based on your URL/Key).
2.  **Submit Configuration:** Click the "Submit" button.
3.  **Analyze:** The application will scan the directory and send data to the LLM for analysis. A loading indicator will be shown.
4.  **Review Proposed Changes:** Once analysis is complete, a summary and a table showing proposed file movements will appear.
5.  **Organize (Optional):** If you approve the changes, click the "Organize Files" button to execute the file movements.
6.  **Save/Load:** Use the "Save" and "Load" buttons (or `Ctrl+S`/`Ctrl+L`) to save your configuration settings to `config.json` or load them from it.
7.  **Quit:** Click "Quit" or press `q`.

## Configuration (`config.json`)

The application can save and load its configuration (Scan Path, LLM details) to a `config.json` file in the project root. This allows you to easily reuse your settings.

## Best Practices

*   **Virtual Environments:** Always use a virtual environment to manage dependencies and avoid conflicts.
*   **Review Changes:** Carefully review the proposed file organization plan in the TUI before clicking "Organize Files". File operations can be hard to undo.
*   **LLM Access:** Ensure the LLM endpoint (local URL or OpenAI) is accessible from the machine running the application. Check firewalls if necessary.
*   **API Keys:** Keep your OpenAI API key secure. Do not commit it directly into version control. Consider using environment variables or other secure methods if adapting the script for wider use.
*   **Backup:** Consider backing up important directories before running the organization step, especially during initial use.