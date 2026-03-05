from __future__ import annotations

import threading
from typing import Any

from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils import timezone

try:
    from channels.layers import get_channel_layer
except Exception:  # pragma: no cover - optional dependency in local environments
    get_channel_layer = None

_proposal_event_lock = threading.Lock()
_proposal_event_buffers: dict[str, dict[str, Any]] = {}


def tender_group_name(kind: str, tender_id: int) -> str:
    return f"tender_rt_{kind}_{tender_id}"


def _send_tender_event(kind: str, tender_id: int, event: str, payload: dict[str, Any]) -> None:
    try:
        if get_channel_layer is None:
            return
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            tender_group_name(kind, tender_id),
            {
                "type": "tender.event",
                "event": event,
                "payload": payload,
                "sent_at": timezone.now().isoformat(),
            },
        )
    except Exception:
        # Realtime delivery must not break tender bidding flow.
        return


def _flush_coalesced_proposal_event(buffer_key: str) -> None:
    with _proposal_event_lock:
        buffer = _proposal_event_buffers.pop(buffer_key, None)
    if not buffer:
        return
    proposal_ids = list(buffer.get("proposal_ids") or [])
    payload = dict(buffer.get("payload") or {})
    if proposal_ids:
        payload["proposal_ids"] = proposal_ids
        payload["proposal_id"] = proposal_ids[0]
        payload.pop("submitted_at", None)
    _send_tender_event(
        kind=str(buffer.get("kind") or ""),
        tender_id=int(buffer.get("tender_id") or 0),
        event=str(buffer.get("event") or ""),
        payload=payload,
    )


def _queue_coalesced_proposal_event(
    kind: str,
    tender_id: int,
    event: str,
    payload: dict[str, Any],
) -> bool:
    window_ms = int(getattr(settings, "REALTIME_PROPOSAL_EVENT_COALESCE_MS", 0) or 0)
    if window_ms <= 0:
        return False
    proposal_id = int(payload.get("proposal_id") or 0)
    if proposal_id <= 0:
        return False
    max_ids = max(
        1, int(getattr(settings, "REALTIME_PROPOSAL_EVENT_COALESCE_MAX_IDS", 300) or 300)
    )
    buffer_key = f"{kind}:{tender_id}:{event}"
    should_flush_now = False
    with _proposal_event_lock:
        buffer = _proposal_event_buffers.get(buffer_key)
        if buffer is None:
            timer = threading.Timer(
                max(0.01, window_ms / 1000.0),
                _flush_coalesced_proposal_event,
                args=(buffer_key,),
            )
            timer.daemon = True
            _proposal_event_buffers[buffer_key] = {
                "kind": kind,
                "tender_id": int(tender_id),
                "event": event,
                "payload": dict(payload),
                "proposal_ids": [proposal_id],
                "proposal_ids_set": {proposal_id},
                "timer": timer,
            }
            timer.start()
            return True
        proposal_ids_set = buffer.get("proposal_ids_set")
        if proposal_id not in proposal_ids_set:
            proposal_ids_set.add(proposal_id)
            buffer["proposal_ids"].append(proposal_id)
        if len(buffer["proposal_ids"]) >= max_ids:
            timer = buffer.get("timer")
            if timer is not None:
                timer.cancel()
            should_flush_now = True
    if should_flush_now:
        _flush_coalesced_proposal_event(buffer_key)
    return True


def publish_tender_event(kind: str, tender_id: int, event: str, payload: dict[str, Any]) -> None:
    if event.startswith("proposal."):
        if _queue_coalesced_proposal_event(kind, tender_id, event, payload):
            return
    _send_tender_event(kind, tender_id, event, payload)
