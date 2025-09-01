from celery import shared_task, group, chord
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models.functions import Lower
from django.db.models import F
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from email.utils import formataddr
from typing import Union, TypedDict




from campaign.models import Campaign, CampaignStatus, ProviderStatus
from audience.models import Contact
from campaign.services import email_service, exceptions


class ErrorResponse(TypedDict):
    detail: str

class SuccessResponse(TypedDict):
    chunks: int
    task_id: str

CHUNK_SIZE = 35            # tune per your infra
PER_EMAIL_SLEEP = 0.25     # seconds; ~240 emails/hour per chunk task
TASK_RATE = "60/m"         # per-worker rate limit for chunk task


@shared_task(bind=True, max_retries=3)
def kickoff_campaign_send(self, campaign_id: str) -> Union[SuccessResponse, ErrorResponse]:
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
        emails = email_service.distinct_emails(email_service.recipient_qs_for(campaign))
        chunks = [emails[i:i + CHUNK_SIZE] for i in range(0, len(emails), CHUNK_SIZE)]
        g = group(send_campaign_chunk.s(campaign_id, chunk) for chunk in chunks)
        workflow = chord(g)(finalize_campaign_send.s(campaign_id))
    except Campaign.DoesNotExist:
        return {"detail": "Campaign not found"}

    except exceptions.ZeroRecipients:
        return {"detail": "No valid recipients found"}
    
    except Exception as e:
        return {"detail": str(e)}
    
    return {"chunks": len(chunks), "task_id": str(workflow.id)}


@shared_task(bind=True, rate_limit=TASK_RATE, max_retries=3, acks_late=True)
def send_campaign_chunk(self, campaign_id: str, emails_chunk: list[str]) -> int:
    """
    Sends one chunk sequentially. Per-task rate limit throttles each worker.
    """
    campaign = Campaign.objects.get(id=campaign_id)
    compiled, text_fallback = email_service.get_campaign_content(campaign)

    if not compiled:
        return 0

    # Build an email->contact_id map in one query (avoid N lookups)
    id_by_email = email_service.map_contacts_by_email(emails_chunk)
    sent = 0

    with get_connection() as conn:
        for email in emails_chunk:
            contact_id = id_by_email.get(email.lower())
            if not contact_id:
                continue
            msg = email_service.build_email_message(campaign, email, contact_id, compiled, text_fallback, conn)

            if email_service.safe_send(msg, email):
                sent += 1

            if PER_EMAIL_SLEEP:
                from time import sleep
                sleep(PER_EMAIL_SLEEP)

    #atomic increment; avoids stale instance writes
    #Campaign.objects.filter(id=campaign_id).update(emails_sent=F("emails_sent") + sent)
    return sent

@shared_task(bind=True, max_retries=3)
def finalize_campaign_send(self, per_chunk_counts, campaign_id: str):
    total_sent = sum(per_chunk_counts or [])

    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(id=campaign_id)
        campaign.mark_sent()  
        campaign.status = CampaignStatus.Completed
        campaign.completed_at = timezone.now()
        campaign.emails_sent = total_sent
        campaign.save()

    return {"total_sent": total_sent}
