import json
import os
import uuid
from datetime import datetime


class SessionStore:
    """保存和恢复对话会话。对应 Claude Code 的 session persistence。"""

    def __init__(self, store_dir: str = ".sessions"):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)

    def new_session_id(self) -> str:
        return str(uuid.uuid4())[:8]

    def save(self, session_id: str, messages: list, metadata: dict = None):
        """保存会话到 JSON 文件"""
        serializable = []
        for msg in messages:
            if isinstance(msg.get("content"), list):
                new_content = []
                for block in msg["content"]:
                    if hasattr(block, "__dict__"):
                        d = {"type": block.type}
                        if block.type == "text":
                            d["text"] = block.text
                        elif block.type == "tool_use":
                            d["id"] = block.id
                            d["name"] = block.name
                            d["input"] = block.input
                        new_content.append(d)
                    else:
                        new_content.append(block)
                serializable.append({**msg, "content": new_content})
            else:
                serializable.append(msg)
        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": serializable,
            "metadata": metadata or {},
        }
        path = os.path.join(self.store_dir, f"{session_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, session_id: str) -> tuple[list, dict]:
        path = os.path.join(self.store_dir, f"{session_id}.json")
        with open(path, "r") as f:
            data = json.load(f)
        # 清理消息中的无效字段（如 SDK 对象序列化残留的 caller: null）
        messages = data["messages"]
        for msg in messages:
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        # 移除 API 不接受的字段
                        for key in ["caller", "server_tool_use"]:
                            block.pop(key, None)
        return messages, data.get("metadata", {})

    def list_sessions(self) -> list[dict]:
        sessions = []
        for fname in os.listdir(self.store_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.store_dir, fname)) as f:
                        data = json.load(f)
                    sessions.append({
                        "id": data["session_id"],
                        "time": data.get("timestamp"),
                        "messages": data.get("message_count", 0),
                    })
                except Exception:
                    pass
        return sorted(sessions, key=lambda x: x["time"], reverse=True)


class SessionRewind:
    """简化版 Rewind：在每轮对话保存检查点，支持回退。"""

    def __init__(self):
        self.checkpoints: list[tuple[int, list]] = []

    def checkpoint(self, turn: int, messages: list):
        self.checkpoints.append((turn, [m for m in messages]))

    def rewind_to(self, turn: int) -> list | None:
        for t, msgs in reversed(self.checkpoints):
            if t <= turn:
                return msgs[:]
        return None

    def list_checkpoints(self) -> list[int]:
        return [t for t, _ in self.checkpoints]
