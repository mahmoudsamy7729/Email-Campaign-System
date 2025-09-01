from celery import shared_task, group, chord
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models.functions import Lower
from django.db.models import F
from django.utils import timezone
from django.utils.html import strip_tags
from email.utils import formataddr



from campaign.models import Campaign, CampaignStatus, ProviderStatus
from audience.models import Contact

CHUNK_SIZE = 35            # tune per your infra
PER_EMAIL_SLEEP = 0.25     # seconds; ~240 emails/hour per chunk task
TASK_RATE = "60/m"         # per-worker rate limit for chunk task


def _recipient_qs_for(campaign: Campaign):
    qs = (Contact.objects
          .filter(audience=campaign.audience)
          .exclude(email_address__isnull=True)
          .exclude(email_address__exact=""))
    if campaign.exclude_unsubscribed:
        qs = qs.filter(status="subscribed")   # align with your actual status values
    return qs


def _distinct_emails(qs):
    return (qs.annotate(e=Lower("email_address"))
             .values_list("e", flat=True)
             .distinct())


@shared_task(bind=True, max_retries=3)
def kickoff_campaign_send(self, campaign_id: str):


    print("Starting campaign:", campaign_id)

    campaign = Campaign.objects.get(pk=campaign_id)

    print("Starting campaign:", campaign)

    emails = list(_distinct_emails(_recipient_qs_for(campaign)))
    if not emails:
        return {"detail": "No recipients"}

    chunks = [emails[i:i + CHUNK_SIZE] for i in range(0, len(emails), CHUNK_SIZE)]

    g = group(send_campaign_chunk.s(campaign_id, chunk) for chunk in chunks)
    workflow = chord(g)(finalize_campaign_send.s(campaign_id))
    return {"chunks": len(chunks), "task_id": str(workflow.id)}


@shared_task(bind=True, rate_limit=TASK_RATE, max_retries=3, acks_late=True)
def send_campaign_chunk(self, campaign_id: str, emails_chunk) -> int:
    """
    Sends one chunk sequentially. Per-task rate limit throttles each worker.
    """
    campaign = Campaign.objects.get(id=campaign_id)
    print("Sending chunk for campaign:", campaign)
    compiled = campaign.compiled_html or ""
    print(compiled)
    print("step1 campaign:", campaign)
    if not compiled:
        # ideally call your compile step here or abort
        return 0
    
    # Build an email->contact_id map in one query (avoid N lookups)
    contacts = Contact.objects.filter(email_address__in=emails_chunk).values("id", "email_address")
    id_by_email = {c["email_address"].lower(): str(c["id"]) for c in contacts}

    text_fallback = getattr(campaign, "content_text", "") or strip_tags(compiled)
    print("text_fallback:", text_fallback)
    print("step2 campaign:", campaign)


    sent = 0
    with get_connection() as conn:
        for email in emails_chunk:
            contact_id = id_by_email.get(email.lower())
            print("Sending email to:", email, "Contact ID:", contact_id)
            html_for_recipient = compiled.replace("?r={recipient_id}", f"?r={contact_id}")
            print(formataddr((campaign.from_name, campaign.from_email)))
            msg = EmailMultiAlternatives(
                subject=campaign.subject_line,
                body=text_fallback,
                from_email=formataddr((campaign.from_name, campaign.from_email)),
                to=[email],
                connection=conn,
                headers=({"Reply-To": campaign.reply_to} if campaign.reply_to else None),
            )
            print("msg:", msg)
            msg.attach_alternative(html_for_recipient, "text/html")  # HTML part
            try:
                msg.send(fail_silently=False)
                sent += 1
            except Exception as e:
                print(f"خطأ في إرسال الإيميل إلى {email}: {e}")
                # Optionally log; continue
                pass

            if PER_EMAIL_SLEEP:
                from time import sleep
                sleep(PER_EMAIL_SLEEP)

    # atomic increment; avoids stale instance writes
    #Campaign.objects.filter(id=campaign_id).update(emails_sent=F("emails_sent") + sent)
    return sent


@shared_task(bind=True, max_retries=3)
def finalize_campaign_send(self, per_chunk_counts, campaign_id: str):
    total_sent = sum(per_chunk_counts or [])

    campaign = Campaign.objects.get(id=campaign_id)
    print("Finalizing campaign:", campaign)
    campaign.mark_sent()
    updated = Campaign.objects.filter(id=campaign_id).update(
        status=CampaignStatus.Completed,
        completed_at=timezone.now(),
        emails_sent=total_sent,
    )
    print("Finalize update count:", updated)

    # Single atomic UPDATE to avoid stale-instance overwrite
    #Campaign.objects.filter(id=campaign_id).update(
    #    emails_sent= 20,
        #status=CampaignStatus.Completed,
        #completed_at=timezone.now(),
        #provider_status=ProviderStatus.COMPLETED,
    #)
    print("Campaign finalized:", campaign_id, "sent:", total_sent)
    return {"total_sent": total_sent}
