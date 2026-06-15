"""Load the personal knowledge base (JSON + Markdown) into searchable chunks.

The whole product rests on this layer: the quality of the structured content
matters more than the sophistication of the model. Everything an answer can say
must trace back to one of these documents.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Chunk:
    source_id: str
    source_title: str
    source_kind: str
    text: str


@dataclass
class Document:
    id: str
    title: str
    kind: str
    text: str
    chunks: list[Chunk] = field(default_factory=list)


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Split a Markdown file into (frontmatter dict, body)."""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].strip()
    return {}, raw.strip()


def _split_markdown_sections(body: str) -> list[str]:
    """Chunk a Markdown body by `##` headings, keeping each heading with its text."""
    sections: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]


def _load_bio(content_dir: Path) -> Document | None:
    path = content_dir / "bio.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"Name: {data.get('name', '')}",
        f"Title: {data.get('title', '')}",
        f"Location: {data.get('location', '')}",
        f"Summary: {data.get('summary', '')}",
        f"Target roles: {', '.join(data.get('target_roles', []))}",
        f"Strengths: {', '.join(data.get('strengths', []))}",
        f"Languages: {', '.join(data.get('languages', []))}",
    ]
    text = "\n".join(lines)
    return Document(id="bio", title="Bio", kind="bio", text=text)


def _load_experience(content_dir: Path) -> list[Document]:
    path = content_dir / "experience.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    docs: list[Document] = []
    for entry in data:
        company = entry.get("company", "")
        role = entry.get("role", "")
        title = f"{role} — {company}".strip(" —")
        parts = [
            f"Company: {company}",
            f"Role: {role}",
            f"Period: {entry.get('period', '')}",
            f"Location: {entry.get('location', '')}",
            f"Context: {entry.get('context', '')}",
        ]
        if entry.get("actions"):
            parts.append("What I did:\n- " + "\n- ".join(entry["actions"]))
        if entry.get("impact"):
            parts.append("Impact:\n- " + "\n- ".join(entry["impact"]))
        if entry.get("tech"):
            parts.append("Tech: " + ", ".join(entry["tech"]))
        docs.append(
            Document(
                id=f"experience-{_slugify(company)}",
                title=title,
                kind="experience",
                text="\n".join(parts),
            )
        )
    return docs


def _load_skills(content_dir: Path) -> Document | None:
    path = content_dir / "skills.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    parts = [f"{group.replace('_', ' ').title()}: {', '.join(items)}" for group, items in data.items()]
    return Document(id="skills", title="Skills", kind="skills", text="\n".join(parts))


def _load_faq(content_dir: Path) -> list[Document]:
    path = content_dir / "faq.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    docs: list[Document] = []
    for i, entry in enumerate(data):
        q = entry.get("question", "")
        a = entry.get("answer", "")
        docs.append(
            Document(
                id=f"faq-{i + 1}",
                title=f"FAQ: {q}",
                kind="faq",
                text=f"Q: {q}\nA: {a}",
            )
        )
    return docs


def _load_markdown_dir(content_dir: Path, subdir: str, kind: str) -> list[Document]:
    folder = content_dir / subdir
    if not folder.exists():
        return []
    docs: list[Document] = []
    for path in sorted(folder.glob("*.md")):
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        slug = meta.get("slug") or path.stem
        title = meta.get("title") or path.stem
        header_bits = []
        if meta.get("stack"):
            header_bits.append("Stack: " + ", ".join(meta["stack"]))
        if meta.get("tags"):
            header_bits.append("Tags: " + ", ".join(meta["tags"]))
        full = (("\n".join(header_bits) + "\n\n") if header_bits else "") + body
        doc = Document(id=slug, title=title, kind=kind, text=full)
        for section in _split_markdown_sections(body):
            doc.chunks.append(
                Chunk(source_id=slug, source_title=title, source_kind=kind, text=section)
            )
        docs.append(doc)
    return docs


def load_documents(content_dir: str | Path) -> list[Document]:
    content_dir = Path(content_dir)
    docs: list[Document] = []

    if bio := _load_bio(content_dir):
        docs.append(bio)
    docs.extend(_load_experience(content_dir))
    if skills := _load_skills(content_dir):
        docs.append(skills)
    docs.extend(_load_faq(content_dir))
    docs.extend(_load_markdown_dir(content_dir, "projects", "project"))
    docs.extend(_load_markdown_dir(content_dir, "roles", "role"))

    # Ensure every document has at least one chunk (its whole body).
    for doc in docs:
        if not doc.chunks:
            doc.chunks.append(
                Chunk(
                    source_id=doc.id,
                    source_title=doc.title,
                    source_kind=doc.kind,
                    text=doc.text,
                )
            )
    return docs


def all_chunks(docs: list[Document]) -> list[Chunk]:
    return [chunk for doc in docs for chunk in doc.chunks]
