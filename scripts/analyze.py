#!/usr/bin/env python3
"""
analyze.py - Project structure scanner for system-visualizer skill.

Scans a project directory and outputs structural data as JSON.

Usage:
    python analyze.py <project_path> [--output FILE] [--exclude DIR1 DIR2 ...]

Examples:
    python analyze.py .
    python analyze.py /path/to/project --output structure.json
    python analyze.py . --exclude node_modules dist build
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_EXCLUDES = {
    "node_modules",
    "__pycache__",
    ".git",
    "dist",
    "build",
    "vendor",
    ".venv",
    "venv",
    "target",
    ".next",
    ".nuxt",
    ".cache",
    ".output",
    "coverage",
    ".tox",
    "egg-info",
    ".eggs",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "bower_components",
    ".svn",
    ".hg",
}

LANGUAGE_MAP = {
    # JavaScript / TypeScript
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    # Python
    ".py": "Python",
    ".pyw": "Python",
    # Go
    ".go": "Go",
    # Java
    ".java": "Java",
    # Rust
    ".rs": "Rust",
    # Ruby
    ".rb": "Ruby",
    # PHP
    ".php": "PHP",
    # Swift
    ".swift": "Swift",
    # Kotlin
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    # C#
    ".cs": "C#",
    # C
    ".c": "C",
    ".h": "C",
    # C++
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    # Vue / Svelte
    ".vue": "Vue",
    ".svelte": "Svelte",
    # Dart
    ".dart": "Dart",
    # Scala
    ".scala": "Scala",
    # Elixir
    ".ex": "Elixir",
    ".exs": "Elixir",
    # Zig
    ".zig": "Zig",
    # Lua
    ".lua": "Lua",
    # R
    ".r": "R",
    ".R": "R",
    # Shell
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    # SQL
    ".sql": "SQL",
    # HTML
    ".html": "HTML",
    ".htm": "HTML",
    # CSS / SCSS / LESS
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "LESS",
    # Data / Config
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    # Markdown
    ".md": "Markdown",
    ".mdx": "MDX",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def count_lines(filepath):
    """Count the number of lines in a file.

    Handles encoding errors gracefully by falling back to latin-1,
    and returns 0 if the file cannot be read at all.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
    except Exception:
        return 0


def detect_language(filepath):
    """Return the language name for a file based on its extension, or None."""
    ext = Path(filepath).suffix
    return LANGUAGE_MAP.get(ext)


# ---------------------------------------------------------------------------
# Tree scanner
# ---------------------------------------------------------------------------

def scan_tree(root, excludes):
    """Recursively scan a directory and return a nested dict representing its structure.

    Each node contains:
      - path:     path relative to the scan root
      - name:     entry name
      - type:     "dir" or "file"

    File nodes also include:
      - size:     file size in bytes
      - language: detected language name (or None)
      - lines:    line count (only when a language is detected)

    Directory nodes include:
      - children: sorted list of child nodes

    Entries are sorted directories-first, then files, both groups in
    case-insensitive alphabetical order.

    Entries whose name is in *excludes* or that start with '.' are skipped.
    Permission and OS errors on individual entries are silently ignored.
    """
    root = Path(root).resolve()

    def _scan(dir_path):
        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            return []
        except OSError:
            return []

        dirs = []
        files = []

        for entry in entries:
            name = entry.name

            # Skip hidden entries and excluded names
            if name.startswith(".") or name in excludes:
                continue

            rel_path = str(entry.relative_to(root))

            try:
                if entry.is_dir():
                    children = _scan(entry)
                    dirs.append({
                        "path": rel_path,
                        "name": name,
                        "type": "dir",
                        "children": children,
                    })
                elif entry.is_file():
                    language = detect_language(entry)
                    node = {
                        "path": rel_path,
                        "name": name,
                        "type": "file",
                        "size": entry.stat().st_size,
                        "language": language,
                    }
                    if language is not None:
                        node["lines"] = count_lines(entry)
                    files.append(node)
            except PermissionError:
                continue
            except OSError:
                continue

        # Sort: directories first, then files; each group case-insensitive alpha
        dirs.sort(key=lambda d: d["name"].lower())
        files.sort(key=lambda f: f["name"].lower())

        return dirs + files

    children = _scan(root)

    return {
        "path": ".",
        "name": root.name,
        "type": "dir",
        "children": children,
    }


# ---------------------------------------------------------------------------
# Import dependency parsing
# ---------------------------------------------------------------------------

# Regex pattern for relative JS/TS imports:
#   - ESM named/default: import ... from './...'  or  import ... from "../..."
#   - ESM side-effect:   import './...'           or  import "../..."
#   - CJS require:       require('./...')         or  require("../...")
#   - Dynamic import:    import('./...')          or  import("../...")
# All variants require the path to start with '.' (relative import).
_JS_IMPORT_PATTERNS = [
    # ESM: import ... from './path'
    re.compile(r'''import\s+.*?\s+from\s+['"](\.[^'"]+)['"]'''),
    # ESM side-effect: import './path'
    re.compile(r'''import\s+['"](\.[^'"]+)['"]'''),
    # CJS: require('./path')
    re.compile(r'''require\(\s*['"](\.[^'"]+)['"]\s*\)'''),
    # Dynamic: import('./path')
    re.compile(r'''import\(\s*['"](\.[^'"]+)['"]\s*\)'''),
]

IMPORT_PATTERNS = {
    "JavaScript": _JS_IMPORT_PATTERNS,
    "TypeScript": _JS_IMPORT_PATTERNS,
    "Vue":        _JS_IMPORT_PATTERNS,
    "Svelte":     _JS_IMPORT_PATTERNS,
    "MDX":        _JS_IMPORT_PATTERNS,
    "Python": [
        # from package.module import name
        re.compile(r'''^\s*from\s+([\w.]+)\s+import''', re.MULTILINE),
        # import package.module
        re.compile(r'''^\s*import\s+([\w.]+)''', re.MULTILINE),
    ],
    "Go": [
        # "package/path" inside import blocks or single import
        re.compile(r'''"([^"]+)"'''),
    ],
    "Java": [
        # import package.name;
        re.compile(r'''^\s*import\s+([\w.]+)\s*;''', re.MULTILINE),
    ],
    "Rust": [
        # use crate::module::item;
        re.compile(r'''^\s*use\s+(crate::[^\s;]+)\s*;''', re.MULTILINE),
        # mod name;
        re.compile(r'''^\s*mod\s+(\w+)\s*;''', re.MULTILINE),
    ],
}

# Extensions to try when resolving JS/TS relative imports
_JS_RESOLVE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte"]


def resolve_import(from_file, import_path, root, language):
    """Resolve a relative import path to an actual file path.

    For JS/TS-family languages, tries:
      1. Exact path (import_path as-is)
      2. import_path + each candidate extension
      3. import_path/index + each candidate extension

    Returns the resolved path relative to *root*, or None if no file is found.
    """
    root = Path(root).resolve()
    from_dir = Path(from_file).resolve().parent

    if language in ("JavaScript", "TypeScript", "Vue", "Svelte", "MDX"):
        base = (from_dir / import_path).resolve()

        # 1. Exact match
        if base.is_file():
            try:
                return str(base.relative_to(root))
            except ValueError:
                return None

        # 2. Try adding extensions
        for ext in _JS_RESOLVE_EXTENSIONS:
            candidate = base.parent / (base.name + ext)
            if candidate.is_file():
                try:
                    return str(candidate.relative_to(root))
                except ValueError:
                    return None

        # 3. Try /index with each extension
        for ext in _JS_RESOLVE_EXTENSIONS:
            candidate = base / ("index" + ext)
            if candidate.is_file():
                try:
                    return str(candidate.relative_to(root))
                except ValueError:
                    return None

    # For other languages (or unresolvable JS imports), return None
    return None


def parse_imports(filepath, language, root):
    """Parse import statements from a single file and return dependency edges.

    Each edge is a dict:
        {"from": <relative path>, "to": <resolved relative path>,
         "type": "import", "raw": <original import string>}

    Unresolvable imports are silently skipped.
    """
    patterns = IMPORT_PATTERNS.get(language)
    if not patterns:
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, "r", encoding="latin-1") as f:
                content = f.read()
        except Exception:
            return []
    except Exception:
        return []

    root = Path(root).resolve()
    try:
        from_rel = str(Path(filepath).resolve().relative_to(root))
    except ValueError:
        return []

    edges = []
    seen = set()

    for pattern in patterns:
        for match in pattern.finditer(content):
            import_path = match.group(1)
            if import_path in seen:
                continue
            seen.add(import_path)

            resolved = resolve_import(filepath, import_path, root, language)
            if resolved is not None:
                edges.append({
                    "from": from_rel,
                    "to": resolved,
                    "type": "import",
                    "raw": import_path,
                })

    return edges


def collect_dependencies(tree, root):
    """Walk the scanned tree and collect import dependency edges from all files.

    Returns a list of edge dicts produced by parse_imports().
    """
    root = Path(root).resolve()
    edges = []

    def _walk(node):
        if node["type"] == "file":
            language = node.get("language")
            if language:
                abs_path = root / node["path"]
                edges.extend(parse_imports(str(abs_path), language, str(root)))
        elif node["type"] == "dir":
            for child in node.get("children", []):
                _walk(child)

    _walk(tree)
    return edges


# ---------------------------------------------------------------------------
# Project metadata detection
# ---------------------------------------------------------------------------

def detect_config(root: Path) -> dict:
    """Detect project configuration: package manager, framework, tests, Docker.

    Returns a dict with keys:
        packageManager, framework, hasTests, hasDocker
    Handles all file-read errors gracefully.
    """
    root = Path(root).resolve()
    config = {
        "packageManager": None,
        "framework": None,
        "hasTests": False,
        "hasDocker": False,
    }

    # --- Package manager & framework (JS ecosystem) ---
    package_json_path = root / "package.json"
    if package_json_path.is_file():
        config["packageManager"] = "npm"
        if (root / "yarn.lock").is_file():
            config["packageManager"] = "yarn"
        elif (root / "pnpm-lock.yaml").is_file():
            config["packageManager"] = "pnpm"
        elif (root / "bun.lockb").is_file():
            config["packageManager"] = "bun"

        # Read package.json to detect framework
        try:
            pkg = json.loads(package_json_path.read_text(encoding="utf-8"))
            all_deps = {}
            all_deps.update(pkg.get("dependencies", {}))
            all_deps.update(pkg.get("devDependencies", {}))

            if "next" in all_deps:
                config["framework"] = "Next.js"
            elif "nuxt" in all_deps:
                config["framework"] = "Nuxt"
            elif "@sveltejs/kit" in all_deps:
                config["framework"] = "SvelteKit"
            elif "react" in all_deps:
                config["framework"] = "React"
            elif "vue" in all_deps:
                config["framework"] = "Vue"
            elif "fastify" in all_deps:
                config["framework"] = "Fastify"
            elif "express" in all_deps:
                config["framework"] = "Express"
        except Exception:
            pass

    # --- Python ecosystem ---
    elif (root / "pyproject.toml").is_file() or (root / "setup.py").is_file():
        config["packageManager"] = "pip"
        # Try detecting Python frameworks from pyproject.toml
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.is_file():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                content_lower = content.lower()
                if "django" in content_lower:
                    config["framework"] = "Django"
                elif "fastapi" in content_lower:
                    config["framework"] = "FastAPI"
                elif "flask" in content_lower:
                    config["framework"] = "Flask"
            except Exception:
                pass
        # Also try setup.py
        if config["framework"] is None:
            setup_path = root / "setup.py"
            if setup_path.is_file():
                try:
                    content = setup_path.read_text(encoding="utf-8")
                    content_lower = content.lower()
                    if "django" in content_lower:
                        config["framework"] = "Django"
                    elif "fastapi" in content_lower:
                        config["framework"] = "FastAPI"
                    elif "flask" in content_lower:
                        config["framework"] = "Flask"
                except Exception:
                    pass

    # --- Go ---
    elif (root / "go.mod").is_file():
        config["packageManager"] = "go"

    # --- Rust ---
    elif (root / "Cargo.toml").is_file():
        config["packageManager"] = "cargo"

    # --- Test directories ---
    test_dirs = ["tests", "test", "__tests__", "spec", "specs"]
    for td in test_dirs:
        if (root / td).is_dir():
            config["hasTests"] = True
            break

    # --- Docker ---
    if (root / "Dockerfile").is_file():
        config["hasDocker"] = True
    elif (root / "docker-compose.yml").is_file():
        config["hasDocker"] = True
    elif (root / "docker-compose.yaml").is_file():
        config["hasDocker"] = True

    return config


def detect_entry_points(root: Path) -> list:
    """Find likely entry point files in the project.

    Returns a list of relative paths (strings) for candidates that exist.
    """
    root = Path(root).resolve()
    candidates = [
        "src/index.ts",
        "src/index.js",
        "src/main.ts",
        "src/main.js",
        "src/app.ts",
        "src/app.js",
        "index.ts",
        "index.js",
        "main.py",
        "app.py",
        "src/main.py",
        "manage.py",
        "main.go",
        "cmd/main.go",
        "src/main.rs",
        "src/lib.rs",
    ]
    found = []
    for c in candidates:
        if (root / c).is_file():
            found.append(c)
    return found


def compute_summary(tree: dict) -> dict:
    """Walk the scanned tree and compute summary statistics.

    Returns a dict with keys:
        totalFiles, totalDirs, languages (sorted by count desc), totalLines
    """
    total_files = 0
    total_dirs = 0
    languages = {}
    total_lines = 0

    def _walk(node):
        nonlocal total_files, total_dirs, total_lines

        if node["type"] == "file":
            total_files += 1
            lang = node.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
                total_lines += node.get("lines", 0)
        elif node["type"] == "dir":
            # Don't count the root itself as a dir
            if node.get("path") != ".":
                total_dirs += 1
            for child in node.get("children", []):
                _walk(child)

    _walk(tree)

    # Sort languages by count descending
    sorted_languages = dict(
        sorted(languages.items(), key=lambda item: item[1], reverse=True)
    )

    return {
        "totalFiles": total_files,
        "totalDirs": total_dirs,
        "languages": sorted_languages,
        "totalLines": total_lines,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze codebase structure")
    parser.add_argument("project_path", help="Path to project root")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file path")
    parser.add_argument("--exclude", nargs="*", default=[], help="Additional directories to exclude")
    args = parser.parse_args()

    root = Path(args.project_path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    excludes = DEFAULT_EXCLUDES | set(args.exclude)

    tree = scan_tree(str(root), excludes)
    dependencies = collect_dependencies(tree, root)

    result = {
        "projectName": root.name,
        "scanTimestamp": datetime.now(timezone.utc).isoformat(),
        "summary": compute_summary(tree),
        "tree": tree,
        "dependencies": dependencies,
        "entryPoints": detect_entry_points(root),
        "config": detect_config(root),
    }

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
