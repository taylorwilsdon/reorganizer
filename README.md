# 📂 Reorganizer

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python)
![Textual TUI](https://img.shields.io/badge/UI-Textual-8a2be2?logo=terminal)
![License MIT](https://img.shields.io/badge/license-MIT-green)
![Made with 🦙](https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI-ff69b4)

> **Zero-cloud, zero-hassle file re-organizer powered by fully local Large Language Models.**  
> Bring order to chaotic folders in seconds - completely private, safe and reproducible.

---

## ✨ Why Reorganizer?

| 🔒 100 % Local | ⚡ Blazing-Fast | 🧠 LLM-Smart |
|---------------|---------------|--------------|
| Runs completely offline with vLLM, Ollama, LMStudio or any OpenAI-compatible endpoint—your data never leaves your machine. | Multi-threaded directory walk + streaming chunked prompts keep even huge codebases responsive. | Automatic model detection chooses the smallest model that can handle your corpus; deep heuristics craft an optimal folder hierarchy before anything is moved. |

---

## 🚀 Features

| Category | Highlights |
|----------|------------|
| **Rich Interactive CLI** | • Textual-powered UI with mouse/keyboard shortcuts<br>• Live progress bars & diff view |
| **Automatic Model Detection** | • Probes your LLM endpoint and lists available models<br>• Scores them on context window & cost before selection |
| **Smart Restructure Engine** | • Token-aware chunking → semantic grouping<br>• Suggests new folders (e.g. `docs/`, `tests/`) with confidence scores<br>• Detects duplicates, temp files, & orphaned assets |
| **Dry-Run Safety** | • Full preview table of planned moves/renames<br>• Per-file accept ✚ / skip ⨯ toggles |
| **Config Profiles** | • Save/load multiple `config.json` sets (work, personal…) |
| **Perf-First Design** | • Async I/O, incremental hashing, and path caching<br>• Typical 10k-file repo analyzed in **< 3 s** on an M2 Pro |

---

## 🛠 Requirements

* Python **3.12+**
* Dependencies in `pyproject.toml`  
  `textual >= 3.1.1`, `requests >= 2.32.3`

---

## 📦 Installation

```bash
# 1. Clone
git clone https://github.com/yourname/reorganizer.git
cd reorganizer

# 2. Create & activate a virtualenv (choose one)
python -m venv .venv            # built-in
# OR
uv venv                         # lightning-fast alternative
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install
pip install .                   # or: uv pip install .
```

---

## ⚡ Quick Start

```bash
python app.py
```

1. **Scan Path** – paste the folder you want tamed.  
2. **Endpoint** – choose **Local LLM** (`http://localhost:11434`) *or* any OpenAI-compatible URL.  
3. **Model** – pick from the auto-populated list.  
4. **Analyze** – watch the live log; grab a coffee ☕.  
5. **Review** – accept/skip individual moves.  
6. **Organize** – hit **Enter** and enjoy a pristine directory tree.

---

## 💾 Configuration (`config.json`)

```jsonc
{
  "scan_path": "~/Downloads",
  "use_openai": false,
  "llm_url": "http://localhost:11434",
  "model": "mistral:7b-instruct",
  "api_key": null
}
```

Store multiple profiles (e.g. `config.work.json`) and load them on launch:  
`python app.py --config config.work.json`

---

## 🏗️ Architecture at a Glance

```text
┌──────────────┐     async walk      ┌─────────────────┐
│   Scanner    │ ──────────────────▶ │  File Registry  │
└──────────────┘                     └────────┬────────┘
                       metadata/embeddings     │
                                               ▼
                                   ┌────────────────────┐
                                   │  LLM Analysis API  │  ⇦ local or OpenAI
                                   └────────┬───────────┘
                                            │  plan (JSON)
                                            ▼
                                 ┌────────────────────┐
                                 │  Planner / Diff UI │
                                 └────────┬───────────┘
                                            │  user accepts
                                            ▼
                                   ┌─────────────────┐
                                   │   Executor      │
                                   └─────────────────┘
```

---

## 🧑‍💻 Contributing

1. Fork & branch off `main`.  
2. Follow the **Dev Setup** in [`CONTRIBUTING.md`](CONTRIBUTING.md).  
3. Run `pre-commit install` to keep the codebase tidy.  
4. Open a PR—tests & readable commits appreciated!

---

## 📝 License

Released under the MIT License—see [`LICENSE`](LICENSE) for details.

---

> **Need help?** Open an issue or join our Discussions board.  
> **Love it?** ⭐ Star the repo & share the productivity!

```
