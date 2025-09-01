# campaign/serializers.py
from django.db.models.functions import Lower
from rest_framework import serializers
from .models import Campaign, CampaignStatus, ScheduleType
from audience.models import Contact


class CampaignSerializer(serializers.ModelSerializer):
    audience_name = serializers.CharField(source="audience.name", read_only=True)

    class Meta:
        model = Campaign
        fields = "__all__"
        read_only_fields = ["created_at","updated_at","emails_sent",
                            "started_sending_at","completed_at",
                            "send_job_id","estimated_recipients","status"]

    def _estimate(self, campaign: Campaign) -> int:
        qs = (Contact.objects
              .filter(audience=campaign.audience)
              .exclude(email_address__isnull=True)
              .exclude(email_address__exact=""))
        if campaign.exclude_unsubscribed:
            qs = qs.filter(status="subscribed")

        return (qs.annotate(e=Lower("email_address"))
                 .values("e").distinct().count())
    
    def validate(self, attrs):
        inst = getattr(self, "instance", None)
        if inst and inst.status in {CampaignStatus.Sending, CampaignStatus.Completed}:
            # choose which fields to lock after sending starts
            locked_fields = {"title", "audience", "content_html", "content_text", "from_name", "from_email"}
            if locked_fields & set(attrs.keys()):
                raise serializers.ValidationError("Cannot edit this campaign after sending has started.")
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["status"] = CampaignStatus.Draft
        validated_data.setdefault("schedule_type", ScheduleType.Immediate)
        campaign = super().create(validated_data)
        campaign.estimated_recipients = self._estimate(campaign)
        campaign.save(update_fields=["estimated_recipients"])
        return campaign

    def update(self, instance, validated_data):
        print(validated_data)
        old_audience = instance.audience
        old_excl = instance.exclude_unsubscribed
        campaign = super().update(instance, validated_data)
        if campaign.audience != old_audience or campaign.exclude_unsubscribed != old_excl:
            campaign.estimated_recipients = self._estimate(campaign)
            campaign.save(update_fields=["estimated_recipients"])
        return campaign
