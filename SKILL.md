---
name: system-visualizer
description: Visualize system structure and architecture. Auto-analyzes codebase and generates interactive HTML with directory treemap, dependency graph, data flow, and architecture layer views. Use when user says "visualize system", "show structure", "show architecture", "시스템 구조", "시각화", "아키텍처 보여줘", "구조 분석", "system overview", "codebase map".
version: 1.0.0
---

# System Visualizer

Analyzes the current project codebase and generates an interactive HTML visualization with 4 views:
1. **Directory structure treemap** - file sizes and composition at a glance
2. **Dependency graph** - import relationships between modules
3. **Data flow diagrams** - how data moves through the system
4. **Architecture layer map** - logical grouping into Presentation, Application, Data, and Infrastructure layers

## Execution Flow

### Phase 1: Data Collection

Run the analysis script to scan the project and collect structural data:

```bash
python3 {SKILL_DIR}/scripts/analyze.py {PROJECT_ROOT} --output /tmp/sv-project-data.json
```

Where:
- `{SKILL_DIR}` is this skill's directory (the folder containing this SKILL.md)
- `{PROJECT_ROOT}` is the user's current working directory

After the script completes, read `/tmp/sv-project-data.json` to understand the project structure. This JSON contains:
- `projectName`: project name (derived from root directory name)
- `scanTimestamp`: ISO 8601 timestamp of when the scan ran
- `summary`: summary statistics (`totalFiles`, `totalDirs`, `languages`, `totalLines`)
- `tree`: nested directory/file structure with sizes and languages
- `dependencies`: import relationships between files (JS/TS-family only; see Notes)
- `entryPoints`: detected entry-point files (`main.*`, `index.*`, `app.*`, `server.*`, etc.)
- `config`: detected configuration files

### Phase 2: Architecture Inference

Using the project data from Phase 1, produce an architecture analysis JSON object. Follow these rules precisely.

#### Layer Classification

Assign each significant directory to one of four architecture layers based on naming conventions:

**Presentation** - UI and display concerns:
- Matching names: `pages`, `views`, `components`, `ui`, `templates`, `layouts`, `screens`, `styles`, `css`, `assets/images`

**Application** - Business logic and orchestration:
- Matching names: `services`, `hooks`, `utils`, `helpers`, `middleware`, `controllers`, `handlers`, `use-cases`, `commands`, `interactors`

**Data** - Data access, storage, and external communication:
- Matching names: `db`, `database`, `models`, `entities`, `repositories`, `api`, `clients`, `schemas`, `migrations`, `seeds`, `fixtures`, `stores`, `state`

**Infrastructure** - Build, deploy, and configuration:
- Matching names: `config`, `docker`, `ci`, `cd`, `scripts`, `deploy`, `terraform`, `k8s`, `helm`, `.github`, `Makefile`, `webpack`, `vite`

If a directory does not clearly match any layer by name, classify it based on the contents of its files (e.g., if files mostly contain class definitions with database queries, classify as Data).

#### Data Flow Inference

From the project's entry points (e.g., `main.*`, `index.*`, `app.*`, `server.*`), trace the dependency chain to identify 3-5 major data flows. Each flow must have:

- **name**: a descriptive label (e.g., "User Authentication", "Data Fetching", "API Request Handling")
- **steps**: an ordered array of `{component, action}` objects that follow the actual import chain

Example:
```json
{
  "name": "API Request Handling",
  "steps": [
    {"component": "Router", "action": "Receives HTTP request and matches route"},
    {"component": "Middleware", "action": "Validates authentication token"},
    {"component": "Controller", "action": "Parses input and delegates to service"},
    {"component": "Service", "action": "Executes business logic"},
    {"component": "Repository", "action": "Queries database and returns data"}
  ]
}
```

If the project has fewer than 3 identifiable flows, produce as many as you can identify.

#### Core Component Analysis

Analyze the dependency data to find:

- **Hub files**: files imported by 5 or more other files. Report each with its `path` and `importedBy` count.
- **Circular dependencies**: pairs where file A imports file B AND file B imports file A. Report as arrays of two paths.
- **Orphan files**: files that have a recognized language but neither import nor are imported by any other file. Exclude config files, READMEs, and non-code assets.

#### Output Format

Combine all analysis into a single JSON object with this structure:

```json
{
  "layers": [
    {
      "name": "Presentation",
      "description": "UI components and pages",
      "items": ["src/pages/", "src/components/"]
    },
    {
      "name": "Application",
      "description": "Business logic and services",
      "items": ["src/services/", "src/hooks/"]
    },
    {
      "name": "Data",
      "description": "Data access and models",
      "items": ["src/models/", "src/api/"]
    },
    {
      "name": "Infrastructure",
      "description": "Configuration and deployment",
      "items": ["config/", "docker/"]
    }
  ],
  "flows": [
    {
      "name": "Main Request Flow",
      "steps": [
        {"component": "Router", "action": "Receives HTTP request"},
        {"component": "Controller", "action": "Validates and dispatches"},
        {"component": "Service", "action": "Executes business logic"},
        {"component": "Repository", "action": "Queries database"}
      ]
    }
  ],
  "insights": {
    "hubs": [
      {"path": "src/utils/index.ts", "importedBy": 12}
    ],
    "circular": [
      ["src/a.ts", "src/b.ts"]
    ],
    "orphans": [
      "src/unused.ts"
    ]
  }
}
```

Ensure every layer has at least an empty `items` array. Omit layers only if the project genuinely has zero directories matching that layer.

### Phase 3: HTML Generation

1. Read the HTML template file:
   ```
   {SKILL_DIR}/assets/template.html
   ```

2. Replace the following placeholders in the template:

   | Placeholder | Replacement |
   |---|---|
   | `__PROJECT_NAME__` | The project name from the JSON data (`projectName` field) |
   | `__PROJECT_DATA__` | The full contents of `/tmp/sv-project-data.json` as a JavaScript object literal |
   | `__ARCHITECTURE_DATA__` | The architecture JSON object produced in Phase 2 as a JavaScript object literal |

3. Write the final HTML file to:
   ```
   /tmp/system-visualizer-{projectName}.html
   ```
   Where `{projectName}` is the project name (lowercase, hyphens instead of spaces).

4. Open the generated HTML in the default browser:
   ```bash
   open /tmp/system-visualizer-{projectName}.html
   ```

5. Report to the user:
   - The file path of the generated visualization
   - A brief summary of what was found (number of files, languages detected, identified layers, notable hubs or circular dependencies)

## Notes

- The analysis script uses only Python standard library modules (no pip install required).
- Default excludes: `node_modules`, `.git`, `dist`, `build`, `vendor`, `__pycache__`, `.next`, `.nuxt`, `coverage`, `.cache`, `out`, `target`, `.idea`, `.vscode`.
- Import statements are detected for JavaScript/TypeScript, Python, Go, Java, and Rust, but only JavaScript/TypeScript-family imports (JS, TS, Vue, Svelte, MDX) are resolved to files and drawn in the dependency graph. Python/Go/Java/Rust imports are parsed but not resolved into dependency edges.
- The HTML visualization uses D3.js v7 and Mermaid.js loaded via CDN, so an internet connection is required to view the output.
- For large projects (1000+ files), the treemap and force-directed graph may take a moment to render in the browser.
- If the analysis script fails or produces incomplete data, inform the user and attempt to diagnose the issue before proceeding.
