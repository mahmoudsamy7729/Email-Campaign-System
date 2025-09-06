from celery import shared_task
from django.core.mail import get_connection
from django.db.models import F
from django.db import transaction
from typing import List, Dict
from .redis_keys import recipients_key, inflight_key, lock_key
from .redis_client import r, redis_lock

from campaign.models import Campaign, CampaignStatus
from campaign.services import email_service, exceptions, redis_service, dispatcher_service


CHUNK_SIZE = 30
MAX_INFLIGHT_CHUNKS = 3
PER_EMAIL_SLEEP = 0.6      # ≈300 emails/min total per campaign (≈5/sec)
TASK_RATE = "1000/m"       # or None; let sleep control throughput


@shared_task(bind=True, max_retries=3)
def kickoff_campaign_send(self, campaign_id: str) -> Dict:

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        emails = email_service.distinct_emails(email_service.recipient_qs_for(campaign))
    except Campaign.DoesNotExist:
        return {"detail": "Campaign not found"}
    except exceptions.ZeroRecipients:
        return {"detail": "No valid recipients found"}

    redis_service.init_state(campaign_id, emails)

    with transaction.atomic():
        campaign.mark_sending()
        campaign.estimated_recipients = len(emails)
        campaign.emails_sent = 0
        campaign.save(update_fields=["status", "started_sending_at", "estimated_recipients", "emails_sent"])

    dispatch_next_chunk.delay(campaign_id)
    return {"queued_recipients": len(emails)}


def _schedule_chunk(campaign_id: str, emails_chunk: List[str]) -> None:
    send_campaign_chunk.apply_async(args=[campaign_id, emails_chunk])

@shared_task(bind=True, max_retries=3)
def dispatch_next_chunk(self, campaign_id: str) -> Dict:
    return dispatcher_service.svc_dispatch(
        campaign_id,
        chunk_size=CHUNK_SIZE,
        max_inflight=MAX_INFLIGHT_CHUNKS,
        schedule_chunk=_schedule_chunk,
    )

@shared_task(bind=True, rate_limit=TASK_RATE, max_retries=3, acks_late=True)
def send_campaign_chunk(self, campaign_id: str, emails_chunk: List[str]) -> Dict:
    sent = 0
    processed = 0
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        compiled, text_fallback = email_service.get_campaign_content(campaign)
        if not compiled:
            redis_service.push_back_front(campaign_id, emails_chunk)
            return {"sent": 0, "detail": "no compiled content"}

        id_by_email = email_service.map_contacts_by_email(emails_chunk)

        from time import sleep
        with get_connection() as conn:
            for email in emails_chunk:
                processed += 1
                # cooperative pause
                if Campaign.objects.only("status").get(pk=campaign_id).status == CampaignStatus.Paused:
                    redis_service.push_back_front(campaign_id, emails_chunk[processed-1:])
                    break

                contact_id = id_by_email.get(email.lower())
                if not contact_id:
                    continue

                msg = email_service.build_email_message(
                    campaign, email, contact_id, compiled, text_fallback, conn
                )
                if email_service.safe_send(msg, email):
                    sent += 1
                if PER_EMAIL_SLEEP:
                    sleep(PER_EMAIL_SLEEP)

        Campaign.objects.filter(id=campaign_id).update(emails_sent=F("emails_sent") + sent)
        return {"sent": sent, "processed": processed}
    except Campaign.DoesNotExist:
        redis_service.push_back_front(campaign_id, emails_chunk)
        return {"sent": 0, "detail": "campaign gone"}
    finally:
        try:
            redis_service.decr_inflight(campaign_id)
        finally:
            # keep streaming until done/paused
            dispatch_next_chunk.delay(campaign_id)

# ------------- FINALIZE -------------
@shared_task(bind=True, max_retries=3)
def finalize_campaign_send(self, campaign_id: str) -> dict:
    key = recipients_key(campaign_id)
    inflight = inflight_key(campaign_id)
    remaining = r().llen(key)
    infl = int(r().get(inflight) or 0)
    if remaining == 0 and infl == 0:
        with transaction.atomic():
            c = Campaign.objects.select_for_update().get(id=campaign_id)
            if c.status == CampaignStatus.Sending:
                c.mark_sent()
                c.save(update_fields=["status", "completed_at"])
        # clean
        r().delete(key); r().delete(inflight)
        return {"status": "completed"}
    return {"status": "not-done", "remaining": int(remaining), "inflight": infl}
