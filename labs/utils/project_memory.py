import os


class ProjectMemory:
    """项目记忆发现器：自动查找并加载 CLAUDE.md 等项目记忆文件。"""

    MEMORY_FILES = ["CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md"]

    def discover(self, work_dir: str) -> str | None:
        current = os.path.abspath(work_dir)
        discovered = []
        while True:
            for mem_file in self.MEMORY_FILES:
                full_path = os.path.join(current, mem_file)
                if os.path.isfile(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        discovered.append((full_path, content))
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        if not discovered:
            return None
        parts = []
        for path, content in discovered:
            parts.append(f"# 项目记忆: {path}\n{content}")
        return "\n\n".join(parts)

    def build_system_prompt(self, base_prompt: str, work_dir: str) -> str:
        memory = self.discover(work_dir)
        if memory:
            return f"{base_prompt}\n\n---\n\n{memory}"
        return base_prompt
