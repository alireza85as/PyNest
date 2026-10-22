"""Tests for PyNest's helper functions."""

import os
import re
from pathlib import Path

import pytest

import llm
import project


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise project.requests.HTTPError(str(self.status_code))


def test_get_python_version_returns_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", project.get_python_version())


def test_normalize_package_name():
    assert llm.normalize_package_name("Scikit_Learn") == "scikit-learn"
    assert llm.normalize_package_name("  My_Cool.Package ") == "my-cool-package"


def test_parse_package_input():
    packages = project.parse_package_input("Requests, numpy>=1.24 , django==5.0,")
    assert packages == [
        {"name": "requests", "version": None, "reason": "Added manually"},
        {"name": "numpy", "version": ">=1.24", "reason": "Added manually"},
        {"name": "django", "version": "==5.0", "reason": "Added manually"},
    ]


def test_parse_package_input_rejects_garbage():
    with pytest.raises(ValueError):
        project.parse_package_input("!!!")


def test_parse_llm_response_plain_json():
    text = (
        '{"packages": [{"name": "Flask", "version": "3.0.0", "reason": "web server"}]}'
    )
    assert llm.parse_llm_response(text) == [
        {"name": "flask", "version": "3.0.0", "reason": "web server"}
    ]


def test_parse_llm_response_with_fences():
    text = (
        "Sure! Here you go:\n"
        '```json\n{"packages": [{"name": "requests", "version": null, "reason": "http"}]}\n```'
    )
    assert llm.parse_llm_response(text) == [
        {"name": "requests", "version": None, "reason": "http"}
    ]


def test_parse_llm_response_rejects_plain_text():
    with pytest.raises(ValueError):
        llm.parse_llm_response("I have no idea what you mean.")


def test_build_llm_system_prompt():
    prompt = llm.build_llm_system_prompt("3.11.4")
    assert '"packages"' in prompt
    assert "Python 3.11.4" in prompt
    assert "15 packages" in prompt


def test_get_llm_provider(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm.get_llm_provider() == "openai"
    monkeypatch.setenv("LLM_PROVIDER", " Gemini ")
    assert llm.get_llm_provider() == "gemini"
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    with pytest.raises(ValueError):
        llm.get_llm_provider()


def test_analyze_with_openai_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.analyze_with_llm("a web scraper", "3.11.4")


def test_analyze_with_gemini_requires_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.analyze_with_llm("a web scraper", "3.11.4")


def test_build_pip_spec():
    assert project.build_pip_spec("requests", None) == "requests"
    assert project.build_pip_spec("requests", "2.31.0") == "requests==2.31.0"
    assert project.build_pip_spec("numpy", ">=1.24") == "numpy>=1.24"


def test_build_pip_install_args():
    python_exe = Path("python")
    args = project.build_pip_install_args(
        python_exe,
        [{"name": "flask", "version": "3.0.0"}, {"name": "requests", "version": None}],
    )
    assert args[:4] == [str(python_exe), "-m", "pip", "install"]
    assert args[4:] == ["flask==3.0.0", "requests"]


def test_check_package_on_pypi_found_and_compatible(monkeypatch):
    payload = {
        "info": {
            "requires_python": ">=3.8",
            "version": "2.31.0",
            "summary": "HTTP library",
        }
    }
    monkeypatch.setattr(
        project.requests, "get", lambda url, timeout: FakeResponse(payload=payload)
    )
    report = project.check_package_on_pypi("requests", None, "3.11.4")
    assert report["found"] is True
    assert report["compatible"] is True
    assert report["latest"] == "2.31.0"


def test_check_package_on_pypi_incompatible_python(monkeypatch):
    payload = {"info": {"requires_python": ">=3.13", "version": "1.0.0", "summary": ""}}
    monkeypatch.setattr(
        project.requests, "get", lambda url, timeout: FakeResponse(payload=payload)
    )
    report = project.check_package_on_pypi("newthing", None, "3.11.4")
    assert report["found"] is True
    assert report["compatible"] is False


def test_check_package_on_pypi_missing(monkeypatch):
    monkeypatch.setattr(
        project.requests, "get", lambda url, timeout: FakeResponse(status_code=404)
    )
    report = project.check_package_on_pypi("nope", None, "3.11.4")
    assert report["found"] is False


def test_check_package_on_pypi_uses_base_slug_for_ranges(monkeypatch):
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        return FakeResponse(
            payload={
                "info": {"requires_python": None, "version": "1.26.0", "summary": ""}
            }
        )

    monkeypatch.setattr(project.requests, "get", fake_get)
    project.check_package_on_pypi("numpy", ">=1.24", "3.11.4")
    assert captured["url"].endswith("/pypi/numpy/json")


def test_validate_packages_drops_unknown(monkeypatch):
    def fake_check(name, version, python_version):
        if name == "ghost":
            return {
                "name": name,
                "found": False,
                "compatible": False,
                "latest": None,
                "error": "Not found on PyPI",
            }
        return {
            "name": name,
            "found": True,
            "compatible": True,
            "latest": "1.0",
            "error": None,
        }

    monkeypatch.setattr(project, "check_package_on_pypi", fake_check)
    packages = [
        {"name": "requests", "version": None, "reason": ""},
        {"name": "ghost", "version": None, "reason": ""},
    ]
    valid, problems = project.validate_packages(packages, "3.11.4")
    assert [pkg["name"] for pkg in valid] == ["requests"]
    assert len(problems) == 1 and "ghost" in problems[0]


def test_prepare_project_path_creates_folder(tmp_path):
    target = tmp_path / "new" / "project"
    result = project.prepare_project_path(str(target))
    assert result == target.resolve()
    assert target.is_dir()


def test_prepare_project_path_rejects_file(tmp_path):
    file_path = tmp_path / "not-a-dir"
    file_path.touch()
    with pytest.raises(ValueError):
        project.prepare_project_path(str(file_path))


def test_get_venv_python_path():
    venv_dir = Path("C:/tmp/foo") if os.name == "nt" else Path("/tmp/foo")
    if os.name == "nt":
        expected = venv_dir / "Scripts" / "python.exe"
    else:
        expected = venv_dir / "bin" / "python"
    assert project.get_venv_python(venv_dir) == expected
