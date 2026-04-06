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
    def validate(self, tool_input: dict) -> bool:
        return all(k in tool_input for k in self.input_schema.get("required", []))
    @abstractmethod
    def execute(self, tool_input: dict) -> str: pass
    def to_api_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


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
    def name(self): return "write_file"
    @property
    def description(self): return "将内容写入指定路径的文件。如果文件已存在会被覆盖。"
    @property
    def input_schema(self):
        return {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}
    def execute(self, tool_input):
        try:
            os.makedirs(os.path.dirname(tool_input["path"]) or ".", exist_ok=True)
            with open(tool_input["path"], "w") as f: f.write(tool_input["content"])
            return f"已写入 {len(tool_input['content'])} 字符到 {tool_input['path']}"
        except Exception as e: return f"错误：{e}"


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

