# System Visualizer Skill - Design Document

**Date:** 2026-02-22
**Status:** Approved

## Overview

A Claude Code skill that automatically analyzes a codebase and generates an interactive HTML visualization showing system structure, module dependencies, data flows, and architecture layers.

## Requirements

- **Target**: Codebase auto-analysis + architecture-level visualization
- **Output**: Interactive HTML page (opens in browser)
- **Diagrams**: Directory structure, dependency graph, data flow, architecture layer map
- **Execution**: Auto-scan project, generate HTML, open in browser
- **Tech**: CDN libraries allowed (D3.js, Mermaid.js)
- **Scope**: Language-agnostic (JS/TS, Python, Go, Java, Rust)

## Architecture: Hybrid Approach

```
User invokes skill
        │
        ▼
Phase 1: Data Collection (Python script)
  - Directory tree scan
  - Import/require parsing
  - File metadata collection
  - Output: project-data.json
        │
        ▼
Phase 2: Architecture Inference (Claude)
  - Layer classification
  - Data flow inference
  - Core component identification
  - Output: architecture.json
        │
        ▼
Phase 3: HTML Generation (Claude + Template)
  - Inject data into HTML template
  - D3.js interactive visualizations
  - 4 view tabs
  - Auto-open in browser
```

## Skill File Structure

```
system-visualizer/
├── SKILL.md                    # Skill instructions
├── scripts/
│   └── analyze.py              # Codebase analysis script
├── assets/
│   └── template.html           # HTML visualization template
└── references/
    └── language-patterns.md    # Language import patterns reference
```

## Phase 1: Python Analysis Script (analyze.py)

### Input
- Project root path (argument)
- Output file path (--output flag)

### Output Schema (project-data.json)

```json
{
  "projectName": "string",
  "scanTimestamp": "ISO8601",
  "summary": {
    "totalFiles": "number",
    "totalDirs": "number",
    "languages": {"language": "fileCount"},
    "totalLines": "number"
  },
  "tree": [
    {
      "path": "string",
      "type": "dir|file",
      "size": "number (bytes)",
      "language": "string",
      "lines": "number",
      "children": ["recursive"]
    }
  ],
  "dependencies": [
    {
      "from": "filePath",
      "to": "filePath",
      "type": "import|require|use"
    }
  ],
  "entryPoints": ["filePaths"],
  "config": {
    "packageManager": "string|null",
    "framework": "string|null",
    "hasTests": "boolean",
    "hasDocker": "boolean"
  }
}
```

### Import Pattern Support

| Language | Patterns |
|----------|----------|
| JS/TS | `import ... from '...'`, `require('...')` |
| Python | `import ...`, `from ... import ...` |
| Go | `import "..."`, `import (...)` |
| Java | `import ...;` |
| Rust | `use ...;`, `mod ...;` |

### Default Excludes
`node_modules`, `__pycache__`, `.git`, `dist`, `build`, `vendor`, `.venv`, `target`, `.next`, `.nuxt`

### Execution
```bash
python analyze.py /path/to/project --output project-data.json
```

## Phase 2: Claude Architecture Inference

Claude reads project-data.json and produces:

### Layer Classification
Assigns each directory/file to an architecture layer:
- **Presentation**: UI components, pages, routing, styles
- **Application**: Business logic, services, hooks, utils
- **Data**: Database access, models, API clients, repositories
- **Infrastructure**: Config, build, deploy, CI/CD

### Data Flow Inference
Traces dependency chains from entry points to identify major data flows:
- User-facing flows (request → response)
- Background processes
- Event/message flows

### Core Component Identification
- Hub files (high dependency count)
- Circular dependency warnings
- Orphan files (no imports/exports)

## Phase 3: HTML Visualization

### Layout
```
┌──────────────────────────────────────────────────┐
│  System Visualizer - [Project]     [Dark/Light]  │
├──────┬───────────────────────────────────────────┤
│      │  [Structure] [Dependencies] [Flow] [Arch] │
│ Side │  ┌───────────────────────────────────┐    │
│ bar  │  │                                   │    │
│      │  │   Active Tab Visualization        │    │
│ Sum- │  │   (Interactive Diagram)            │    │
│ mary │  │                                   │    │
│      │  └───────────────────────────────────┘    │
│      │  ┌───────────────────────────────────┐    │
│      │  │ Detail Panel (selected item info)  │    │
│      │  └───────────────────────────────────┘    │
└──────┴───────────────────────────────────────────┘
```

### 4 Tabs

| Tab | Visualization | Library |
|-----|---------------|---------|
| Structure | Treemap (file size proportional) + folder drill-down | D3.js Treemap |
| Dependencies | Force-directed graph (nodes=files, edges=imports) | D3.js Force |
| Flow | Sequence diagrams (per major flow) | Mermaid.js |
| Architecture | Horizontal layer diagram (components in layers) | D3.js Custom |

### Interactions
- Node click → detail panel shows file info, import list
- Drag & zoom support
- Search/filter (filename, language)
- Dark/light mode toggle

### CDN Dependencies
- D3.js v7 (treemap, force graph, custom diagrams)
- Mermaid.js (sequence diagrams)
