# PyNest

> Describe your project — PyNest picks the right packages with an LLM, creates the virtual environment, installs everything, and writes `requirements.txt`.

PyNest is a CLI wizard that removes the boring setup from starting a Python project. Describe what you want to build (an LLM suggests the PyPI packages) or type the package names yourself. Every package is validated against PyPI and your local Python version, nothing is installed until you approve, and you end up with a ready-to-code project folder.

## Features

- **LLM-powered suggestions** — describe your idea, get a reviewed package list via **Google Gemini** or any OpenAI-compatible API (OpenAI, OpenRouter, Groq, Ollama, ...).
- **Manual mode** — already know your packages? Just type them: `requests, numpy>=1.24`.
- **Compatibility checks** — each package is verified on PyPI and matched against your installed Python version (`requires_python`) before anything is installed.
- **Automatic scaffolding** — creates the project folder and a `.venv`, installs the approved packages, and freezes a pinned `requirements.txt`.
- **Safe by default** — nothing is installed until you confirm; API keys live in `.env`, which is never committed.

## Requirements

- Python **3.10+**
- An API key for the LLM provider (only needed for "describe" mode)

## Quick start

```bash
git clone https://github.com/alireza85as/pynest.git
cd pynest
pip install -r requirements.txt

cp .env.example .env   # then edit .env and set your API key

python project.py
```

The wizard will ask:

1. **Where the project should live** — an existing or new folder path.
2. **How to pick packages** — `describe` (LLM) or `manual`.
3. **Confirmation** — a table of the proposed packages; nothing installs before you agree.

## Example session

```text
Where should the project live? (folder path): C:\code\web-scraper
How do you want to pick packages? [describe/manual] (describe): describe
Describe the project you want to build: a web scraper that saves articles to CSV

Proposed packages (Python 3.11.15)
 #  Package         Version  Why
 1  requests        latest   fetch pages over HTTP
 2  beautifulsoup4  latest   parse HTML content
 3  pandas          latest   store results as CSV

Install these packages? [Y/n]: y
...
Project is ready!
Folder: C:\code\web-scraper
Activate the environment:
  C:\code\web-scraper\.venv\Scripts\activate
```

## Configuration (`.env`)

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | no | `openai` (default) or `gemini` |
| `OPENAI_API_KEY` | yes (openai provider) | Your OpenAI-compatible API key |
| `OPENAI_BASE_URL` | no | Any OpenAI-compatible endpoint (OpenRouter, Groq, Ollama, ...) |
| `OPENAI_MODEL` | no | Model name (default: `gpt-4o-mini`) |
| `GEMINI_API_KEY` | yes (gemini provider) | Your Google AI Studio key |
| `GEMINI_MODEL` | no | Model name (default: `gemini-2.5-flash`) |

To use Gemini instead of OpenAI:

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-google-ai-studio-key
```

## Testing

```bash
pytest
```

## Project structure

```text
pynest/
├── project.py        # CLI wizard: main(), PyPI validation, venv setup
├── llm.py            # LLM providers (OpenAI/Gemini) + reply parsing
├── test_project.py   # pytest suite
├── requirements.txt  # PyNest's own dependencies
└── .env.example      # template for API keys
```

## Roadmap

- [ ] Editable package list before install
- [ ] Node.js / npm support
- [ ] Starter templates (README, .gitignore) for generated projects
