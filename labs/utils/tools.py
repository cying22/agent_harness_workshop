from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


_WINDOWS_BASH_READY: bool | None = None


def _workspace_root() -> Path:
    return Path(os.getcwd()).resolve()


def _device_encoding() -> str:
    return os.device_encoding(1) or os.device_encoding(0) or "utf-8"


def _looks_like_windows_root_relative_path(value: str) -> bool:
    return (
        os.name == "nt"
        and value.startswith(("/", "\\"))
        and not value.startswith(("//", "\\\\"))
        and not re.match(r"^[A-Za-z]:[\\/]", value)
    )


def _resolve_local_path(raw_path: str) -> Path:
    path_text = (raw_path or "").strip()
    if not path_text:
        raise ValueError("path is required")

    expanded = os.path.expanduser(path_text)
    if _looks_like_windows_root_relative_path(expanded):
        expanded = expanded.lstrip("/\\")

    path = Path(expanded)
    if not path.is_absolute():
        path = _workspace_root() / path
    return path.resolve()


def _pick_path(tool_input: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _unknown_fields(tool_input: dict[str, Any], allowed: set[str]) -> list[str]:
    return [key for key in tool_input if key not in allowed]


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    encodings = ["utf-8", "utf-8-sig", _device_encoding()]
    if os.name == "nt":
        encodings.append("gb18030")
    encodings.append("latin-1")

    tried: set[str] = set()
    for encoding in encodings:
        if not encoding or encoding in tried:
            continue
        tried.add(encoding)
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _format_directory_listing(path: Path) -> str:
    entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    if not entries:
        return "(empty directory)"

    lines = [f"Directory listing for {path}:"]
    for item in entries:
        prefix = "[DIR]" if item.is_dir() else "[FILE]"
        lines.append(f"{prefix} {item.name}")
    return "\n".join(lines)


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _powershell_token(value: str) -> str:
    if re.match(r"^[A-Za-z0-9_./:\\=-]+$", value):
        return value
    return _powershell_quote(value)


def _split_simple_command(command: str) -> list[str] | None:
    if any(token in command for token in ("&&", "||", "|", ";", "\n", ">>", "<<")):
        return None
    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return None


def _normalize_windows_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    for token in tokens:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
            token = token[1:-1]
        if _looks_like_windows_root_relative_path(token) and ("/" in token[1:] or "." in Path(token).name):
            normalized.append(str(_resolve_local_path(token)))
        else:
            normalized.append(token)
    return normalized


def _translate_windows_command(command: str) -> str:
    tokens = _split_simple_command(command)
    if not tokens:
        return command

    tokens = _normalize_windows_tokens(tokens)
    head = tokens[0].lower()

    if head == "pwd" and len(tokens) == 1:
        return "(Get-Location).Path"

    if head in {"ls", "dir"}:
        target = next((token for token in tokens[1:] if not token.startswith("-")), ".")
        return (
            f"Get-ChildItem -Force -Path {_powershell_quote(target)} | "
            "Select-Object Mode,LastWriteTime,Length,Name | "
            "Format-Table -AutoSize | Out-String -Width 4096"
        )

    if head in {"cat", "type"} and len(tokens) >= 2:
        return f"Get-Content -Path {_powershell_quote(tokens[1])}"

    if head == "head" and len(tokens) >= 2:
        count = "10"
        file_path = tokens[-1]
        if len(tokens) >= 4 and tokens[1] == "-n":
            count = tokens[2]
        elif len(tokens) >= 3 and tokens[1].startswith("-") and tokens[1][1:].isdigit():
            count = tokens[1][1:]
        return f"Get-Content -Path {_powershell_quote(file_path)} -TotalCount {count}"

    if head == "tail" and len(tokens) >= 2:
        count = "10"
        file_path = tokens[-1]
        if len(tokens) >= 4 and tokens[1] == "-n":
            count = tokens[2]
        elif len(tokens) >= 3 and tokens[1].startswith("-") and tokens[1][1:].isdigit():
            count = tokens[1][1:]
        return f"Get-Content -Path {_powershell_quote(file_path)} -Tail {count}"

    if head == "mkdir" and len(tokens) >= 3 and tokens[1] == "-p":
        return f"New-Item -ItemType Directory -Path {_powershell_quote(tokens[2])} -Force | Out-Null"

    if head == "find" and tokens[:4] == ["find", ".", "-maxdepth", "1"] and tokens[-2:] == ["-type", "f"]:
        return "Get-ChildItem -Path . -File | Select-Object -ExpandProperty Name"

    if head == "which" and len(tokens) > 1:
        quoted = ", ".join(_powershell_quote(name) for name in tokens[1:])
        return (
            f"foreach ($name in @({quoted})) "
            "{ $cmd = Get-Command $name -ErrorAction SilentlyContinue; "
            "if ($cmd) { $cmd.Source } else { Write-Output ($name + ' not found') } }"
        )

    if head == "rm" and len(tokens) >= 3 and tokens[1] in {"-f", "-rf", "-fr"}:
        recurse = " -Recurse" if "r" in tokens[1] else ""
        return f"Remove-Item -LiteralPath {_powershell_quote(tokens[2])} -Force{recurse}"

    return " ".join(_powershell_token(token) for token in tokens)


def _prefers_bash_on_windows(command: str) -> bool:
    if not _has_working_windows_bash():
        return False
    lowered = command.lower()
    if any(
        keyword in lowered
        for keyword in (
            "get-childitem",
            "get-content",
            "get-location",
            "select-string",
            "remove-item",
            "new-item",
            "powershell",
        )
    ):
        return False
    return any(
        keyword in lowered
        for keyword in (
            "grep ",
            "find ",
            "head ",
            "tail ",
            "wc ",
            "sed ",
            "awk ",
            "mkdir -p",
            "rm -f",
            "2>/dev/null",
            "/dev/null",
            "&&",
            "||",
        )
    )


def _has_working_windows_bash() -> bool:
    global _WINDOWS_BASH_READY

    if os.name != "nt":
        return False
    if _WINDOWS_BASH_READY is not None:
        return _WINDOWS_BASH_READY

    bash = shutil.which("bash")
    if not bash:
        _WINDOWS_BASH_READY = False
        return False

    try:
        result = subprocess.run(
            [bash, "-lc", "exit 0"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        _WINDOWS_BASH_READY = result.returncode == 0
    except Exception:
        _WINDOWS_BASH_READY = False

    return _WINDOWS_BASH_READY


def _run_shell(command: str) -> subprocess.CompletedProcess[str]:
    common_kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": 30,
        "cwd": str(_workspace_root()),
        "encoding": "utf-8",
        "errors": "replace",
    }

    if os.name != "nt":
        return subprocess.run(command, shell=True, **common_kwargs)

    if _prefers_bash_on_windows(command):
        bash = shutil.which("bash")
        return subprocess.run([bash, "-lc", command], **common_kwargs)

    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if powershell:
        translated = _translate_windows_command(command)
        prolog = (
            "$ErrorActionPreference='Continue'; "
            "[Console]::InputEncoding=[System.Text.Encoding]::UTF8; "
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
            "$OutputEncoding=[System.Text.Encoding]::UTF8; "
        )
        return subprocess.run(
            [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", prolog + translated],
            **common_kwargs,
        )

    return subprocess.run(command, shell=True, **common_kwargs)


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        raise NotImplementedError

    def validate(self, tool_input: dict[str, Any]) -> str | None:
        schema = self.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        missing = [key for key in required if key not in tool_input]
        if missing:
            return f"Missing required fields: {', '.join(missing)}"

        if properties:
            unknown = [key for key in tool_input if key not in properties]
            if unknown:
                return f"Unknown fields: {', '.join(unknown)}"

        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        errors: list[str] = []
        for key, value in tool_input.items():
            prop = properties.get(key)
            if prop and "type" in prop:
                expected_type = type_map.get(prop["type"])
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{key}' has type {type(value).__name__}; expected {prop['type']}"
                    )

        for key, value in tool_input.items():
            prop = properties.get(key)
            if prop and "enum" in prop and value not in prop["enum"]:
                errors.append(f"Field '{key}' must be one of {prop['enum']}")

        if errors:
            return "; ".join(errors)
        return None

    @abstractmethod
    def execute(self, tool_input: dict[str, Any]) -> str:
        raise NotImplementedError

    def to_api_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ReadFileTool(Tool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read a file from the local workspace. Relative paths are resolved from the current "
            "working directory. If the target is a directory, return a one-level directory listing."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file or directory"},
                "file_path": {
                    "type": "string",
                    "description": "Alias for path; accepted for compatibility",
                },
            },
        }

    def validate(self, tool_input: dict[str, Any]) -> str | None:
        path_value = _pick_path(tool_input, "path", "file_path")
        if not path_value:
            return "Missing required field: path"
        unknown = _unknown_fields(tool_input, {"path", "file_path"})
        if unknown:
            return f"Unknown fields: {', '.join(unknown)}"
        return None

    def execute(self, tool_input: dict[str, Any]) -> str:
        try:
            target = _resolve_local_path(_pick_path(tool_input, "path", "file_path") or "")
            if not target.exists():
                return f"Error: path does not exist: {target}"
            if target.is_dir():
                return _format_directory_listing(target)
            return _read_text(target) or "(empty file)"
        except Exception as exc:
            return f"Error: {exc}"


class WriteFileTool(Tool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Write a file to the local workspace. Supports both relative paths and platform-native "
            "absolute paths. Prefer relative paths when working inside the current project."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to write"},
                "path": {
                    "type": "string",
                    "description": "Alias for file_path; accepted for compatibility",
                },
                "content": {"type": "string", "description": "File contents"},
            },
        }

    def validate(self, tool_input: dict[str, Any]) -> str | None:
        file_path = _pick_path(tool_input, "file_path", "path")
        if not file_path:
            return "Missing required field: file_path"
        if "content" not in tool_input:
            return "Missing required field: content"
        if not isinstance(tool_input["content"], str):
            return "Field 'content' must be a string"
        unknown = _unknown_fields(tool_input, {"file_path", "path", "content"})
        if unknown:
            return f"Unknown fields: {', '.join(unknown)}"
        return None

    def execute(self, tool_input: dict[str, Any]) -> str:
        try:
            target = _resolve_local_path(_pick_path(tool_input, "file_path", "path") or "")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.is_dir():
                return f"Error: target is a directory: {target}"
            target.write_text(tool_input["content"], encoding="utf-8")
            return f"Wrote {len(tool_input['content'])} chars to {target}"
        except Exception as exc:
            return f"Error: {exc}"


class EditFileTool(Tool):
    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return (
            "Perform exact string replacements in files. The edit fails if old_string is not "
            "present or is ambiguous while replace_all is false."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to modify"},
                "old_string": {"type": "string", "description": "Text to replace"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace every occurrence instead of just one",
                    "default": False,
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        file_path = tool_input["file_path"]
        old_string = tool_input["old_string"]
        new_string = tool_input["new_string"]
        replace_all = tool_input.get("replace_all", False)

        if old_string == new_string:
            return "Error: old_string and new_string are identical"

        try:
            target = _resolve_local_path(file_path)
            content = _read_text(target)
        except FileNotFoundError:
            return f"Error: file not found: {file_path}"
        except Exception as exc:
            return f"Error: failed to read file: {exc}"

        count = content.count(old_string)
        if count == 0:
            preview = content[:200] + "..." if len(content) > 200 else content
            return f"Error: old_string not found. File preview:\n{preview}"

        if replace_all:
            new_content = content.replace(old_string, new_string)
            replaced = count
        else:
            if count > 1:
                return (
                    f"Error: found {count} matches. Provide more context or set replace_all=true."
                )
            new_content = content.replace(old_string, new_string, 1)
            replaced = 1

        try:
            target.write_text(new_content, encoding="utf-8")
            return f"Replaced {replaced} occurrence(s) in {target}"
        except Exception as exc:
            return f"Error: failed to write file: {exc}"


class BashTool(Tool):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        if os.name == "nt":
            return (
                "Execute a shell command and return stdout and stderr. On Windows, the tool uses "
                "PowerShell by default and falls back to Bash when Bash-only syntax is detected. "
                "Prefer portable commands such as ls, pwd, cat, python, mkdir -p, and relative paths."
            )
        return (
            "Execute a shell command and return stdout and stderr. Prefer portable commands and "
            "relative paths when working inside the current project."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        shell_name = "PowerShell/Bash command" if os.name == "nt" else "Shell command"
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": f"{shell_name} to execute from the current working directory",
                }
            },
            "required": ["command"],
        }

    def execute(self, tool_input: dict[str, Any]) -> str:
        command = tool_input.get("command", "").strip()
        if not command:
            return "Error: command is required"

        try:
            result = _run_shell(command)
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 30 seconds"
        except Exception as exc:
            return f"Error: {exc}"

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = (stdout + stderr).strip()

        if result.returncode != 0:
            if output:
                return f"(exit {result.returncode})\n{output}"
            return f"Error: command failed with exit code {result.returncode}"

        return output or "(no output)"


def clean_cache_control(messages: list[dict[str, Any]]):
    positions = []
    for i, msg in enumerate(messages):
        if isinstance(msg, dict) and "cache_control" in msg:
            positions.append((i, None))
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, list):
            for j, block in enumerate(content):
                if isinstance(block, dict) and "cache_control" in block:
                    positions.append((i, j))

    if len(positions) <= 1:
        return messages

    for msg_idx, block_idx in positions[:-1]:
        if block_idx is None:
            del messages[msg_idx]["cache_control"]
        else:
            del messages[msg_idx]["content"][block_idx]["cache_control"]
    return messages
