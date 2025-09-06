from django.db import models
from django.utils import timezone
import uuid

# Create your models here.

class Kind(models.TextChoices):
    Regular = "regular", "Regular"
    RSS = "rss", "RSS"
    Automated = "automated", "Automated"

class CampaignStatus(models.TextChoices):
    Draft = "draft", "Draft"
    Scheduled = "scheduled", "Scheduled"
    Sending = "sending", "Sending"
    Completed = "completed", "Completed"
    Canceled = "canceled", "Canceled"
    Failed = "failed", "Failed"
    Paused = "paused", "Paused"


class ScheduleType(models.TextChoices):
    Immediate = "immediate", "Immediate"
    Scheduled = "scheduled", "Scheduled"

class ProviderStatus(models.TextChoices):
    NONE = "none", "None"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    ERROR = "error", "Error"
    
class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default="regular")
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default="draft", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    audience = models.ForeignKey('audience.Audience', on_delete=models.CASCADE, related_name='campaigns', db_index=True)
    #segment_name = models.CharField(max_length=200, blank=True, default="")
    #segment_filter_json = models.JSONField(default=dict, blank=True)
    #include_tags = models.JSONField(default=list, blank=True)         # store tag UUIDs or names as strings
    #exclude_tags = models.JSONField(default=list, blank=True)
    estimated_recipients = models.PositiveIntegerField(default=0)
    exclude_unsubscribed = models.BooleanField(default=True)
    #suppress_list_ids = models.JSONField(default=list, blank=True)


    subject_line = models.CharField(max_length=255)
    preview_text = models.TextField(max_length=255, blank=True, default="")
    from_name = models.CharField(max_length=120)
    from_email = models.EmailField()
    reply_to = models.EmailField(blank=True, default="")
    to_name_format = models.CharField(max_length=120, blank=True, default="")  # e.g. "{{first_name}}"

    #template = models.CharField(max_length=120, blank=True, default="")  # or FK to a Template model if you add one
    content_html = models.TextField(blank=True, default="")
    content_text = models.TextField(blank=True, default="")
    #editor_json = models.JSONField(default=dict, blank=True)
    #inline_css = models.BooleanField(default=True)
    #auto_footer = models.BooleanField(default=True)
    #web_version_enabled = models.BooleanField(default=True)
    #permalink_slug = models.SlugField(max_length=220, blank=True, default="", help_text="Public archive slug")

    schedule_type = models.CharField(max_length=20, choices=ScheduleType.choices, default="immediate")
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    #timezone_str = models.CharField(max_length=64, default="UTC")
    #per_recipient_local_time = models.BooleanField(default=False)
    #resend_to_non_openers_after_hours = models.PositiveIntegerField(null=True, blank=True)

    # Tracking & analytics
    #track_opens = models.BooleanField(default=True)
    #track_clicks = models.BooleanField(default=True)
    #track_google_analytics = models.BooleanField(default=False)
    #utm_source = models.CharField(max_length=100, blank=True, default="")
    #utm_medium = models.CharField(max_length=100, blank=True, default="")
    #utm_campaign = models.CharField(max_length=100, blank=True, default="")
    #utm_term = models.CharField(max_length=100, blank=True, default="")
    #utm_content = models.CharField(max_length=100, blank=True, default="")

    # Delivery settings / infrastructure
    #provider = models.CharField(max_length=50, blank=True, default="")  # e.g., "ses", "sendgrid", "smtp"
    #provider_campaign_id = models.CharField(max_length=120, blank=True, default="")
    #envelope_sender = models.EmailField(blank=True, default="")
    #dkim_domain = models.CharField(max_length=255, blank=True, default="")
    #dkim_selector = models.CharField(max_length=63, blank=True, default="")
    #spf_domain = models.CharField(max_length=255, blank=True, default="")
    #throttle_per_minute = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    #batch_size = models.PositiveIntegerField(default=1000)
    #max_retries = models.PositiveIntegerField(default=3)

    # Runtime status (system-filled)
    send_job_id = models.CharField(max_length=120, blank=True, default="")
    started_sending_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    emails_sent = models.PositiveIntegerField(default=0)
    #provider_status = models.CharField(max_length=20, choices=ProviderStatus.choices, default=ProviderStatus.NONE, db_index=True)
    #last_error_message = models.TextField(blank=True, default="")

    # Metrics (denormalized rollups)
    #delivered_count = models.PositiveIntegerField(default=0)
    #hard_bounce_count = models.PositiveIntegerField(default=0)
    #soft_bounce_count = models.PositiveIntegerField(default=0)
    #open_count = models.PositiveIntegerField(default=0)
    #unique_open_count = models.PositiveIntegerField(default=0)
    #open_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)   # percent
    click_count = models.PositiveIntegerField(default=0)
    unique_click_count = models.PositiveIntegerField(default=0)
    click_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # percent
    first_click_at = models.DateTimeField(null=True, blank=True)
    last_click_at = models.DateTimeField(null=True, blank=True)
    #unsub_count = models.PositiveIntegerField(default=0)
    #spam_complaint_count = models.PositiveIntegerField(default=0)

    # Content & compiled version
    content_html = models.TextField(blank=True, default="")
    compiled_html = models.TextField(blank=True, default="")
    compiled_at = models.DateTimeField(null=True, blank=True)

    # Fingerprint of the distinct URLs found in content_html (SHA-256 hex = 64 chars)
    linkset_fingerprint = models.CharField(max_length=64, blank=True, default="")

    # A/B (optional)
    #ab_enabled = models.BooleanField(default=False)
    #ab_criterion = models.CharField(max_length=40, blank=True, default="")   # subject | from_name | send_time | content
    #ab_split_percent = models.PositiveSmallIntegerField(default=50)
    #ab_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    #ab_winner_metric = models.CharField(max_length=40, blank=True, default="")  # open_rate | click_rate | revenue
    #ab_variant_a_subject = models.CharField(max_length=255, blank=True, default="")
    #ab_variant_b_subject = models.CharField(max_length=255, blank=True, default="")
    #ab_winner = models.CharField(max_length=1, blank=True, default="")  # "A" | "B" | ""

    # Social card
    #social_title = models.CharField(max_length=120, blank=True, default="")
    #social_description = models.CharField(max_length=200, blank=True, default="")
    #social_image_url = models.URLField(blank=True, default="")

    # Compliance
    #include_mailing_address = models.BooleanField(default=True)
    #include_unsubscribe_link = models.BooleanField(default=True)
    #gdpr_note = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            #models.Index(fields=["provider_status"]),
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["audience", "status", "kind"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"
    
    @property
    def is_schedulable(self) -> bool:
        if self.schedule_type == ScheduleType.Scheduled and not self.scheduled_at:
            return False
        return self.status in {CampaignStatus.Draft, CampaignStatus.Scheduled}
    
    def schedule_now(self):
        self.schedule_type = ScheduleType.Immediate
        self.scheduled_at = timezone.now()
        self.status = CampaignStatus.Scheduled

    def mark_sending(self):
        self.status = CampaignStatus.Sending
        self.started_sending_at = timezone.now()
        #self.provider_status = ProviderStatus.RUNNING

    def mark_sent(self):
        self.status = CampaignStatus.Completed
        self.completed_at = timezone.now()
        #self.provider_status = ProviderStatus.COMPLETED

    def mark_paused(self):
        self.status = CampaignStatus.Paused

