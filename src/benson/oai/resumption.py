"""OAI-PMH resumption token encode/decode."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ResumptionState:
    verb: str
    metadata_prefix: str
    set_spec: str | None
    from_raw: str | None
    until_raw: str | None
    cursor: int


def encode_token(state: ResumptionState) -> str:
    payload = json.dumps(asdict(state), separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decode_token(token: str) -> ResumptionState | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        data: dict[str, Any] = json.loads(raw.decode("utf-8"))
        return ResumptionState(
            verb=str(data["verb"]),
            metadata_prefix=str(data["metadata_prefix"]),
            set_spec=data.get("set_spec"),
            from_raw=data.get("from_raw"),
            until_raw=data.get("until_raw"),
            cursor=int(data["cursor"]),
        )
    except (ValueError, KeyError, json.JSONDecodeError, TypeError):
        return None
