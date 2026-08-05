---
name: markdown-source-images
description: Organize repository Markdown image assets under a top-level source/ directory, with each .md file's local images stored below its matching source path, all Markdown image links rewritten and validated, and emptied legacy attachment trees such as image/xxx removed. Use after adding or editing Markdown documents, importing notes from Obsidian/Typora, moving images, or when asked to clean, verify, or enforce this repository's Markdown image structure.
---

# Markdown Source Images

## Purpose

Maintain this repository's image layout:

- All local image files live under top-level `source/`.
- Images used by `path/to/doc.md` live under `source/path/to/doc/`.
- Markdown links point from the `.md` file to that `source/...` asset using standard Markdown image syntax.
- Obsidian wiki image embeds and editor-local absolute paths are treated as problems to resolve.
- Empty legacy attachment trees such as `image/xxx` are removed after their images are migrated.

## Standard Workflow

1. From the repository root, run:

```bash
python3 .codex/skills/markdown-source-images/scripts/organize_markdown_images.py
```

2. Review the summary. Confirm that empty legacy attachment trees were removed. It should report zero broken links, zero images outside `source/`, and zero unreferenced images unless the user explicitly wants orphan images preserved.

3. If the user only asks for inspection, run:

```bash
python3 .codex/skills/markdown-source-images/scripts/organize_markdown_images.py --check
```

4. If the user wants to preview changes before editing:

```bash
python3 .codex/skills/markdown-source-images/scripts/organize_markdown_images.py --dry-run
```

## Behavior

- Move local images referenced by Markdown into `source/<md-relative-path-without-extension>/`.
- Rewrite Markdown image links to the moved target using relative paths from the Markdown file.
- Encode spaces in Markdown links as `%20`.
- Preserve alt text and optional Markdown link titles.
- Do not modify remote image URLs such as `https://...`.
- Report absolute local paths, missing files, wiki embeds, unreferenced images, and image files outside `source/`.
- After moving images, remove an entire legacy attachment tree when it contains no files. Recognize names such as `image`, `images`, `图片和附件`, `assets`, and `attachments`; this must remove empty structures such as `image/xxx`, not leave their empty subdirectories behind.

## Manual Rules

When editing manually, follow the same destination rule:

```text
some/folder/page.md
source/some/folder/page/<image-file>
```

The Markdown link from `some/folder/page.md` should be:

```markdown
![description](../../source/some/folder/page/image.png)
```

Prefer running the script after manual edits.
