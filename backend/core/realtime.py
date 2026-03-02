from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone


def tender_group_name(kind: str, tender_id: int) -> str:
    return f"tender_rt_{kind}_{tender_id}"


def publish_tender_event(kind: str, tender_id: int, event: str, payload: dict[str, Any]) -> None:
    try:
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
