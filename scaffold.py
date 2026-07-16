"""
Reusable Project Scaffold Generator
-----------------------------------

Creates directories and empty files for a project structure.

Usage:
    python scaffold_project.py kenyan-poker

Optional:
    python scaffold_project.py my-project --template kadi
    python scaffold_project.py my-project --overwrite

Design goals:
- Reusable for other projects
- Safe by default: does not overwrite existing files
- Simple dictionary-based templates
- Easy to extend
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List


ProjectTemplate = Dict[str, List[str]]


TEMPLATES: dict[str, ProjectTemplate] = {
    "kadi": {
        "directories": [
            "backend/app",
            "backend/app/rules",
            "backend/app/game",
            "backend/app/api",
            "backend/tests",
            "frontend",
            "docs",
        ],
        "files": [
            # Backend app root
            "backend/app/__init__.py",
            "backend/app/main.py",

            # Rules engine
            "backend/app/rules/__init__.py",
            "backend/app/rules/cards.py",
            "backend/app/rules/config.py",
            "backend/app/rules/actions.py",
            "backend/app/rules/state.py",
            "backend/app/rules/events.py",
            "backend/app/rules/engine.py",

            # Game/session layer
            "backend/app/game/__init__.py",
            "backend/app/game/room.py",
            "backend/app/game/room_manager.py",
            "backend/app/game/serializers.py",

            # API/networking layer
            "backend/app/api/__init__.py",
            "backend/app/api/routes.py",
            "backend/app/api/websocket.py",

            # Tests
            "backend/tests/__init__.py",
            "backend/tests/test_rules_engine.py",
            "backend/tests/test_questions.py",
            "backend/tests/test_draws.py",
            "backend/tests/test_skips.py",
            "backend/tests/test_ace_rules.py",
            "backend/tests/test_finish_rules.py",

            # Backend utility/config files
            "backend/requirements.txt",
            "backend/pytest.ini",

            # Frontend placeholder
            "frontend/README.md",

            # Project docs
            "docs/rules.md",
            "docs/architecture.md",
            "README.md",
            ".gitignore",
        ],
    },

    # Example reusable empty Python service template
    "python-service": {
        "directories": [
            "app",
            "app/core",
            "app/api",
            "tests",
            "docs",
        ],
        "files": [
            "app/__init__.py",
            "app/main.py",
            "app/core/__init__.py",
            "app/api/__init__.py",
            "tests/__init__.py",
            "tests/test_app.py",
            "requirements.txt",
            "pytest.ini",
            "README.md",
            ".gitignore",
        ],
    },
}


DEFAULT_FILE_CONTENTS: dict[str, str] = {
    ".gitignore": """__pycache__/
*.pyc
.env
.venv/
venv/
node_modules/
dist/
build/
.coverage
.pytest_cache/
""",

    "README.md": """# Project

Generated project scaffold.

""",

    "backend/requirements.txt": """fastapi
uvicorn[standard]
pydantic
pytest
""",

    "backend/pytest.ini": """[pytest]
pythonpath = .
testpaths = tests
""",

    "frontend/README.md": """# Frontend

Frontend will be generated later.

""",

    "docs/rules.md": """# Game Rules

Document the locked Kenyan Poker rules here.

""",

    "docs/architecture.md": """# Architecture

Document the backend, rules engine, networking, and frontend architecture here.

""",
}


def create_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def create_file(path: Path, overwrite: bool = False) -> str:
    if path.exists() and not overwrite:
        return "skipped"

    path.parent.mkdir(parents=True, exist_ok=True)

    relative_path = str(path).replace("\\", "/")
    file_name = path.name

    content = ""

    # Match exact relative suffixes so the script remains reusable
    for key, value in DEFAULT_FILE_CONTENTS.items():
        if relative_path.endswith(key):
            content = value
            break

    path.write_text(content, encoding="utf-8")
    return "created" if content else "created_empty"


def scaffold_project(
    project_name: str,
    template_name: str = "kadi",
    overwrite: bool = False,
) -> None:
    if template_name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise ValueError(
            f"Unknown template '{template_name}'. Available templates: {available}"
        )

    project_root = Path(project_name)
    template = TEMPLATES[template_name]

    print(f"Creating project: {project_root}")
    print(f"Using template: {template_name}")
    print("-" * 60)

    create_directory(project_root)

    for directory in template["directories"]:
        directory_path = project_root / directory
        create_directory(directory_path)
        print(f"[DIR]  {directory_path}")

    print("-" * 60)

    created = 0
    skipped = 0

    for file_path in template["files"]:
        full_path = project_root / file_path
        status = create_file(full_path, overwrite=overwrite)

        if status == "skipped":
            skipped += 1
            print(f"[SKIP] {full_path}")
        elif status == "created_empty":
            created += 1
            print(f"[FILE] {full_path}")
        else:
            created += 1
            print(f"[FILE] {full_path}")

    print("-" * 60)
    print("Scaffold complete.")
    print(f"Files created: {created}")
    print(f"Files skipped: {skipped}")
    print(f"Root folder:   {project_root.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reusable project scaffold generator"
    )

    parser.add_argument(
        "project_name",
        help="Name of the project folder to create",
    )

    parser.add_argument(
        "--template",
        default="kadi",
        choices=sorted(TEMPLATES.keys()),
        help="Project template to use",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    scaffold_project(
        project_name=args.project_name,
        template_name=args.template,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()