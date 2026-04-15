from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable


DEFAULT_OPENAI_MODEL = "gpt-5.4"
DEFAULT_DEEPSEEK_MODEL = "deepseek-reasoner"
DEFAULT_DEEPSEEK_TOOL_MODEL = "deepseek-chat"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MAX_TOKENS = 8192
DEFAULT_DEEPSEEK_CONTEXT_WINDOW = 131072
EMERGENCY_CONTEXT_NOTICE = (
    "[系统提示] 为适配模型上下文长度，较早的对话与工具输出已被自动压缩，请以最近几轮结果为准继续。"
)


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


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


def default_provider(
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    explicit = provider or os.getenv("LLM_PROVIDER")
    if explicit:
        return explicit.lower()
    if base_url and "deepseek" in base_url.lower():
        return "deepseek"
    if model and model.startswith("deepseek-"):
        return "deepseek"
    if _env_first("DEEPSEEK_API_KEY", "DEEPSEEK_APIKEY"):
        return "deepseek"
    return "openai"


def default_model(
    fallback: str | None = None,
    *,
    provider: str | None = None,
) -> str:
    resolved_provider = default_provider(provider=provider, model=fallback)
    if resolved_provider == "deepseek":
        deepseek_fallback = (
            fallback if fallback and fallback.startswith("deepseek-") else DEFAULT_DEEPSEEK_MODEL
        )
        return os.getenv("DEEPSEEK_MODEL", deepseek_fallback)
    openai_fallback = (
        fallback if fallback and not fallback.startswith("deepseek-") else DEFAULT_OPENAI_MODEL
    )
    return os.getenv("OPENAI_MODEL", openai_fallback)


def create_harness_client(
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'openai'. Install it with `pip install openai`."
        ) from exc

    resolved_provider = default_provider(provider=provider, model=model, base_url=base_url)
    resolved_model = model or default_model(provider=resolved_provider)
    if resolved_provider == "deepseek":
        resolved_api_key = api_key or _env_first("DEEPSEEK_API_KEY", "DEEPSEEK_APIKEY")
        resolved_base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL)
        tool_model_name = os.getenv("DEEPSEEK_TOOL_MODEL", DEFAULT_DEEPSEEK_TOOL_MODEL)
    else:
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL")
        tool_model_name = None

    if not resolved_api_key:
        expected_var = (
            "DEEPSEEK_API_KEY (or DEEPSEEK_APIKEY)"
            if resolved_provider == "deepseek"
            else "OPENAI_API_KEY"
        )
        raise RuntimeError(f"Missing API key. Set `{expected_var}` or pass api_key explicitly.")

    raw_client = OpenAI(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
    )
    return OpenAIHarnessClient(
        raw_client,
        default_model_name=resolved_model,
        provider=resolved_provider,
        tool_model_name=tool_model_name,
    )


class OpenAIHarnessClient:
    def __init__(
        self,
        raw_client: Any,
        *,
        default_model_name: str,
        provider: str = "openai",
        tool_model_name: str | None = None,
    ):
        self._raw_client = raw_client
        self.default_model_name = default_model_name
        self.provider = provider
        self.tool_model_name = tool_model_name
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
        openai_tools = _to_openai_tools(tools or [])
        request_model = model or self._parent.default_model_name
        if openai_tools and _requires_tool_model_fallback(
            provider=self._parent.provider,
            model=request_model,
        ):
            request_model = self._parent.tool_model_name or request_model

        request_kwargs = _normalize_chat_completion_kwargs(kwargs)
        chat = self._parent._raw_client.chat.completions
        raw_messages = deepcopy(messages or [])
        request_max_tokens = _normalize_max_tokens(
            max_tokens,
            provider=self._parent.provider,
            model=request_model,
        )
        context_compaction_level = 0

        while True:
            request = {
                "model": request_model,
                "messages": _to_openai_messages(system=system, messages=raw_messages),
                **request_kwargs,
            }
            if openai_tools:
                request["tools"] = openai_tools
                request["tool_choice"] = "auto"
            if request_max_tokens is not None:
                request["max_tokens"] = request_max_tokens

            try:
                raw_response = chat.create(**request)
                break
            except Exception as exc:
                token_limit = _extract_max_tokens_upper_bound(exc)
                context_error = _extract_context_length_error(exc)

                if (
                    request_max_tokens is not None
                    and token_limit is not None
                    and token_limit < request_max_tokens
                ):
                    request_max_tokens = token_limit
                    continue

                if context_error is not None:
                    next_level = context_compaction_level + 1
                    compacted_messages = _compact_messages_for_context_limit(
                        raw_messages,
                        level=next_level,
                    )
                    compacted_max_tokens = _shrink_completion_for_context_error(
                        request_max_tokens,
                        context_error=context_error,
                        provider=self._parent.provider,
                        model=request_model,
                    )
                    if compacted_messages == raw_messages and compacted_max_tokens == request_max_tokens:
                        raise
                    raw_messages = compacted_messages
                    request_max_tokens = compacted_max_tokens
                    context_compaction_level = next_level
                    continue

                if request_max_tokens is None or not _should_retry_with_max_completion_tokens(exc):
                    raise

                retry_tokens = request_max_tokens
                if token_limit is not None:
                    retry_tokens = min(retry_tokens, token_limit)
                request.pop("max_tokens", None)
                request["max_completion_tokens"] = retry_tokens
                raw_response = chat.create(**request)
                break

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


def _normalize_max_tokens(
    max_tokens: int | None,
    *,
    provider: str,
    model: str,
) -> int | None:
    if max_tokens is None:
        return None

    normalized = max(1, int(max_tokens))
    known_limit = _known_max_tokens_limit(provider=provider, model=model)
    if known_limit is None:
        return normalized
    return min(normalized, known_limit)


def _known_max_tokens_limit(*, provider: str, model: str) -> int | None:
    if provider == "deepseek" or model.startswith("deepseek-"):
        return DEFAULT_DEEPSEEK_MAX_TOKENS
    return None


def _extract_max_tokens_upper_bound(exc: Exception) -> int | None:
    message = str(exc)
    patterns = (
        r"valid range of max_tokens is \[\s*\d+\s*,\s*(\d+)\s*\]",
        r"max_tokens[^0-9]+(?:from\s+\d+\s+to|between)\s+\d+\s+(?:and|to)\s+(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_context_length_error(exc: Exception) -> dict[str, int] | None:
    message = str(exc)
    patterns = (
        r"maximum context length is (?P<context>\d+) tokens.*?requested (?P<requested>\d+) tokens "
        r"\((?P<messages>\d+) in the messages, (?P<completion>\d+) in the completion\)",
        r"context length is (?P<context>\d+) tokens.*?requested (?P<requested>\d+) tokens "
        r"\((?P<messages>\d+) in the messages, (?P<completion>\d+) in the completion\)",
    )
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return {
                "context": int(match.group("context")),
                "requested": int(match.group("requested")),
                "messages": int(match.group("messages")),
                "completion": int(match.group("completion")),
            }
    return None


def _shrink_completion_for_context_error(
    max_tokens: int | None,
    *,
    context_error: dict[str, int],
    provider: str,
    model: str,
) -> int | None:
    known_limit = _known_max_tokens_limit(provider=provider, model=model)
    fallback = known_limit or 1024
    current = max_tokens or fallback

    available = context_error["context"] - context_error["messages"] - 1
    if available > 0:
        return max(1, min(current, available))

    return max(1, min(current, 1024))


def _compact_messages_for_context_limit(
    messages: list[dict[str, Any]],
    *,
    level: int,
) -> list[dict[str, Any]]:
    if not messages:
        return []

    compacted = deepcopy(messages)
    total = len(compacted)
    keep_recent = 8 if level == 1 else 6 if level == 2 else 4

    for index, message in enumerate(compacted):
        is_recent = index >= max(0, total - keep_recent)
        compacted[index] = _compact_single_message(
            message,
            level=level,
            is_recent=is_recent,
        )

    if level >= 2 and len(compacted) > keep_recent + 2:
        compacted = [compacted[0], {"role": "user", "content": EMERGENCY_CONTEXT_NOTICE}, *compacted[-keep_recent:]]

    if level >= 3 and len(compacted) > 5:
        compacted = [compacted[0], {"role": "user", "content": EMERGENCY_CONTEXT_NOTICE}, *compacted[-4:]]

    if level >= 4:
        compacted = [{"role": "user", "content": EMERGENCY_CONTEXT_NOTICE}, *compacted[-3:]]

    return compacted


def _compact_single_message(
    message: dict[str, Any],
    *,
    level: int,
    is_recent: bool,
) -> dict[str, Any]:
    compacted = dict(message)
    content = compacted.get("content")

    if isinstance(content, str):
        limit = _message_text_limit(level=level, is_recent=is_recent)
        compacted["content"] = _truncate_text(content, limit)
        return compacted

    if not isinstance(content, list):
        return compacted

    new_content: list[Any] = []
    for block in content:
        if not isinstance(block, dict):
            new_content.append(block)
            continue
        compacted_block = dict(block)
        block_type = compacted_block.get("type")

        if block_type == "tool_result":
            limit = _tool_result_limit(level=level, is_recent=is_recent)
            compacted_block["content"] = _truncate_text(
                _stringify_content(compacted_block.get("content", "")),
                limit,
            )
            compacted_block.pop("cache_control", None)
        elif block_type == "text":
            limit = _message_text_limit(level=level, is_recent=is_recent)
            compacted_block["text"] = _truncate_text(str(compacted_block.get("text", "")), limit)
        elif block_type in {"thinking", "redacted_thinking"} and not is_recent:
            continue

        new_content.append(compacted_block)

    compacted["content"] = new_content
    return compacted


def _message_text_limit(*, level: int, is_recent: bool) -> int:
    if level >= 4:
        return 160
    if level == 3:
        return 240 if is_recent else 160
    if level == 2:
        return 600 if is_recent else 240
    return 2400 if is_recent else 400


def _tool_result_limit(*, level: int, is_recent: bool) -> int:
    if level >= 4:
        return 220
    if level == 3:
        return 480 if is_recent else 220
    if level == 2:
        return 1200 if is_recent else 360
    return 4000 if is_recent else 600


def _truncate_text(value: str, limit: int) -> str:
    if limit <= 0:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    if limit <= 32:
        return text[:limit]
    head = max(1, int(limit * 0.7))
    tail = max(1, limit - head - len("\n...[已截断]...\n"))
    return text[:head] + "\n...[已截断]...\n" + text[-tail:]


def _normalize_chat_completion_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(kwargs)

    # Claude-style thinking blocks are used in some labs, but the current
    # OpenAI/DeepSeek compatibility layer is implemented on chat.completions,
    # which does not accept a `thinking` argument.
    normalized.pop("thinking", None)

    return normalized


def _requires_tool_model_fallback(*, provider: str, model: str) -> bool:
    return provider == "deepseek" and model == DEFAULT_DEEPSEEK_MODEL


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
