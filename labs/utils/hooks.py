from typing import Callable


class HookRunner:
    """生命周期钩子运行器：在工具执行前后插入自定义逻辑。"""

    def __init__(self):
        self.pre_tool_hooks: list[Callable] = []
        self.post_tool_hooks: list[Callable] = []

    def register_pre_tool(self, hook_fn: Callable) -> None:
        self.pre_tool_hooks.append(hook_fn)

    def register_post_tool(self, hook_fn: Callable) -> None:
        self.post_tool_hooks.append(hook_fn)

    def run_pre_tool(self, tool_name: str, tool_input: dict) -> dict | None:
        current_input = tool_input
        for hook in self.pre_tool_hooks:
            result = hook(tool_name, current_input)
            if result is None:
                return None
            current_input = result
        return current_input

    def run_post_tool(self, tool_name: str, tool_input: dict, result: str) -> str:
        current_result = result
        for hook in self.post_tool_hooks:
            current_result = hook(tool_name, tool_input, current_result)
        return current_result
