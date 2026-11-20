"""
Anthropic Agent Skills standard implementation for agentic-discovery.
Discovers and loads SKILL.md definitions from `skills/`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Optional


ROOT_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT_DIR / "skills"


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    body: str
    tools: list[str] = field(default_factory=list)
    version: str = "1.0.0"


class SkillRegistry:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or SKILLS_DIR
        self._skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        self._skills.clear()
        if not self.root.exists():
            return
        for skill_dir in self.root.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    skill = self._parse_skill(skill_md)
                    if skill:
                        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def _parse_skill(self, path: Path) -> Optional[Skill]:
        content = path.read_text(encoding="utf-8")
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            return None

        fm_text = frontmatter_match.group(1)
        body = frontmatter_match.group(2).strip()

        name = path.parent.name
        desc = ""
        tools = []
        version = "1.0.0"

        for line in fm_text.splitlines():
            line = line.strip()
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("version:"):
                version = line.split(":", 1)[1].strip().strip('"\'')
            elif line.startswith("tools:"):
                tools_part = line.split(":", 1)[1].strip()
                if tools_part.startswith("[") and tools_part.endswith("]"):
                    tools = [t.strip().strip('"\'') for t in tools_part[1:-1].split(",") if t.strip()]

        return Skill(name=name, description=desc, path=path, body=body, tools=tools, version=version)
