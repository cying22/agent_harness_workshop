import subprocess
import os
from abc import ABC, abstractmethod

class Tool(ABC):
    """所有工具的基类。对应 Claude Code 中 Tool.ts 的统一接口。"""

    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def input_schema(self) -> dict: pass

    def validate(self, tool_input: dict) -> str | None:
        """
        校验工具输入参数。
        返回 None 表示通过，返回 str 表示错误信息。
        """
        schema = self.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # 1. 检查缺失的必填字段
        missing = [k for k in required if k not in tool_input]
        if missing:
            return f"缺少必填参数: {', '.join(missing)}"

        # 2. 检查未知字段
        if properties:
            unknown = [k for k in tool_input if k not in properties]
            if unknown:
                return f"未知参数: {', '.join(unknown)}"

        # 3. 检查类型（基础类型映射）
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        errors = []
        for key, value in tool_input.items():
            prop = properties.get(key)
            if prop and "type" in prop:
                expected_type = type_map.get(prop["type"])
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"参数 '{key}' 类型错误: 期望 {prop['type']}, 实际为 {type(value).__name__}"
                    )

        # 4. 检查 enum 约束
        for key, value in tool_input.items():
            prop = properties.get(key)
            if prop and "enum" in prop and value not in prop["enum"]:
                errors.append(
                    f"参数 '{key}' 值无效: '{value}' 不在允许值 {prop['enum']} 中"
                )

        if errors:
            return "; ".join(errors)

        return None  # ✅ 校验通过

    @abstractmethod
    def execute(self, tool_input: dict) -> str: pass

    def to_api_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ReadFileTool(Tool):
    @property
    def name(self): return "read_file"
    @property
    def description(self): return "读取指定路径的文件内容"
    @property
    def input_schema(self):
        return {"type": "object", "properties": {"path": {"type": "string", "description": "文件路径"}}, "required": ["path"]}
    def execute(self, tool_input):
        try:
            with open(tool_input["path"], "r") as f: return f.read() or "(空文件)"
        except Exception as e: return f"错误：{e}"


class WriteFileTool(Tool):
    @property
    def name(self): 
        return "write_file"
    @property
    def description(self): 
        return "Writes a file to the local filesystem.\n\nUsage:\n- This tool will overwrite the existing file if there is one at the provided path.\n- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.\n- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked."
    @property
    def input_schema(self):
        return {"type": "object", "properties": {"file_path": {"type": "string","description": "the absolute path to the file to write (must be absolute, not relative)"},
                                                  "content": {"type": "string","description": "The content to write to the file"}
                                                  },
                                                 "required": ["file_path", "content"]}
    def execute(self, tool_input):
        try:
            os.makedirs(os.path.dirname(tool_input["file_path"]) or ".", exist_ok=True)
            with open(tool_input["file_path"], "w") as f: f.write(tool_input["content"]) 
            return f"已写入 {len(tool_input['content'])} 字符到 {tool_input['file_path']}"
        except Exception as e: return f"错误：{e}"


class EditFileTool(Tool):
    """精确替换文件中的文本片段。对应 Claude Code 的 Edit 工具。"""
    @property
    def name(self): return "edit_file"
    @property
    def description(self):
        return (
            "Performs exact string replacements in files.\n\n"
            "Usage:\n"
            "- The edit will FAIL if `old_string` is not unique in the file. "
            "Either provide a larger string with more surrounding context to make it unique "
            "or use `replace_all` to change every instance of `old_string`.\n"
            "- Use `replace_all` for replacing and renaming strings across the file."
        )
    @property
    def input_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_path":   {"type": "string",  "description": "The absolute path to the file to modify"},
                "old_string":  {"type": "string",  "description": "The text to replace"},
                "new_string":  {"type": "string",  "description": "The text to replace it with (must be different from old_string)"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences of old_string (default false)", "default": False},
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    def execute(self, tool_input):
        file_path   = tool_input["file_path"]
        old_string  = tool_input["old_string"]
        new_string  = tool_input["new_string"]
        replace_all = tool_input.get("replace_all", False)

        if old_string == new_string:
            return "错误：old_string 和 new_string 相同，无需替换"

        try:
            with open(file_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            return f"错误：文件不存在 {file_path}"
        except Exception as e:
            return f"错误：读取文件失败 {e}"

        count = content.count(old_string)
        if count == 0:
            preview = content[:200] + "..." if len(content) > 200 else content
            return f"错误：未找到匹配的文本。文件前 200 字符：\n{preview}"

        if replace_all:
            new_content = content.replace(old_string, new_string)
        else:
            if count > 1:
                return f"错误：找到 {count} 处匹配，请提供更多上下文使匹配唯一，或设置 replace_all=true"
            new_content = content.replace(old_string, new_string, 1)

        try:
            with open(file_path, "w") as f:
                f.write(new_content)
            replaced = count if replace_all else 1
            return f"已替换 {replaced} 处文本（{len(old_string)} → {len(new_string)} 字符）in {file_path}"
        except Exception as e:
            return f"错误：写入文件失败 {e}"


class BashTool(Tool):
    @property
    def name(self): return "bash"
    @property
    def description(self): return "执行一条 bash 命令并返回标准输出和标准错误"
    @property
    def input_schema(self):
        return {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
    def execute(self, tool_input):
        try:
            r = subprocess.run(tool_input["command"], shell=True, capture_output=True, text=True, timeout=30, cwd=os.getcwd())
            output = r.stdout + r.stderr
            return output.strip() if output.strip() else "(无输出)"
        except subprocess.TimeoutExpired: return "错误：命令执行超时（30秒）"
        except Exception as e: return f"错误：{e}"


def clean_cache_control(messages:list):
    """
    清理 messages 中多余的 cache_control，只保留最后一个。
    cache_control 可能出现在：
        1. 消息级别: messages[i]["cache_control"]
        2. content 块级别: messages[i]["content"][j]["cache_control"]（当 content 是 list 时）
    """
    # 第一遍：收集所有 cache_control 的位置 (msg_idx, block_idx or None)
    positions = []
    for i, msg in enumerate(messages):
        # 检查消息级别的 cache_control
        if isinstance(msg, dict) and "cache_control" in msg:
            positions.append((i, None))
        # 检查 content 块级别
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list):
            for j, block in enumerate(content):
                if isinstance(block, dict) and "cache_control" in block:
                    positions.append((i, j))
    # 如果不超过1个，无需清理
    if len(positions) <= 1:
        return messages
    # 第二遍：只保留最后一个，删除其余的
    keep = positions[-1]
    for pos in positions[:-1]:
        msg_idx, block_idx = pos
        if block_idx is None:
            # 消息级别
            del messages[msg_idx]["cache_control"]
        else:
            # content 块级别
            del messages[msg_idx]["content"][block_idx]["cache_control"]
    return messages