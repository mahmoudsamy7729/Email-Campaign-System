from __future__ import annotations
from typing import Callable, Dict, List
from django.db import transaction
from campaign.models import Campaign, CampaignStatus
from .redis_service import (
    redis_lock, lock_key, get_inflight, incr_inflight, pop_chunk,
    queue_len, cleanup
)

def svc_dispatch(
    campaign_id: str,
    *,
    chunk_size: int,
    max_inflight: int,
    schedule_chunk: Callable[[str, List[str]], None],
) -> Dict:
    try:
        c = Campaign.objects.only("status").get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return {"detail": "Campaign not found"}
    if c.status != CampaignStatus.Sending:
        return {"detail": f"Not dispatching; status={c.status}"}

    dispatched = 0
    with redis_lock(lock_key(campaign_id)) as ok:
        if not ok:
            return {"detail": "Dispatch lock busy"}

        current = get_inflight(campaign_id)
        need = max(0, max_inflight - current)

        for _ in range(need):
            emails_chunk = pop_chunk(campaign_id, chunk_size)
            if not emails_chunk:
                break
            incr_inflight(campaign_id)
            schedule_chunk(campaign_id, emails_chunk)
            dispatched += 1

    if dispatched == 0:
        return maybe_finalize(campaign_id)
    return {"dispatched": dispatched, "inflight_now": get_inflight(campaign_id)}

def maybe_finalize(campaign_id: str) -> Dict:
    from .redis_service import get_inflight
    remaining = queue_len(campaign_id)
    inflight = get_inflight(campaign_id)
    if remaining == 0 and inflight == 0:
        with transaction.atomic():
            c = Campaign.objects.select_for_update().get(pk=campaign_id)
            if c.status == CampaignStatus.Sending:
                c.status = CampaignStatus.Completed
                c.completed_at = c.completed_at or c._meta.get_field("completed_at").pre_save(c, add=True)
                c.save(update_fields=["status", "completed_at"])
        cleanup(campaign_id)
        return {"status": "completed"}
    return {"status": "not-done", "remaining": remaining, "inflight": inflight}