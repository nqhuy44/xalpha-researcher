"""TOON (Token-Oriented Object Notation) encoder.

A compact, LLM-friendly serialization for structured data. Roughly 30-50% fewer
tokens than indented JSON for typical record-shaped payloads, with no loss of
information that an LLM cares about.

Spec reference: https://toonformat.dev. Example:

    JSON:                                    TOON:
    {                                        peers[2]{ticker,rsi}:
      "peers": [                               HPG,55.2
        {"ticker": "HPG", "rsi": 55.2},        VNM,48.1
        {"ticker": "VNM", "rsi": 48.1}
      ]
    }

This module ships only the encoder — LLMs read TOON, we don't parse it back.
The official `toon-format` package on PyPI is a namespace reservation as of
2026-05 (its `encode()` raises `NotImplementedError`); we keep our public API
shaped like the spec so swapping to it later is a one-line change.

Migration safety: once `toon-format` is real, replace these two functions with
shims that call `toon_format.encode()` and the call sites stay unchanged.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

_INDENT_UNIT = "  "


def encode(value: Any, *, name: str | None = None, indent: int = 0) -> str:
    """Encode a Python value as TOON.

    Accepts dicts, lists, Pydantic models (auto-converted via `model_dump()`),
    and primitives. Uniform-shape dict arrays render as tabular blocks; mixed
    arrays fall back to nested objects.

    Args:
        value: The value to encode.
        name: Optional outer key — used when the value is a list passed at the
            top level, so the result has a `name[N]…:` header instead of an
            anonymous one.
        indent: Internal indentation depth. Callers should leave at 0.

    Returns:
        A TOON string with no trailing newline.
    """
    if _is_pydantic(value):
        value = value.model_dump()

    pad = _INDENT_UNIT * indent

    if isinstance(value, Mapping):
        return _encode_mapping(value, indent)

    if isinstance(value, list):
        return _encode_list(value, name=name, indent=indent)

    return f"{pad}{_scalar(value)}"


def encode_pydantic(model: Any, *, name: str | None = None) -> str:
    """Convenience wrapper for Pydantic models. Equivalent to
    `encode(model.model_dump(), name=name)`.
    """
    if not _is_pydantic(model):
        raise TypeError(f"encode_pydantic expected a Pydantic model, got {type(model).__name__}")
    return encode(model.model_dump(), name=name)


# -- internals ---------------------------------------------------------------


def _is_pydantic(obj: Any) -> bool:
    return hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump"))


def _is_uniform_record_array(value: Any) -> bool:
    """True if `value` is a non-empty list of dicts with identical key sets."""
    if not isinstance(value, list) or not value:
        return False
    if not all(isinstance(item, Mapping) for item in value):
        return False
    keys = list(value[0].keys())
    return all(list(item.keys()) == keys for item in value)


def _scalar(v: Any) -> str:
    """Render a scalar in the most compact form that still round-trips meaning.

    Quotes are added only when the raw string would be ambiguous (contains the
    row delimiter `,`, a newline, leading/trailing whitespace, or starts with a
    structural character).
    """
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)

    s = str(v)
    if s == "":
        return '""'
    needs_quote = (
        "," in s
        or "\n" in s
        or s != s.strip()
        or s[0] in "[{:#-"  # structural / could be parsed as length-marker / negative-leading edge
    )
    if needs_quote:
        return json.dumps(s, ensure_ascii=False)
    return s


def _encode_row(row: Mapping[str, Any], columns: Sequence[str]) -> str:
    return ",".join(_scalar(row.get(c)) for c in columns)


def _encode_list(value: list, *, name: str | None, indent: int) -> str:
    pad = _INDENT_UNIT * indent
    inner_pad = _INDENT_UNIT * (indent + 1)

    if not value:
        prefix = f"{name}[0]:" if name else "[0]:"
        return f"{pad}{prefix}"

    if _is_uniform_record_array(value):
        cols = list(value[0].keys())
        header_body = f"[{len(value)}]{{{','.join(cols)}}}:"
        prefix = f"{name}{header_body}" if name else header_body
        rows = [f"{inner_pad}{_encode_row(row, cols)}" for row in value]
        return "\n".join([f"{pad}{prefix}", *rows])

    if all(_is_scalar(item) for item in value):
        body = ",".join(_scalar(item) for item in value)
        prefix = f"{name}[{len(value)}]:" if name else f"[{len(value)}]:"
        return f"{pad}{prefix} {body}"

    # Mixed-shape array: render each item on its own line as nested object/scalar.
    prefix = f"{name}[{len(value)}]:" if name else f"[{len(value)}]:"
    lines = [f"{pad}{prefix}"]
    for item in value:
        if isinstance(item, Mapping):
            lines.append(_encode_mapping(item, indent + 1))
        elif isinstance(item, list):
            lines.append(_encode_list(item, name=None, indent=indent + 1))
        else:
            lines.append(f"{inner_pad}{_scalar(item)}")
    return "\n".join(lines)


def _encode_mapping(value: Mapping[str, Any], indent: int) -> str:
    pad = _INDENT_UNIT * indent
    lines: list[str] = []

    for key, v in value.items():
        if _is_pydantic(v):
            v = v.model_dump()

        if isinstance(v, Mapping):
            if not v:
                lines.append(f"{pad}{key}:")
                continue
            lines.append(f"{pad}{key}:")
            lines.append(_encode_mapping(v, indent + 1))
        elif isinstance(v, list):
            lines.append(_encode_list(v, name=key, indent=indent))
        else:
            lines.append(f"{pad}{key}: {_scalar(v)}")

    return "\n".join(lines)


def _is_scalar(v: Any) -> bool:
    return v is None or isinstance(v, (bool, int, float, str))
