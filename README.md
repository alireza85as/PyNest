# PyNest

**Describe your project. Get the right packages. Start coding.**

PyNest is an LLM-powered CLI wizard that simplifies Python project setup. Describe your project in plain English to receive package recommendations, or specify dependencies manually. PyNest validates packages against PyPI and your local Python version, creates a virtual environment, installs approved dependencies, and generates a pinned `requirements.txt` file.

**[▶ Watch the Project Demo](https://youtu.be/3szYAa6oRUQ)** · **[GitHub Repository](https://github.com/alireza85as/pynest)**

## Features

- **LLM-Powered Package Suggestions** — Describe your project in plain English and receive relevant package recommendations using Google Gemini or any OpenAI-compatible API, including OpenAI, OpenRouter, Groq, and Ollama.
- **Manual Package Selection** — Specify packages and version constraints directly, such as `requests` or `numpy>=1.24`.
- **Package Validation** — Verify that packages exist on PyPI and check their declared Python version requirements against your local Python interpreter.
- **Automated Project Setup** — Create the project directory and a dedicated `.venv` virtual environment, then install approved dependencies.
- **Pinned Dependencies** — Generate a `requirements.txt` file containing the installed package versions.
- **User-Controlled Installation** — Review the proposed packages and confirm before installation begins.
- **Environment-Based Configuration** — Store API credentials in `.env` instead of committing secrets to version control.

## Requirements

- Python 3.10 or later
- An LLM provider API key for `describe` mode
- Internet access for package validation, LLM requests, and dependency installation

Manual mode does not require an LLM API key.

## Installation

Clone the repository and install PyNest's dependencies:

```bash
git clone https://github.com/alireza85as/pynest.git
cd pynest
pip install -r requirements.txt
```

Create your environment configuration file:

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

Edit `.env` and configure your LLM provider if you intend to use `describe` mode.

Run PyNest:

```bash
python project.py
```

## Usage

PyNest guides you through three main steps:

1. **Choose a project location** — specify an existing or new directory for your project.
2. **Select a package selection mode** — choose `describe` for LLM-powered recommendations or `manual` to enter dependencies yourself.
3. **Review and confirm** — inspect the proposed packages and approve the installation.

Once confirmed, PyNest creates the virtual environment, installs the selected dependencies, and generates `requirements.txt`.

## Example

Suppose you want to build a web scraper that extracts article information and exports it to CSV.

Describe your project:

```text
I want to create a web scraper that extracts article titles
and URLs from websites and saves them to a CSV file.
I need suitable Python packages for this project.
```

PyNest may recommend packages such as:

| Package | Purpose |
|---|---|
| `requests` | Fetch web pages over HTTP |
| `beautifulsoup4` | Parse HTML and extract article information |
| `pandas` | Organize data and export it to CSV |

The actual recommendations depend on the LLM response and the project description.

After reviewing the package list, approve the installation to continue.

Example output:

```text
Project is ready!
Folder: C:\code\web-scraper

Activate the environment:
  C:\code\web-scraper\.venv\Scripts\activate
```

## Configuration

PyNest uses a `.env` file to configure the LLM provider.

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | No | Provider selection: `openai` (default) or `gemini` |
| `OPENAI_API_KEY` | For OpenAI-compatible providers | API key for the selected endpoint |
| `OPENAI_BASE_URL` | No | Custom OpenAI-compatible API endpoint |
| `OPENAI_MODEL` | No | Model name; defaults to `gpt-4o-mini` |
| `GEMINI_API_KEY` | For Gemini | Google AI Studio API key |
| `GEMINI_MODEL` | No | Gemini model; defaults to `gemini-2.5-flash` |

### Using Google Gemini

Configure your `.env` file:

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-google-ai-studio-key
```

### Using an OpenAI-Compatible API

```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=your-provider-endpoint
OPENAI_MODEL=your-model-name
```

Use the endpoint and model name provided by your chosen service. Never commit your actual API keys to GitHub.

## Testing

PyNest includes an automated test suite built with `pytest`.

Run the tests from the project root:

```bash
pytest
```

## Project Structure

```text
pynest/
├── project.py        # CLI workflow, PyPI validation, and environment setup
├── llm.py            # LLM provider integration and response parsing
├── test_project.py   # Automated tests
├── requirements.txt  # PyNest's dependencies
└── .env.example      # Environment configuration template
```

## Roadmap

- [ ] Allow users to edit the proposed package list before installation
- [ ] Add Node.js and npm project support
- [ ] Generate starter files such as `README.md` and `.gitignore`

## Built With

- Python
- Google Gemini and OpenAI-compatible LLM APIs
- PyPI
- `venv` and `pip`
- `pytest`

---

**PyNest — Spend less time setting up projects and more time building them.**
