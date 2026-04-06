class ContextManager:
    """管理对话上下文，防止 token 溢出。对应 Claude Code 的 apiMicrocompact.ts。"""

    def __init__(self, max_tokens: int = 50000):
        self.max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        """粗略估算 token 数（1 token ≈ 3 个字符）"""
        return len(str(text)) // 3

    def count_message_tokens(self, messages: list) -> int:
        return sum(self.estimate_tokens(str(m)) for m in messages)

    def should_compact(self, messages: list) -> bool:
        """当 token 用量超过阈值的 80% 时触发压缩"""
        return self.count_message_tokens(messages) > self.max_tokens * 0.8

    def compact(self, messages: list) -> list:
        """压缩旧消息中的 tool_result，保留最近对话。"""
        if len(messages) <= 8:
            return messages
        keep_recent = 8
        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]
        compacted = []
        for msg in old_messages:
            if isinstance(msg.get("content"), list):
                new_content = []
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        original = str(block.get("content", ""))
                        if len(original) > 200:
                            block = {**block, "content": f"[已压缩] {original[:100]}... (原始 {len(original)} 字符)"}
                    new_content.append(block)
                msg = {**msg, "content": new_content}
            compacted.append(msg)
        boundary = {"role": "user", "content": "[系统提示：较早的对话上下文已被压缩以节省 token。]"}
        return compacted + [boundary] + recent_messages
