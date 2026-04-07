import os
import platform
from pathlib import Path
from datetime import datetime


class ProjectMemory:
    """项目记忆发现器：自动查找并加载 CLAUDE.md 等项目记忆文件。"""

    # 支持的记忆文件名
    MEMORY_FILES = ["CLAUDE.md", ".claude/CLAUDE.md"]

    def discover(self, work_dir: str) -> str | None:
        """在工作目录中发现项目记忆文件。

        搜索顺序：
        1. 当前目录下的 MEMORY_FILES
        2. 父目录递归向上（最多到根目录）

        返回:
            找到的记忆文件内容，或 None
        """
        current = os.path.abspath(work_dir)
        discovered = []

        # 从当前目录向上搜索
        while True:
            for mem_file in self.MEMORY_FILES:
                full_path = os.path.join(current, mem_file)
                if os.path.isfile(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        discovered.append((full_path, content))
                        print(f"  发现记忆文件: {full_path}")

            # 向上一层
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        if not discovered:
            print("  未发现任何项目记忆文件")
            return None

        # 拼接所有发现的记忆
        parts = []
        for path, content in discovered:
            parts.append(f"# 项目记忆: {path}\n{content}")
        return "\n\n".join(parts)

    def _collect_env_meta(self, work_dir: str) -> str:
        """收集当前环境元信息。"""
        abs_dir = os.path.abspath(work_dir)

        # 操作系统信息
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

        # 当前时间
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z").strip()
        timezone = datetime.now().astimezone().tzname()

        # 工作目录下的文件列表（只扫描一层，避免目录过大）
        try:
            entries = sorted(os.listdir(abs_dir))
            file_list = []
            dir_count = 0
            file_count = 0
            for entry in entries:
                full = os.path.join(abs_dir, entry)
                if os.path.isdir(full):
                    file_list.append(f"  📁 {entry}/")
                    dir_count += 1
                else:
                    size = os.path.getsize(full)
                    file_list.append(f"  📄 {entry} ({_human_size(size)})")
                    file_count += 1

            # 如果文件太多，截断并提示
            MAX_DISPLAY = 50
            if len(file_list) > MAX_DISPLAY:
                file_list = file_list[:MAX_DISPLAY]
                file_list.append(f"  ... 共 {dir_count} 个目录, {file_count} 个文件 (仅显示前 {MAX_DISPLAY} 项)")

            files_str = "\n".join(file_list) if file_list else "  (空目录)"
            summary = f"共 {dir_count} 个目录, {file_count} 个文件"
        except PermissionError:
            files_str = "  (无权限读取)"
            summary = "无权限"

        meta = f"""# 环境信息
- 操作系统: {os_info}
- 当前时间: {now} ({timezone})
- 工作目录: {abs_dir}
- Shell: {os.environ.get('SHELL', os.environ.get('COMSPEC', 'unknown'))}
- Python: {platform.python_version()}

## 工作目录文件 ({summary})
{files_str}"""

        return meta

    def build_system_prompt(self, base_prompt: str, work_dir: str) -> str:
        """将项目记忆和环境元信息注入到基础 system prompt 中。

        参数:
            base_prompt: 基础系统提示词
            work_dir: 工作目录路径

        返回:
            注入了环境信息和项目记忆的完整 system prompt
        """
        print(f"\n扫描目录: {work_dir}")

        parts = [base_prompt]

        # 注入环境元信息
        env_meta = self._collect_env_meta(work_dir)
        parts.append(env_meta)
        print(f"  环境信息已注入")

        # 注入项目记忆
        memory = self.discover(work_dir)
        if memory:
            parts.append(memory)
            print(f"  项目记忆已注入 system prompt")
        else:
            print(f"  无项目记忆，使用基础 prompt")

        full_prompt = "\n\n---\n\n".join(parts)
        return full_prompt


def _human_size(size_bytes: int) -> str:
    """将字节数转为人类可读格式"""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f}{unit}" if unit == "B" else f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"
