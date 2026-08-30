# System Visualizer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Claude Code skill that auto-analyzes codebases and generates an interactive HTML visualization with 4 views (structure, dependencies, flow, architecture).

**Architecture:** Hybrid approach - Python script collects structural data (directory tree, imports), Claude infers architecture layers and data flows, then generates an interactive HTML page using D3.js and Mermaid.js from a template.

**Tech Stack:** Python 3 (stdlib only), D3.js v7 (CDN), Mermaid.js (CDN), single-file HTML output

---

### Task 1: Create analyze.py - CLI skeleton and directory tree scanner

**Files:**
- Create: `scripts/analyze.py`

**Step 1: Write the script with CLI argument parsing and tree scanning**

```python
#!/usr/bin/env python3
"""
System Visualizer - Codebase Analyzer
Scans a project directory and outputs structural data as JSON.

Usage:
    python analyze.py /path/to/project
    python analyze.py /path/to/project --output project-data.json
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_EXCLUDES = {
    "node_modules", "__pycache__", ".git", "dist", "build", "vendor",
    ".venv", "venv", "target", ".next", ".nuxt", ".cache", ".output",
    "coverage", ".tox", "egg-info", ".eggs", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", "bower_components", ".svn", ".hg",
}

LANGUAGE_MAP = {
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    ".py": "Python", ".pyw": "Python",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin", ".kts": "Kotlin",
    ".cs": "C#",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".hpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".dart": "Dart",
    ".scala": "Scala",
    ".ex": "Elixir", ".exs": "Elixir",
    ".zig": "Zig",
    ".lua": "Lua",
    ".r": "R", ".R": "R",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".sql": "SQL",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".less": "LESS",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
    ".md": "Markdown", ".mdx": "MDX",
}


def count_lines(filepath: str) -> int:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def detect_language(filepath: str) -> str | None:
    ext = Path(filepath).suffix.lower()
    return LANGUAGE_MAP.get(ext)


def scan_tree(root: str, excludes: set[str]) -> dict:
    root_path = Path(root).resolve()
    name = root_path.name

    def _scan(dirpath: Path) -> dict:
        node = {
            "path": str(dirpath.relative_to(root_path)),
            "name": dirpath.name,
            "type": "dir",
            "children": [],
        }
        try:
            entries = sorted(dirpath.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return node

        for entry in entries:
            if entry.name in excludes or entry.name.startswith("."):
                continue
            if entry.is_dir():
                node["children"].append(_scan(entry))
            elif entry.is_file():
                lang = detect_language(str(entry))
                lines = count_lines(str(entry)) if lang else 0
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                node["children"].append({
                    "path": str(entry.relative_to(root_path)),
                    "name": entry.name,
                    "type": "file",
                    "size": size,
                    "language": lang,
                    "lines": lines,
                })
        return node

    return _scan(root_path)
```

**Step 2: Run to verify tree scanning works**

Run: `python scripts/analyze.py /path/to/small/project 2>&1 | head -50`
Expected: JSON output with tree structure

**Step 3: Commit**

```bash
git add scripts/analyze.py
git commit -m "feat: add analyze.py with CLI and directory tree scanner"
```

---

### Task 2: Add import dependency parsing to analyze.py

**Files:**
- Modify: `scripts/analyze.py`

**Step 1: Add import pattern parsers**

Append to `analyze.py`:

```python
# --- Import Parsing ---

IMPORT_PATTERNS = {
    "JavaScript": [
        re.compile(r'''import\s+.*?\s+from\s+['"](\..*?)['"]'''),
        re.compile(r'''import\s+['"](\..*?)['"]'''),
        re.compile(r'''require\(\s*['"](\..*?)['"]\s*\)'''),
        re.compile(r'''import\(\s*['"](\..*?)['"]\s*\)'''),
    ],
    "TypeScript": [
        re.compile(r'''import\s+.*?\s+from\s+['"](\..*?)['"]'''),
        re.compile(r'''import\s+['"](\..*?)['"]'''),
        re.compile(r'''require\(\s*['"](\..*?)['"]\s*\)'''),
        re.compile(r'''import\(\s*['"](\..*?)['"]\s*\)'''),
    ],
    "Python": [
        re.compile(r'''^\s*from\s+(\S+)\s+import''', re.MULTILINE),
        re.compile(r'''^\s*import\s+(\S+)''', re.MULTILINE),
    ],
    "Go": [
        re.compile(r'''"(\S+)"'''),
    ],
    "Java": [
        re.compile(r'''^\s*import\s+(\S+)\s*;''', re.MULTILINE),
    ],
    "Rust": [
        re.compile(r'''^\s*use\s+(\S+)\s*;''', re.MULTILINE),
        re.compile(r'''^\s*mod\s+(\S+)\s*;''', re.MULTILINE),
    ],
}

# Languages that share JS patterns
for lang in ("Vue", "Svelte", "MDX"):
    IMPORT_PATTERNS[lang] = IMPORT_PATTERNS["JavaScript"]


def resolve_import(from_file: str, import_path: str, root: Path, language: str) -> str | None:
    """Resolve a relative import to a file path relative to root."""
    if language in ("JavaScript", "TypeScript", "Vue", "Svelte", "MDX"):
        from_dir = Path(from_file).parent
        candidate = (root / from_dir / import_path).resolve()
        # Try exact match then with extensions
        extensions = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".vue", ".svelte", ""]
        for ext in extensions:
            for try_path in [candidate.with_suffix(ext), candidate / f"index{ext}"]:
                if try_path.is_file():
                    try:
                        return str(try_path.relative_to(root))
                    except ValueError:
                        return None
    return None


def parse_imports(filepath: str, language: str, root: Path) -> list[dict]:
    """Parse import statements from a file and return dependency edges."""
    patterns = IMPORT_PATTERNS.get(language, [])
    if not patterns:
        return []

    try:
        with open(root / filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except OSError:
        return []

    deps = []
    for pattern in patterns:
        for match in pattern.finditer(content):
            import_path = match.group(1)
            resolved = resolve_import(filepath, import_path, root, language)
            if resolved:
                deps.append({
                    "from": filepath,
                    "to": resolved,
                    "type": "import",
                    "raw": import_path,
                })
    return deps


def collect_dependencies(tree: dict, root: Path) -> list[dict]:
    """Walk the tree and collect all import dependencies."""
    all_deps = []

    def _walk(node: dict):
        if node["type"] == "file" and node.get("language"):
            all_deps.extend(parse_imports(node["path"], node["language"], root))
        for child in node.get("children", []):
            _walk(child)

    _walk(tree)
    return all_deps
```

**Step 2: Run to verify import parsing works on a JS/TS project**

Run: `python scripts/analyze.py /path/to/js-project 2>&1 | python -m json.tool | grep -A3 '"dependencies"'`
Expected: Array of dependency objects with from/to paths

**Step 3: Commit**

```bash
git add scripts/analyze.py
git commit -m "feat: add multi-language import dependency parsing"
```

---

### Task 3: Add project metadata detection and main output assembly

**Files:**
- Modify: `scripts/analyze.py`

**Step 1: Add metadata detection and main function**

Append to `analyze.py`:

```python
# --- Project Metadata Detection ---

def detect_config(root: Path) -> dict:
    """Detect project configuration from marker files."""
    config = {
        "packageManager": None,
        "framework": None,
        "hasTests": False,
        "hasDocker": False,
    }

    if (root / "package.json").exists():
        config["packageManager"] = "npm"
        if (root / "yarn.lock").exists():
            config["packageManager"] = "yarn"
        elif (root / "pnpm-lock.yaml").exists():
            config["packageManager"] = "pnpm"
        elif (root / "bun.lockb").exists():
            config["packageManager"] = "bun"
        # Framework detection
        try:
            pkg = json.loads((root / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                config["framework"] = "Next.js"
            elif "nuxt" in deps:
                config["framework"] = "Nuxt"
            elif "svelte" in deps or "@sveltejs/kit" in deps:
                config["framework"] = "SvelteKit"
            elif "react" in deps:
                config["framework"] = "React"
            elif "vue" in deps:
                config["framework"] = "Vue"
            elif "express" in deps:
                config["framework"] = "Express"
            elif "fastify" in deps:
                config["framework"] = "Fastify"
        except (json.JSONDecodeError, OSError):
            pass

    elif (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        config["packageManager"] = "pip"
        # Check for frameworks
        for f in ["pyproject.toml", "requirements.txt"]:
            try:
                content = (root / f).read_text()
                if "django" in content.lower():
                    config["framework"] = "Django"
                elif "fastapi" in content.lower():
                    config["framework"] = "FastAPI"
                elif "flask" in content.lower():
                    config["framework"] = "Flask"
            except OSError:
                pass

    elif (root / "go.mod").exists():
        config["packageManager"] = "go"
    elif (root / "Cargo.toml").exists():
        config["packageManager"] = "cargo"

    # Tests
    test_dirs = ["tests", "test", "__tests__", "spec", "specs"]
    config["hasTests"] = any((root / d).is_dir() for d in test_dirs)

    # Docker
    config["hasDocker"] = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()

    return config


def detect_entry_points(root: Path, tree: dict) -> list[str]:
    """Detect likely entry point files."""
    candidates = [
        "src/index.ts", "src/index.js", "src/main.ts", "src/main.js",
        "src/app.ts", "src/app.js", "index.ts", "index.js",
        "main.py", "app.py", "src/main.py", "manage.py",
        "main.go", "cmd/main.go",
        "src/main.rs", "src/lib.rs",
    ]
    found = []
    for c in candidates:
        if (root / c).is_file():
            found.append(c)
    return found


def compute_summary(tree: dict) -> dict:
    """Compute summary statistics from the tree."""
    total_files = 0
    total_dirs = 0
    total_lines = 0
    languages = {}

    def _walk(node: dict):
        nonlocal total_files, total_dirs, total_lines
        if node["type"] == "dir":
            total_dirs += 1
            for child in node.get("children", []):
                _walk(child)
        else:
            total_files += 1
            lines = node.get("lines", 0)
            total_lines += lines
            lang = node.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

    _walk(tree)
    return {
        "totalFiles": total_files,
        "totalDirs": total_dirs,
        "languages": dict(sorted(languages.items(), key=lambda x: -x[1])),
        "totalLines": total_lines,
    }


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
        "entryPoints": detect_entry_points(root, tree),
        "config": detect_config(root),
    }

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
```

**Step 2: Run full analysis on a real project**

Run: `python scripts/analyze.py /path/to/project --output /tmp/test-data.json && python -c "import json; d=json.load(open('/tmp/test-data.json')); print(f'Files: {d[\"summary\"][\"totalFiles\"]}, Deps: {len(d[\"dependencies\"])}, Entry: {d[\"entryPoints\"]}')" `
Expected: Summary of files, dependencies count, and detected entry points

**Step 3: Commit**

```bash
git add scripts/analyze.py
git commit -m "feat: add project metadata detection and main output assembly"
```

---

### Task 4: Create HTML visualization template

**Files:**
- Create: `assets/template.html`

**Step 1: Write the HTML template**

This is a single-file HTML with D3.js and Mermaid.js via CDN. It contains a `__PROJECT_DATA__` placeholder that gets replaced with actual JSON data. The template includes:

- Sidebar with project summary
- 4 tab buttons (Structure, Dependencies, Flow, Architecture)
- Main visualization canvas
- Detail panel
- Dark/light mode toggle
- D3.js treemap for Structure tab
- D3.js force graph for Dependencies tab
- Mermaid.js rendering for Flow tab
- D3.js custom layer diagram for Architecture tab
- CSS for responsive layout and both color themes

The template file will be ~800 lines of HTML/CSS/JS.

Key structure:
```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>System Visualizer - __PROJECT_NAME__</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>/* CSS variables for dark/light, layout grid, tab styles */</style>
</head>
<body>
    <header><!-- project name + theme toggle --></header>
    <main>
        <aside><!-- summary sidebar --></aside>
        <section>
            <nav><!-- tab buttons --></nav>
            <div id="viz-canvas"><!-- D3/Mermaid renders here --></div>
            <div id="detail-panel"><!-- selected item info --></div>
        </section>
    </main>
    <script>
        const PROJECT_DATA = __PROJECT_DATA__;
        const ARCHITECTURE = __ARCHITECTURE_DATA__;
        // Tab switching, D3 treemap, force graph, mermaid, layer diagram
    </script>
</body>
</html>
```

**Step 2: Verify template loads in browser with placeholder data**

Run: `open assets/template.html` (with hardcoded sample data for testing)
Expected: HTML page opens with working layout and tab switching

**Step 3: Commit**

```bash
git add assets/template.html
git commit -m "feat: add interactive HTML visualization template with 4 views"
```

---

### Task 5: Create SKILL.md

**Files:**
- Create: `SKILL.md`

**Step 1: Write the skill instructions**

```markdown
---
name: system-visualizer
description: Visualize system structure and architecture. Auto-analyzes codebase and generates interactive HTML with directory treemap, dependency graph, data flow, and architecture layer views. Use when user says "visualize system", "show structure", "show architecture", "시스템 구조", "시각화", "아키텍처 보여줘", "구조 분석".
---

# System Visualizer

Analyzes the current project codebase and generates an interactive HTML visualization.

## Execution Flow

### Phase 1: Data Collection
1. Run the analysis script on the current project:
   ```bash
   python {SKILL_DIR}/scripts/analyze.py {PROJECT_ROOT} --output /tmp/sv-project-data.json
   ```
2. Read the output JSON.

### Phase 2: Architecture Inference
Analyze the project-data.json and produce architecture JSON with:

**Layer Classification** - Assign each top-level directory to a layer:
- Presentation: UI, pages, components, styles, views, templates
- Application: services, hooks, utils, helpers, middleware, controllers
- Data: db, models, repositories, api clients, schemas, migrations
- Infrastructure: config, docker, ci/cd, scripts, deploy

**Data Flow Inference** - From entry points, trace import chains to identify 3-5 major flows. Name each flow by its purpose.

**Core Components** - Identify:
- Hub files: files imported by 5+ other files
- Circular dependencies: A→B→A chains
- Orphan files: files with no imports and not imported by others

Output format:
```json
{
  "layers": [
    {"name": "Presentation", "description": "...", "items": ["path1/", "path2/"]},
    ...
  ],
  "flows": [
    {"name": "Flow Name", "steps": [{"component": "Name", "action": "description"}, ...]},
    ...
  ],
  "insights": {
    "hubs": [{"path": "...", "importedBy": 12}],
    "circular": [["a.ts", "b.ts"]],
    "orphans": ["path/file.ts"]
  }
}
```

### Phase 3: HTML Generation
1. Read the template: `{SKILL_DIR}/assets/template.html`
2. Replace `__PROJECT_DATA__` with the project-data.json content
3. Replace `__ARCHITECTURE_DATA__` with the architecture JSON
4. Replace `__PROJECT_NAME__` with the project name
5. Write to `/tmp/system-visualizer-{projectName}.html`
6. Open in browser:
   ```bash
   open /tmp/system-visualizer-{projectName}.html
   ```

## Notes
- The analysis script uses only Python stdlib (no pip install needed)
- Excludes node_modules, .git, dist, build, vendor, __pycache__ by default
- Supports JS/TS, Python, Go, Java, Rust import parsing
- HTML uses D3.js v7 and Mermaid.js via CDN (requires internet)
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat: add SKILL.md with execution instructions"
```

---

### Task 6: Create language patterns reference

**Files:**
- Create: `references/language-patterns.md`

**Step 1: Write the reference document**

A concise reference of import patterns per language that Claude can consult when analyzing ambiguous imports. Covers JS/TS (ESM, CJS, dynamic), Python (relative, absolute, __init__), Go (standard, third-party), Java (package conventions), Rust (mod, use, crate).

**Step 2: Commit**

```bash
git add references/language-patterns.md
git commit -m "docs: add language import patterns reference"
```

---

### Task 7: Create symlink and end-to-end test

**Files:**
- No new files

**Step 1: Create symlink for Claude Code access**

```bash
ln -sf "$(pwd)" ~/.claude/skills/system-visualizer
```

**Step 2: Run end-to-end test on this skill repository itself**

```bash
python scripts/analyze.py . --output /tmp/sv-test.json
```

Verify JSON has valid structure, dependencies, and metadata.

**Step 3: Test the skill by invoking /system-visualizer in Claude Code**

Expected: Claude runs analyze.py, infers architecture, generates HTML, opens in browser.

**Step 4: Commit**

```bash
git commit -m "chore: verify end-to-end skill execution"
```
