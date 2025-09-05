from django.db.models.functions import Lower
from rest_framework import serializers
from .models import Campaign, CampaignStatus, ScheduleType
from audience.models import Contact
from campaign.services import campaigns


class CampaignSerializer(serializers.ModelSerializer):
    audience_name = serializers.CharField(source="audience.name", read_only=True)
    test_email = serializers.EmailField(write_only=True, required=False)

    class Meta:
        model = Campaign
        fields = "__all__"
        read_only_fields = ["created_at","updated_at","emails_sent",
                            "started_sending_at","completed_at",
                            "send_job_id","estimated_recipients","status"]

   
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
        campaign.estimated_recipients = campaigns.estimate_recipients(campaign)
        campaign.save(update_fields=["estimated_recipients"])
        return campaign

    def update(self, instance, validated_data):
        old_audience = instance.audience
        old_excl = instance.exclude_unsubscribed
        if "schedule_type" in validated_data and validated_data["schedule_type"] == ScheduleType.Immediate:
            validated_data["scheduled_at"] = None
        if validated_data["schedule_type"] == ScheduleType.Scheduled:
            validated_data["status"] = CampaignStatus.Scheduled
        campaign = super().update(instance, validated_data)
        if campaign.audience != old_audience or campaign.exclude_unsubscribed != old_excl:
            campaign.estimated_recipients = campaigns.estimate_recipients(campaign)
            campaign.save(update_fields=["estimated_recipients"])
        return campaign
