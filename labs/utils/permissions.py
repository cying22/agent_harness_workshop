from dataclasses import dataclass
from typing import Literal

DANGEROUS_PATTERNS = [
    "rm ", "rm\t", "rmdir",
    "sudo ",
    "chmod ", "chown ",
    "> /dev/", "mkfs",
    "curl | sh", "wget | sh",
    "dd if=",
    "mv /", "> /etc/", ">> /etc/",
]

SAFE_PATTERNS = [
    "ls", "cat ", "head ", "tail ",
    "echo ", "pwd", "whoami", "date",
    "python ", "python3 ", "node ",
    "pip list", "pip show",
    "git status", "git log", "git diff", "git branch",
    "wc ", "sort ", "grep ", "find ",
    "which ", "type ", "file ",
]


def classify_bash(command: str) -> str:
    """对 bash 命令进行安全分类。返回 allow / ask / deny。"""
    cmd = command.lower().strip()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd:
            return "ask"
    for pattern in SAFE_PATTERNS:
        if cmd.startswith(pattern):
            return "allow"
    return "ask"


@dataclass
class PermissionRule:
    tool_name: str
    behavior: Literal["allow", "deny", "ask"]
    pattern: str | None = None


class SmartPermissionChecker:
    """权限检查器，对 bash 命令使用分类器。"""

    def __init__(self):
        self.rules = [
            PermissionRule("read_file", "allow"),
            PermissionRule("write_file", "ask"),
            PermissionRule("bash", "ask"),
        ]

    def check(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "bash":
            return classify_bash(tool_input.get("command", ""))
        for rule in self.rules:
            if rule.tool_name == tool_name:
                return rule.behavior
        return "ask"
