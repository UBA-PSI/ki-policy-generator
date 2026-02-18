# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KI-Policy-Generator is an interactive browser-based tool for creating AI usage policies for university courses. It is a purely client-side application (no backend, no build system, no npm). The project is bilingual (German/English) and maintained by Otto-Friedrich-Universität Bamberg.

Live: https://web.psi.uni-bamberg.de/ki-policy-generator/v3/

## Development

There is no build step, no package.json, no bundler. The app runs directly in the browser.

```bash
# Serve locally
python3 -m http.server 8000
# Open http://localhost:8000
```

YAML files must be served over HTTP (not file://), so a local server is required.

## Architecture

**Single-file SPA** with three views managed via CSS classes (`active-view`):
1. **Welcome View** (`#welcome-view`) – landing page
2. **Editor View** (`#editor-view`) – policy builder
3. **Result View** (`#result-view`) – generated policy output

### Key Files

- `index.html` – contains all HTML, CSS, and core JavaScript (~3000 lines)
- `policy-loader.js` – loads and parses YAML policy data, renders categories/items into the DOM
- `data/policy-data.yaml` / `data/policy-data-en.yaml` – hierarchical policy content (categories → subcategories → items)
- `lib/js-yaml.min.js` – YAML parser (uses SAFE_SCHEMA)
- `pako.min.js` – compression for export/import of configurations

### Global State

App state lives in window-level variables:
- `selectedItems` – array of user-selected policy items
- `originalPolicyItems` – map of original text for reverting edits
- `currentLanguage` – active language (`de`/`en`)
- `documentIntro` – intro text for generated policy

### YAML Data Structure

```yaml
metadata:
  title, subtitle, default_document_title, default_document_intro
categories:
  - id, title
    subcategories:
      - id, title, guidance
        items:
          - id, tags: [{label, type}], text (Markdown)
```

### Security

- `escapeHTML()` is called before Markdown parsing to prevent XSS
- CSP meta tag restricts resources to `'self'` (with `'unsafe-inline'` for scripts/styles)
- YAML uses `SAFE_SCHEMA` (no code execution)
- No external network requests except loading local YAML files

## Dual Licensing

- **Code** (HTML, JS): MIT License
- **Content** (policy texts in `data/*.yaml`): CC BY-SA 4.0
- **Fonts**: Apache 2.0
