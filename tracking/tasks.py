# app/tasks.py
import hashlib
from datetime import datetime
from django.utils import timezone as djtz
from campaign.models import Campaign
from celery import shared_task
from django.db import IntegrityError, transaction
from .models import ClickEvent
from django.db.models import F, Value, Case, When
from django.db.models.functions import Greatest
from tracking.models import CampaignLink, CampaignRecipient


def _round_bucket(ts: datetime, secs=5) -> int:
    epoch = int(ts.timestamp())
    return epoch - (epoch % secs)

def _idempotency_key(recipient_id, link_id, occurred_at_iso, bucket_secs=5):
    # Collapse rapid repeats for same recipient+link into one row per bucket
    ts = datetime.fromisoformat(occurred_at_iso)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=djtz.get_current_timezone())
    b = _round_bucket(ts, secs=bucket_secs)
    raw = f"{recipient_id}:{link_id}:{b}".encode()
    return hashlib.sha256(raw).hexdigest()[:64]

@shared_task(bind=True, max_retries=2, default_retry_delay=5,ignore_result=True)
def record_click_event(
    self, *,
    campaign_id, recipient_id, link_id,
    occurred_at, ip_address, user_agent, referrer, source="redirect",
    count=True,
):
    if not count:
        return  # drop obvious bots from metrics
    
    print("count step")
    
    # Normalize occurred_at -> aware datetime
    if isinstance(occurred_at, str):
        # tolerate "…Z" and naive iso strings
        occurred_dt = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    else:
        occurred_dt = occurred_at

    if occurred_dt.tzinfo is None:
        occurred_dt = djtz.make_aware(occurred_dt)

    idem = _idempotency_key(recipient_id, link_id, occurred_dt.isoformat())
    print(f"Idem key: {idem}")
    try:
        with transaction.atomic():
            ClickEvent.objects.create(
                campaign_id=campaign_id,
                recipient_id=recipient_id,   # FK set by id
                link_id=link_id,             # FK set by id
                occurred_at=occurred_dt,
                ip_address=ip_address or None,
                user_agent=user_agent or "",
                referrer=referrer or "",
                source=source,
                idempotency_key=idem,
                metadata={},                 # add any extras if you like
            )
            # --- Campaign-level UNIQUE ---
            cr, created_cr = CampaignRecipient.objects.get_or_create(
                campaign_id=campaign_id,
                recipient_id=recipient_id,
                defaults={"clicks_count": 1, "first_clicked_at": occurred_dt, "last_clicked_at": occurred_dt},
            )
            print(f"created:{created_cr}")
            if created_cr:
                # first-ever click for this recipient in this campaign
                Campaign.objects.filter(id=campaign_id).update(
                    unique_click_count=F("unique_click_count") + 1
                )
                CampaignLink.objects.filter(id=link_id).update(
                    unique_click_count=F("unique_click_count") + 1
                )
            else:
                # subsequent clicks by same recipient in this campaign
                CampaignRecipient.objects.filter(pk=cr.id).update(
                    clicks_count=F("clicks_count") + 1,
                    first_clicked_at=Case(
                        When(first_clicked_at__isnull=True, then=Value(occurred_dt)),
                        default=F("first_clicked_at"),
                    ),
                    last_clicked_at=Greatest(F("last_clicked_at"), Value(occurred_dt)),
                )
            # --- increment per-link counters ---
            CampaignLink.objects.filter(id=link_id).update(
                click_count=F("click_count") + 1,
                first_clicked_at=Case(
                    When(first_clicked_at__isnull=True, then=Value(occurred_dt)),
                    default=F("first_clicked_at"),
                ),
                # Handle NULL safely: if NULL -> occurred_dt, else greatest(existing, occurred_dt)
                last_clicked_at=Case(
                    When(last_clicked_at__isnull=True, then=Value(occurred_dt)),
                    default=Greatest(F("last_clicked_at"), Value(occurred_dt)),
                ),
            )
            # --- increment campaign counters ---
            Campaign.objects.filter(id=campaign_id).update(
                click_count=F("click_count") + 1,
                first_click_at=Case(
                    When(first_click_at__isnull=True, then=Value(occurred_dt)),
                    default=F("first_click_at"),
                ),
                last_click_at=Case(
                    When(last_click_at__isnull=True, then=Value(occurred_dt)),
                    default=Greatest(F("last_click_at"), Value(occurred_dt)),
                ),
            )
        
    except IntegrityError:
        # Duplicate (same recipient+link within bucket); ignore
        return



