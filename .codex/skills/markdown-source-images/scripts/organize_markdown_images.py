#!/usr/bin/env python3
"""Organize Markdown image assets into source/<markdown-path>/ folders."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
LEGACY_ATTACHMENT_DIRS = {"图片和附件", "images", "assets", "attachments", "attach", "附件"}
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"']", re.I)
WIKI_IMAGE_RE = re.compile(
    r"!\[\[([^\]]+?\.(?:png|jpe?g|gif|webp|svg))(?:\|[^\]]*)?\]\]", re.I
)


@dataclass
class Rewrite:
    old: str
    new: str
    src: Path
    dest: Path


def split_markdown_target(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if raw.startswith("<") and raw.endswith(">"):
        return raw[1:-1], ""
    parts = re.split(r"\s+(?=[\"'])", raw, maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def is_remote_or_fragment(link: str) -> bool:
    if link.startswith("#"):
        return True
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", link)) and not bool(
        re.match(r"^[a-zA-Z]:[\\/]", link)
    )


def is_absolute_local(link: str) -> bool:
    return Path(link).is_absolute() or bool(re.match(r"^[a-zA-Z]:[\\/]", link))


def encode_link(path: str) -> str:
    return path.replace(" ", "%20")


def md_files(root: Path) -> list[Path]:
    ignored_parts = {".git", ".codex", "source"}
    return sorted(
        p
        for p in root.rglob("*.md")
        if p.is_file() and not any(part in ignored_parts for part in p.relative_to(root).parts)
    )


def image_files(root: Path) -> dict[Path, str]:
    return {
        p.resolve(): p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    }


def collect_rewrites(root: Path) -> tuple[dict[Path, list[Rewrite]], list[str]]:
    rewrites: dict[Path, list[Rewrite]] = {}
    problems: list[str] = []

    for md in md_files(root):
        text = md.read_text(encoding="utf-8", errors="replace")
        for match in MD_IMAGE_RE.finditer(text):
            alt = match.group(1)
            raw = match.group(2)
            link, title = split_markdown_target(raw)
            if is_remote_or_fragment(link):
                continue

            decoded = urllib.parse.unquote(link)
            if is_absolute_local(decoded):
                problems.append(f"{md.relative_to(root)}: absolute local image path: {link}")
                continue

            src = (md.parent / decoded).resolve()
            if not src.exists() or src.suffix.lower() not in IMAGE_EXTS:
                problems.append(f"{md.relative_to(root)}: missing image: {link}")
                continue

            dest_dir = root / "source" / md.relative_to(root).with_suffix("")
            dest = dest_dir / src.name
            rel = os.path.relpath(dest, md.parent.resolve()).replace(os.sep, "/")
            new_link = encode_link(rel)
            if title:
                new_link += " " + title
            new = f"![{alt}]({new_link})"

            if src == dest.resolve() and match.group(0) == new:
                continue
            rewrites.setdefault(md, []).append(Rewrite(match.group(0), new, src, dest))

        for match in WIKI_IMAGE_RE.finditer(text):
            problems.append(f"{md.relative_to(root)}: Obsidian wiki image embed: {match.group(0)}")

        for match in HTML_IMAGE_RE.finditer(text):
            src = match.group(1)
            if not is_remote_or_fragment(src):
                problems.append(f"{md.relative_to(root)}: HTML image src requires manual review: {src}")

    return rewrites, problems


def apply_rewrites(root: Path, rewrites: dict[Path, list[Rewrite]], dry_run: bool) -> None:
    moves: dict[Path, Path] = {}
    for items in rewrites.values():
        for item in items:
            if item.dest in moves and moves[item.dest] != item.src:
                raise RuntimeError(f"destination collision: {moves[item.dest]} and {item.src} -> {item.dest}")
            moves[item.dest] = item.src

    for dest, src in sorted(moves.items(), key=lambda item: item[1].as_posix()):
        if src == dest.resolve():
            continue
        print(f"move: {src.relative_to(root)} -> {dest.relative_to(root)}")
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                raise RuntimeError(f"destination already exists: {dest.relative_to(root)}")
            shutil.move(str(src), str(dest))

    for md, items in rewrites.items():
        print(f"update: {md.relative_to(root)} ({len(items)} links)")
        if dry_run:
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        for item in items:
            text = text.replace(item.old, item.new, 1)
        md.write_text(text, encoding="utf-8")


def remove_empty_legacy_dirs(root: Path, dry_run: bool) -> int:
    removed = 0
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if not path.is_dir() or path.name not in LEGACY_ATTACHMENT_DIRS:
            continue
        try:
            next(path.iterdir())
            continue
        except StopIteration:
            print(f"remove empty attachment dir: {path.relative_to(root)}")
            removed += 1
            if not dry_run:
                path.rmdir()
    return removed


def validate(root: Path) -> tuple[list[str], list[str], list[str]]:
    existing = image_files(root)
    used: set[Path] = set()
    problems: list[str] = []

    for md in md_files(root):
        text = md.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in MD_IMAGE_RE.finditer(line):
                raw = match.group(2)
                link, _ = split_markdown_target(raw)
                if is_remote_or_fragment(link):
                    continue
                decoded = urllib.parse.unquote(link)
                if is_absolute_local(decoded):
                    problems.append(f"{md.relative_to(root)}:{line_no}: absolute local image path: {link}")
                    continue
                target = (md.parent / decoded).resolve()
                if target in existing:
                    used.add(target)
                else:
                    problems.append(f"{md.relative_to(root)}:{line_no}: missing image: {link}")

            for match in WIKI_IMAGE_RE.finditer(line):
                problems.append(f"{md.relative_to(root)}:{line_no}: Obsidian wiki image embed: {match.group(0)}")

    unreferenced = [rel for path, rel in existing.items() if path not in used]
    outside_source = [rel for rel in existing.values() if not rel.startswith("source/")]
    return problems, unreferenced, outside_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repository root, default: current directory")
    parser.add_argument("--check", action="store_true", help="only validate; do not move or rewrite")
    parser.add_argument("--dry-run", action="store_true", help="show planned changes without editing")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        print(f"warning: {root} does not contain .git", file=sys.stderr)

    if not args.check:
        rewrites, preflight_problems = collect_rewrites(root)
        if preflight_problems:
            print("preflight problems:")
            for problem in preflight_problems:
                print(f"  {problem}")
        apply_rewrites(root, rewrites, args.dry_run)
        remove_empty_legacy_dirs(root, args.dry_run)

    problems, unreferenced, outside_source = validate(root)
    print(f"image files: {len(image_files(root))}")
    print(f"broken or nonstandard image refs: {len(problems)}")
    for problem in problems:
        print(f"  {problem}")
    print(f"unreferenced image files: {len(unreferenced)}")
    for rel in unreferenced:
        print(f"  {rel}")
    print(f"images outside source: {len(outside_source)}")
    for rel in outside_source:
        print(f"  {rel}")

    return 1 if problems or unreferenced or outside_source else 0


if __name__ == "__main__":
    raise SystemExit(main())
