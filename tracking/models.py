from django.db import models
import uuid
from django.db.models import Q
from django.utils import timezone

from campaign.models import Campaign
from audience.models import Contact

# Create your models here.

class CampaignLink(models.Model):
    """
    One row per distinct URL inside a specific campaign.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="links")
    original_url = models.URLField()
    # Token used in tracking URLs, e.g., https://t.example.com/c/<token>
    token = models.CharField(max_length=64, unique=True, db_index=True)

    # Lightweight aggregates (clicks only) per link
    click_count = models.PositiveIntegerField(default=0)
    unique_click_count = models.PositiveIntegerField(default=0)
    first_clicked_at = models.DateTimeField(null=True, blank=True)
    last_clicked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["campaign"]),
            models.Index(fields=["token"]),
        ]

    def __str__(self):
        return f"{self.campaign.id} → {self.original_url}"
    

class CampaignRecipient(models.Model):
    """
    Join row for a recipient targeted by a campaign.
    Stores per-recipient click summary (no send/open fields in this MVP).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipients")
    recipient = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="campaign_memberships")

    # Click summary for this recipient within this campaign
    clicks_count = models.PositiveIntegerField(default=0)
    first_clicked_at = models.DateTimeField(null=True, blank=True)
    last_clicked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["campaign", "recipient"], name="uniq_campaign_recipient"),
        ]
        indexes = [
            models.Index(fields=["campaign", "recipient"]),
            models.Index(fields=["recipient"]),
        ]

    def __str__(self):
        return f"{self.campaign.id} · {self.recipient.id}"
    
class ClickEvent(models.Model):
    """
    Append-only raw click events (source of truth).
    """
    class Source(models.TextChoices):
        REDIRECT = "redirect", "Redirect"   # your /c/<token> endpoint
        WEBHOOK = "webhook", "Webhook"      # if you ever ingest from ESP/webhook
        TEST    = "test", "Test"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="click_events")
    recipient = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="click_events")
    link = models.ForeignKey(CampaignLink, on_delete=models.CASCADE, related_name="click_events")

    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Optional debugging / bot-filtering aids
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    referrer = models.TextField(blank=True, default="")
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.REDIRECT)

    # Idempotency/dedupe key (e.g., hash of recipient+link+rounded_timestamp)
    idempotency_key = models.CharField(max_length=128, unique=True, null=True, blank=True)

    # Free-form extras; safe for SQLite and Postgres via Django JSONField
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["campaign", "occurred_at"]),
            models.Index(fields=["link", "occurred_at"]),
            models.Index(fields=["recipient", "occurred_at"]),
        ]
        # Ensure idempotency_key is unique when present (allows multiple NULLs)
        

    def __str__(self):
        return f"click {self.id} · camp={self.campaign.id} · rec={self.recipient.id} · link={self.link.id}"
    


