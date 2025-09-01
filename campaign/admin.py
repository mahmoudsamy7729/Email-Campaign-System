# campaign/admin.py
from django.contrib import admin
from django.db.models.functions import Lower

from .models import Campaign, CampaignStatus
from audience.models import Contact
from .tasks import kickoff_campaign_send


def _estimate_for_campaign(campaign: Campaign) -> int:
    qs = (
        Contact.objects
        .filter(audience=campaign.audience)
        .exclude(email_address__isnull=True)
        .exclude(email_address__exact="")
    )
    if campaign.exclude_unsubscribed:
        qs = qs.filter(status="subscribed")  # adjust to your status names
    return (
        qs.annotate(e=Lower("email_address"))
          .values("e").distinct().count()
    )


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "title", "audience", "status", 
        "estimated_recipients", "emails_sent", "created_at",
    )
    list_filter = (
        "status", "exclude_unsubscribed",
        "audience", "created_at",
    )
    search_fields = ("title", "subject_line", "from_email", "from_name")
    date_hierarchy = "created_at"

    # You can edit most fields; keep runtime ones read-only
    readonly_fields = (
        "id", "created_at", "updated_at",
        "started_sending_at", "completed_at",
        "send_job_id", 
        "emails_sent", "estimated_recipients",
    )

    fieldsets = (
        ("Basics", {
            "fields": ("title", "kind", "audience", "status"),
        }),
        ("Message", {
            "fields": ("subject_line", "preview_text", "from_name",
                       "from_email", "reply_to", "to_name_format", "content_text"),
        }),
        ("Sending", {
            "fields": ("schedule_type", "scheduled_at",
                       "exclude_unsubscribed", "estimated_recipients"),
        }),
        ("Runtime", {
            "fields": ("send_job_id",
                       "emails_sent", "started_sending_at", "completed_at"),
        }),
        ("Meta", {
            "fields": ("id", "created_at", "updated_at"),
        }),
    )

    actions = ["recalculate_estimated_recipients", "send_now"]

    def recalculate_estimated_recipients(self, request, queryset):
        updated = 0
        for campaign in queryset:
            estimate = _estimate_for_campaign(campaign)
            if estimate != campaign.estimated_recipients:
                Campaign.objects.filter(pk=campaign.pk).update(
                    estimated_recipients=estimate
                )
                updated += 1
        self.message_user(request, f"Recalculated estimate for {updated} campaign(s).")
    recalculate_estimated_recipients.short_description = "Recalculate estimated recipients"

    def send_now(self, request, queryset):
        started = 0
        for campaign in queryset:
            # Only start from Draft/Scheduled and if there’s someone to send to
            if campaign.status in {CampaignStatus.Draft, CampaignStatus.Scheduled} and campaign.estimated_recipients > 0:
                campaign.mark_sending()
                campaign.save(update_fields=["status", "started_sending_at"])
                kickoff_campaign_send.delay(str(campaign.id))
                started += 1
        self.message_user(request, f"Started sending for {started} campaign(s).")
    send_now.short_description = "Send now (enqueue Celery tasks)"
