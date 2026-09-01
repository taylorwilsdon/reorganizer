<div align="center">

# Reorganizer

A terminal app that asks an LLM to sort a directory, shows you the proposed moves, and waits for your approval before changing anything.

<p>
  <a href="https://www.python.org/downloads/"><img alt="Python 3.12+" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://textual.textualize.io/"><img alt="Textual UI" src="https://img.shields.io/badge/UI-Textual-8A2BE2"></a>
  <a href="https://ollama.com/"><img alt="Ollama and OpenAI" src="https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI-555555"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-2EA44F"></a>
</p>

[How it works](#how-it-works) · [Install](#installation) · [Usage](#usage) · [Configuration](#configuration)

</div>

Reorganizer recursively scans a folder and sends its relative file paths to either a local Ollama server or the OpenAI API. The selected model returns a list of file moves, which the app presents in a Textual interface before you choose whether to apply the plan.

No file contents are sent to the model. Reorganizer only includes relative paths in the request. If you use OpenAI, those paths leave your machine. A local model keeps the request local.

## How it works

1. Choose the directory you want to organize.
2. Connect to Ollama or enable the OpenAI API.
3. Select one of the models reported by the endpoint.
4. Review the proposed source and destination paths.
5. Apply the complete plan or cancel it.

Reorganizer creates destination folders as needed and skips a move if the destination already exists. It also rejects paths that begin with `..`. Only files are moved; directories are left in place.

> [!CAUTION]
> Applying a plan moves files on disk. Review every proposed destination first, and keep a backup of anything important.

## Features

- Terminal interface built with Textual
- Recursive directory scanning
- Support for Ollama and the OpenAI API
- Automatic model list retrieval from the configured endpoint
- Preview table for every proposed move
- Explicit confirmation before files are moved
- Collision checks and basic path traversal protection
- Saved settings in a local `config.json` file

The model request is currently limited to the first 500 file paths in a scan.

## Requirements

- Python 3.12 or newer
- An Ollama server with a model installed, or an OpenAI API key

## Installation

Clone the repository and install it in a virtual environment:

```bash
git clone https://github.com/taylorwilsdon/reorganizer.git
cd reorganizer

python -m venv .venv
source .venv/bin/activate
pip install .
```

With `uv`:

```bash
git clone https://github.com/taylorwilsdon/reorganizer.git
cd reorganizer

uv sync
```

## Usage

Start your LLM server first if you are using a local model. The default endpoint is `http://localhost:11434`.

Run the app with the virtual environment active:

```bash
python app.py
```

Or run it through `uv`:

```bash
uv run python app.py
```

In the app:

1. Enter a scan path.
2. Leave **Use OpenAI API** unchecked for Ollama, or enable it and enter your API key.
3. Select a model after the list loads.
4. Select **Submit** to build a plan.
5. Review the proposed moves, then select **Organize Files** or **Cancel**.

Keyboard shortcuts:

| Shortcut | Action |
| --- | --- |
| `Ctrl+S` | Save configuration |
| `Ctrl+L` | Load configuration |
| `Q` | Quit |

## Configuration

The **Save** button writes the current settings to `config.json` in the working directory. **Load** reads that file back into the app.

```json
{
  "scan_path": "/Users/example/Downloads",
  "use_openai_api": false,
  "llm_url": "http://localhost:11434",
  "openai_key": "",
  "model": "llama3.2:latest"
}
```

The OpenAI API key is stored as plain text when you save the configuration. Do not commit `config.json` or share it if it contains a key.

## Project structure

```text
app.py                  Textual application and workflow
cli_config.py           Configuration loading and saving
styles.py               Textual styles
utils/file_scanner.py   Recursive directory scanner
utils/list_models.py    Model discovery
utils/analysis.py       LLM request and plan validation
utils/organizer.py      File move execution
```

## License

Reorganizer is available under the [MIT License](LICENSE).
