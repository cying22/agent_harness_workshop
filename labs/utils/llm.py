from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable


DEFAULT_OPENAI_MODEL = "gpt-5.4"


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class CompatMessage:
    content: list[Any]
    stop_reason: str
    model: str | None = None


def default_model(fallback: str = DEFAULT_OPENAI_MODEL) -> str:
    return os.getenv("OPENAI_MODEL", fallback)


def create_harness_client(
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'openai'. Install it with `pip install openai`."
        ) from exc

    resolved_model = model or default_model()
    raw_client = OpenAI(
        api_key=api_key or os.getenv("OPENAI_API_KEY"),
        base_url=base_url or os.getenv("OPENAI_BASE_URL"),
    )
    return OpenAIHarnessClient(raw_client, default_model_name=resolved_model)


class OpenAIHarnessClient:
    def __init__(self, raw_client: Any, *, default_model_name: str):
        self._raw_client = raw_client
        self.default_model_name = default_model_name
        self.messages = _MessagesAPI(self)


class _MessagesAPI:
    def __init__(self, parent: OpenAIHarnessClient):
        self._parent = parent

    def create(
        self,
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> CompatMessage:
        request = {
            "model": model or self._parent.default_model_name,
            "messages": _to_openai_messages(system=system, messages=messages or []),
            **kwargs,
        }

        openai_tools = _to_openai_tools(tools or [])
        if openai_tools:
            request["tools"] = openai_tools
            request["tool_choice"] = "auto"
        if max_tokens is not None:
            request["max_tokens"] = max_tokens

        chat = self._parent._raw_client.chat.completions
        try:
            raw_response = chat.create(**request)
        except Exception as exc:
            if max_tokens is None or not _should_retry_with_max_completion_tokens(exc):
                raise
            retry_request = dict(request)
            retry_request.pop("max_tokens", None)
            retry_request["max_completion_tokens"] = max_tokens
            raw_response = chat.create(**retry_request)

        return _from_openai_response(raw_response)

    def stream(self, **kwargs: Any):
        return _CompatStream(self, kwargs)


class _CompatStream:
    def __init__(self, api: _MessagesAPI, kwargs: dict[str, Any]):
        self._api = api
        self._kwargs = kwargs
        self._response: CompatMessage | None = None
        self.text_stream: Iterable[str] = ()

    def __enter__(self):
        self._response = self._api.create(**self._kwargs)
        self.text_stream = _iter_text_chunks(self._response.content)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_final_message(self) -> CompatMessage:
        if self._response is None:
            raise RuntimeError("Stream has not started.")
        return self._response


def _should_retry_with_max_completion_tokens(exc: Exception) -> bool:
    message = str(exc).lower()
    return "max_tokens" in message and "max_completion_tokens" in message


def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted = []
    for tool in tools:
        name = tool.get("name")
        if not name:
            continue
        parameters = deepcopy(tool.get("input_schema") or {"type": "object", "properties": {}})
        if parameters.get("type") == "object" and "additionalProperties" not in parameters:
            parameters["additionalProperties"] = False
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": parameters,
                },
            }
        )
    return converted


def _to_openai_messages(
    *,
    system: str | None,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    if system:
        converted.append({"role": "system", "content": system})

    for message in messages:
        role = message.get("role")
        content = message.get("content")

        if role == "assistant":
            assistant_message = _assistant_message_from_content(content)
            if assistant_message is not None:
                converted.append(assistant_message)
            continue

        if role == "user":
            converted.extend(_user_messages_from_content(content))
            continue

        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": message["tool_call_id"],
                    "content": _stringify_content(content),
                }
            )
            continue

        converted.append({"role": role or "user", "content": _stringify_content(content)})

    return converted


def _assistant_message_from_content(content: Any) -> dict[str, Any] | None:
    if isinstance(content, str):
        return {"role": "assistant", "content": content}

    blocks = _as_block_list(content)
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    for block in blocks:
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text")
            if text:
                text_parts.append(text)
        elif block_type == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id"),
                    "type": "function",
                    "function": {
                        "name": block.get("name"),
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                    },
                }
            )

    if not text_parts and not tool_calls:
        return None

    return {
        "role": "assistant",
        "content": "\n".join(text_parts) if text_parts else None,
        **({"tool_calls": tool_calls} if tool_calls else {}),
    }


def _user_messages_from_content(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"role": "user", "content": content}]

    blocks = _as_block_list(content)
    converted: list[dict[str, Any]] = []
    pending_text: list[str] = []

    def flush_text() -> None:
        if pending_text:
            converted.append({"role": "user", "content": "\n".join(pending_text)})
            pending_text.clear()

    for block in blocks:
        block_type = block.get("type")
        if block_type == "tool_result":
            flush_text()
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id"),
                    "content": _stringify_content(block.get("content", "")),
                }
            )
        elif block_type == "text":
            text = block.get("text")
            if text:
                pending_text.append(text)
        else:
            value = block.get("content")
            if value:
                pending_text.append(_stringify_content(value))

    flush_text()
    if converted:
        return converted
    return [{"role": "user", "content": _stringify_content(content)}]


def _from_openai_response(raw_response: Any) -> CompatMessage:
    choice = raw_response.choices[0]
    message = choice.message
    content: list[Any] = []

    if message.content:
        content.append(TextBlock(message.content))

    for tool_call in message.tool_calls or []:
        content.append(
            ToolUseBlock(
                id=tool_call.id,
                name=tool_call.function.name,
                input=_parse_tool_arguments(tool_call.function.arguments),
            )
        )

    return CompatMessage(
        content=content,
        stop_reason=_map_finish_reason(choice.finish_reason),
        model=getattr(raw_response, "model", None),
    )


def _map_finish_reason(finish_reason: str | None) -> str:
    return {
        "tool_calls": "tool_use",
        "length": "max_tokens",
        "stop": "end_turn",
        "content_filter": "end_turn",
    }.get(finish_reason, "end_turn")


def _parse_tool_arguments(arguments: str | None) -> dict[str, Any]:
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError:
        return {"raw_arguments": arguments}


def _as_block_list(content: Any) -> list[dict[str, Any]]:
    if not isinstance(content, list):
        return []
    blocks = []
    for block in content:
        if isinstance(block, dict):
            blocks.append(block)
        elif hasattr(block, "__dict__"):
            blocks.append(
                {
                    key: value
                    for key, value in vars(block).items()
                    if not key.startswith("_")
                }
            )
    return blocks


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _iter_text_chunks(content_blocks: list[Any], chunk_size: int = 32) -> Iterable[str]:
    text = "".join(
        block.text for block in content_blocks if getattr(block, "type", None) == "text"
    )
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]
