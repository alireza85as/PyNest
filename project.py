"""PyNest: scaffold ready-to-code Python projects with LLM-picked dependencies.

The wizard asks where the project should live, figures out which packages are
needed (via an LLM or manual input), validates them against PyPI and the local
Python version, creates a virtual environment, installs everything and writes
a pinned requirements.txt.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import venv
from pathlib import Path

import requests
from dotenv import load_dotenv
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
import pyfiglet

from llm import analyze_with_llm, normalize_package_name

console = Console()

PYPI_JSON_URL = "https://pypi.org/pypi/{slug}/json"
VENV_DIR_NAME = ".venv"


def get_python_version() -> str:
    """Return the version of the Python interpreter running PyNest."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def build_pip_spec(name: str, version: str | None) -> str:
    """Turn a name plus optional version/constraint into a pip requirement."""
    if not version:
        return name
    if version[0] in "<>=!~":
        return f"{name}{version}"
    return f"{name}=={version}"


def parse_package_input(raw: str) -> list[dict]:
    """Parse comma-separated manual input such as 'requests, numpy>=1.24'."""
    packages = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*([<>=!~].*)?$", chunk)
        if not match:
            raise ValueError(f"Invalid package specifier: '{chunk}'")
        version = match.group(2)
        packages.append(
            {
                "name": normalize_package_name(match.group(1)),
                "version": version.strip() if version else None,
                "reason": "Added manually",
            }
        )
    return packages


def check_package_on_pypi(name: str, version: str | None, python_version: str) -> dict:
    """Look a package up on PyPI and check it against the local Python version."""
    exact = version and version.strip() and version.strip()[0].isdigit()
    slug = f"{name}/{version.strip()}" if exact else name
    try:
        response = requests.get(PYPI_JSON_URL.format(slug=slug), timeout=15)
    except requests.RequestException as exc:
        return {
            "name": name,
            "version": version,
            "found": False,
            "compatible": False,
            "latest": None,
            "error": f"Could not reach PyPI: {exc}",
        }
    if response.status_code == 404:
        return {
            "name": name,
            "version": version,
            "found": False,
            "compatible": False,
            "latest": None,
            "error": "Not found on PyPI",
        }
    try:
        response.raise_for_status()
        info = response.json().get("info", {})
    except (requests.RequestException, ValueError) as exc:
        return {
            "name": name,
            "version": version,
            "found": False,
            "compatible": False,
            "latest": None,
            "error": f"Bad PyPI response: {exc}",
        }

    requires_python = info.get("requires_python")
    compatible = True
    if requires_python:
        try:
            compatible = SpecifierSet(requires_python).contains(python_version)
        except InvalidSpecifier:
            compatible = True
    return {
        "name": name,
        "version": version,
        "found": True,
        "compatible": compatible,
        "latest": info.get("version"),
        "requires_python": requires_python,
        "summary": (info.get("summary") or "").strip(),
        "error": (
            None
            if compatible
            else f"Requires Python {requires_python}, but you have {python_version}"
        ),
    }


def validate_packages(
    packages: list[dict], python_version: str
) -> tuple[list[dict], list[str]]:
    """Check every package on PyPI, dropping the ones that cannot be installed."""
    valid, problems = [], []
    for pkg in packages:
        report = check_package_on_pypi(pkg["name"], pkg.get("version"), python_version)
        if not report["found"] and pkg.get("version") and pkg["version"][0].isdigit():
            fallback = check_package_on_pypi(pkg["name"], None, python_version)
            if fallback["found"]:
                problems.append(
                    f"{pkg['name']}: Version {pkg['version']} not found (latest is {fallback['latest']})"
                )
            else:
                problems.append(f"{pkg['name']}: Package not found on PyPI")
            continue
        if not report["found"]:
            problems.append(f"{pkg['name']}: {report['error']}")
            continue
        if not report["compatible"]:
            problems.append(f"{pkg['name']}: {report['error']}")
            continue
        valid.append(pkg)
    return valid, problems


def prepare_project_path(raw: str) -> Path:
    """Validate the target folder, creating it when it does not exist yet."""
    path = Path(raw).expanduser().resolve()
    if path.exists() and not path.is_dir():
        raise ValueError(f"'{path}' exists and is not a folder.")
    if not path.exists():
        path.mkdir(parents=True)
    return path


def get_venv_python(venv_dir: Path) -> Path:
    """Return the path of the Python executable inside a virtual environment."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def create_virtual_environment(project_path: Path, recreate: bool = False) -> Path:
    """Create a fresh virtual environment and return its Python executable."""
    venv_dir = project_path / VENV_DIR_NAME
    if venv_dir.exists() and not recreate:
        python_exe = get_venv_python(venv_dir)
        if python_exe.exists():
            return python_exe
    venv.create(venv_dir, with_pip=True, clear=venv_dir.exists())
    return get_venv_python(venv_dir)


def build_pip_install_args(python_exe: Path, packages: list[dict]) -> list[str]:
    """Build the 'pip install' command for the chosen packages."""
    specs = [build_pip_spec(pkg["name"], pkg.get("version")) for pkg in packages]
    return [str(python_exe), "-m", "pip", "install", *specs]


def install_packages(python_exe: Path, packages: list[dict]) -> None:
    """Install every approved package into the virtual environment."""
    subprocess.run(
        [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True
    )
    subprocess.run(build_pip_install_args(python_exe, packages), check=True)


def freeze_requirements(python_exe: Path, project_path: Path) -> Path:
    """Write the environment's pinned packages to requirements.txt."""
    result = subprocess.run(
        [str(python_exe), "-m", "pip", "freeze"],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    requirements = project_path / "requirements.txt"
    requirements.write_text(result.stdout, encoding="utf-8")
    return requirements


def confirm_packages(packages: list[dict], python_version: str) -> bool:
    """Show the package list and ask the user for approval."""
    table = Table(title=f"Proposed packages (Python {python_version})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Package", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Why")
    for index, pkg in enumerate(packages, start=1):
        table.add_row(
            str(index),
            pkg["name"],
            pkg.get("version") or "latest",
            pkg.get("reason") or "-",
        )
    console.print(table)
    return Confirm.ask("Install these packages?", default=True)


def main() -> None:
    """Run the PyNest wizard from start to finish."""
    load_dotenv()
    os.system("cls" if os.name == "nt" else "clear")

    GREEN = "\033[92m"
    WHITE = "\033[97m"
    RESET = "\033[0m"

    first = pyfiglet.figlet_format("Py", font="slant").splitlines()
    rest = pyfiglet.figlet_format("Nest", font="slant").splitlines()

    for a, b in zip(first, rest):
        print(f"{GREEN}{a}{WHITE}{b}{RESET}")

    print()
    info_table = Table(show_header=False, box=None, padding=(0, 2), expand=False)

    info_table.add_column(style="dim")
    info_table.add_column(style="cyan")

    info_table.add_row("Description", "Scaffold Python projects with the right dependencies")
    info_table.add_row("Author", "Alireza Asadiyan")
    info_table.add_row("Version", "1.0.0")

    console.print(info_table)
    console.print()

    python_version = get_python_version()
    console.print(f"Using Python [green]{python_version}[/green] ({sys.executable})")

    while True:
        raw = Prompt.ask("Where should the project live? (folder path)")
        try:
            project_path = prepare_project_path(raw)
            break
        except (ValueError, OSError) as exc:
            console.print(f"[red]{exc}[/red] Try again.")
    if any(project_path.iterdir()) and not Confirm.ask(
        "That folder is not empty. Continue anyway?", default=True
    ):
        console.print("Aborted.")
        return

    mode = Prompt.ask(
        "How do you want to pick packages?",
        choices=["describe", "manual"],
        default="describe",
    )
    try:
        if mode == "describe":
            description = ""
            while not description.strip():
                description = Prompt.ask("Describe the project you want to build")
            with console.status("Asking the LLM for a package list..."):
                packages = analyze_with_llm(description, python_version)
        else:
            packages = []
            while not packages:
                raw_packages = Prompt.ask(
                    "Enter packages, comma separated (e.g. requests, numpy>=1.24)"
                )
                try:
                    packages = parse_package_input(raw_packages)
                except ValueError as exc:
                    console.print(f"[red]{exc}[/red]")
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return
    except Exception as exc:
        console.print(f"[red]LLM request failed:[/red] {exc}")
        return

    with console.status("Checking packages on PyPI..."):
        packages, problems = validate_packages(packages, python_version)
    for problem in problems:
        console.print(f"[yellow]Skipped:[/yellow] {problem}")
    if not packages:
        console.print("[red]Nothing left to install.[/red]")
        return

    if not confirm_packages(packages, python_version):
        console.print("Aborted.")
        return

    venv_dir = project_path / VENV_DIR_NAME
    recreate = venv_dir.exists() and Confirm.ask(
        "[yellow].venv already exists. Recreate it?[/yellow]", default=True
    )
    try:
        console.print("[bold]Creating the virtual environment...[/bold]")
        python_exe = create_virtual_environment(project_path, recreate=recreate)
        console.print(f"[bold]Installing {len(packages)} package(s)...[/bold]")
        install_packages(python_exe, packages)
        requirements = freeze_requirements(python_exe, project_path)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Command failed:[/red] {' '.join(map(str, exc.cmd))}")
        return
    except OSError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return

    if os.name == "nt":
        activate_cmd = str(venv_dir / "Scripts" / "activate")
    else:
        activate_cmd = f"source {venv_dir / 'bin' / 'activate'}"
    console.print(
        Panel.fit(
            f"[bold green]Project is ready![/bold green]\n"
            f"Folder: {project_path}\n"
            f"Requirements: {requirements}\n\n"
            f"Activate the environment:\n  {activate_cmd}",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
