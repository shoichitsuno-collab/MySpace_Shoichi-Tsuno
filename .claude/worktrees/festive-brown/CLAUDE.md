# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains two separate tools:

1. **タスク管理ツール** (`index.html` + `api/addTask.js`): A browser-based daily task manager with localStorage persistence and Notion integration, deployed on Vercel.
2. **PowerPoint Generator** (`slide_generator_pptx.py` + `project_slides.md`): A Python-based slide generation tool using the `slide-usual-ppt` Claude Code skill.

## Running the Task Manager

No build step required. Open `index.html` directly in a browser for local use.

For the Notion integration to work, the app must be served via Vercel (or another serverless platform) with these environment variables set:
- `NOTION_TOKEN` — Notion integration token
- `NOTION_DATABASE_ID` — Target Notion database ID

The API endpoint `api/addTask.js` is a Vercel serverless function (ES module with default export handler).

## PowerPoint Generation

The `slide-usual-ppt` skill converts Markdown slide files into `.pptx` files.

**Slide Markdown format** (`project_slides.md` is the example):
- Slides separated by `---`
- Layout specified with HTML comment: `<!-- layout: layout_name -->`
- Section dividers: `# Section Title` (no layout comment)
- Title `##`, key message `###`, content as bullet points or columns

**Available layouts**: `title`, `section`, `toc`, `bullet_points`, `numbered_list`, `two_column`, `three_column`, `four_column`, `metrics`, `quote`, `faq`, `comparison_table`, `image_with_text`, `chart`, `cta`

**Run the generator directly:**
```bash
python slide_generator_pptx.py \
  --markdown-file project_slides.md \
  --config ~/.claude/skills/slide-usual-ppt/config.json \
  --title "スライドタイトル" \
  --output-dir .
```

Skill config and references are at `~/.claude/skills/slide-usual-ppt/`.

## Architecture

- `index.html`: Self-contained SPA — all CSS and JS are inline. Tasks stored in `localStorage` as JSON array with `{ id, text, completed }`.
- `api/addTask.js`: Vercel serverless function. POSTs to Notion API `v1/pages`, creating a page in the configured database. The `database_id` has hyphens stripped before use.
- `slide_generator_pptx.py`: Python script (lives in repo root but mirrors the skill's script). Parses the custom Markdown format and generates `.pptx` via `python-pptx`.
