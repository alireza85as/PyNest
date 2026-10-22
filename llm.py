"""LLM-based dependency analysis for PyNest.

Asks the configured provider (OpenAI-compatible or Google Gemini) which
PyPI packages a described project needs, and parses the reply into
package dicts ready for PyPI validation.
"""

from __future__ import annotations

import json
import os
import re

from openai import OpenAI


def normalize_package_name(name: str) -> str:
    """Normalize a package name according to PEP 503."""
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def parse_llm_response(text: str) -> list[dict]:
    """Extract the package list from an LLM reply (tolerates markdown fences)."""
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    payload = fence.group(1) if fence else text
    start, end = payload.find("{"), payload.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("The LLM reply does not contain any JSON object.")
    data = json.loads(payload[start : end + 1])
    items = data.get("packages", []) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("The LLM reply does not contain a package list.")

    packages, seen = [], set()
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = normalize_package_name(str(item["name"]))
        if name in seen:
            continue
        seen.add(name)
        version = item.get("version")
        version = str(version).strip() if version not in (None, "") else None
        packages.append(
            {
                "name": name,
                "version": version,
                "reason": str(item.get("reason", "")).strip(),
            }
        )
    if not packages:
        raise ValueError("The LLM suggested no packages.")
    return packages


def build_llm_system_prompt(python_version: str) -> str:
    """Build the shared system prompt used by every LLM provider."""
    json_shape = '{"packages": [{"name": "package-name", "version": "1.2.3" | null, "reason": "why it is needed"}]}'
    return "\n".join(
        [
            "You are a Python dependency advisor. The user describes a project and you reply with the PyPI packages required to build it.",
            "Reply with ONLY a JSON object of the form:",
            json_shape,
            "Rules:",
            "- Use real PyPI package names.",
            f"- Suggest versions that work with Python {python_version}, or null for the latest release.",
            "- Suggest at most 15 packages and only ones the project really needs.",
            "- Keep every reason under 12 words.",
        ]
    )


def get_llm_provider() -> str:
    """Return the configured LLM provider: 'openai' (default) or 'gemini'."""
    provider = (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if provider not in ("openai", "gemini"):
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Use 'openai' or 'gemini'."
        )
    return provider


def analyze_with_openai(description: str, python_version: str) -> list[dict]:
    """Ask an OpenAI-compatible endpoint which packages the project needs."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": build_llm_system_prompt(python_version)},
            {
                "role": "user",
                "content": f"Python version on this machine: {python_version}\nProject description: {description}",
            },
        ],
    )
    return parse_llm_response(response.choices[0].message.content or "")


def analyze_with_gemini(description: str, python_version: str) -> list[dict]:
    """Ask Google Gemini which packages the described project needs."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "The 'google-genai' package is missing. Run: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    response = client.models.generate_content(
        model=model,
        contents=f"Python version on this machine: {python_version}\nProject description: {description}",
        config=types.GenerateContentConfig(
            system_instruction=build_llm_system_prompt(python_version),
            temperature=0.2,
        ),
    )
    return parse_llm_response(response.text or "")


def analyze_with_llm(description: str, python_version: str) -> list[dict]:
    """Ask the configured LLM provider which packages the project needs."""
    if get_llm_provider() == "gemini":
        return analyze_with_gemini(description, python_version)
    return analyze_with_openai(description, python_version)
