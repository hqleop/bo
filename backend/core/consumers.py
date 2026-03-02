from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import (
    CompanyUser,
    ProcurementTender,
    SalesTender,
    TenderProposal,
    SalesTenderProposal,
)
from .realtime import tender_group_name


VISIBLE_PARTICIPATION_STAGES = ["acceptance", "decision", "approval", "completed", "preparation"]


class TenderRealtimeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.kind = str(self.scope["url_route"]["kwargs"].get("kind", "")).strip()
        tender_id_raw = self.scope["url_route"]["kwargs"].get("tender_id")
        try:
            self.tender_id = int(tender_id_raw)
        except (TypeError, ValueError):
            await self.close(code=4400)
            return

        if self.kind not in {"procurement", "sales"}:
            await self.close(code=4400)
            return

        has_access = await _user_can_access_tender(user.id, self.kind, self.tender_id)
        if not has_access:
            await self.close(code=4403)
            return

        self.group_name = tender_group_name(self.kind, self.tender_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "payload": {"kind": self.kind, "tender_id": self.tender_id}})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("event") == "ping":
            await self.send_json({"event": "pong"})

    async def tender_event(self, event):
        await self.send_json(
            {
                "event": event.get("event"),
                "payload": event.get("payload") or {},
                "sent_at": event.get("sent_at"),
            }
        )


@database_sync_to_async
def _user_can_access_tender(user_id: int, kind: str, tender_id: int) -> bool:
    company_ids = list(
        CompanyUser.objects.filter(
            user_id=user_id,
            status=CompanyUser.Status.APPROVED,
        ).values_list("company_id", flat=True)
    )
    if not company_ids:
        return False

    if kind == "procurement":
        tender = ProcurementTender.objects.filter(id=tender_id).values("company_id").first()
        if not tender:
            return False
        if tender["company_id"] in company_ids:
            return True
        if TenderProposal.objects.filter(
            tender_id=tender_id,
            supplier_company_id__in=company_ids,
        ).exists():
            return True
        return ProcurementTender.objects.filter(
            id=tender_id,
            conduct_type__in=["rfx", "online_auction"],
            stage__in=VISIBLE_PARTICIPATION_STAGES,
        ).exclude(company_id__in=company_ids).exists()

    tender = SalesTender.objects.filter(id=tender_id).values("company_id").first()
    if not tender:
        return False
    if tender["company_id"] in company_ids:
        return True
    if SalesTenderProposal.objects.filter(
        tender_id=tender_id,
        supplier_company_id__in=company_ids,
    ).exists():
        return True
    return SalesTender.objects.filter(
        id=tender_id,
        conduct_type__in=["rfx", "online_auction"],
        stage__in=VISIBLE_PARTICIPATION_STAGES,
    ).exclude(company_id__in=company_ids).exists()
