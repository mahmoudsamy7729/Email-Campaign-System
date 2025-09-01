from typing import Mapping, Any, Dict, TypedDict, Optional
from django.conf import settings
from django.db import transaction

from rest_framework.response import Response
from rest_framework import status

from campaign.models import Campaign, CampaignStatus
from campaign.serializers import CampaignSerializer
from campaign.tasks import kickoff_campaign_send
from campaign.services import exceptions
from tracking import link_compiler
from campaign.models import Campaign
from audience.models import Contact
from django.db.models.functions import Lower


class SendResult(TypedDict):
    task_id: str


def estimate_recipients(campaign: Campaign) -> int:
        qs = (Contact.objects
              .filter(audience=campaign.audience)
              .exclude(email_address__isnull=True)
              .exclude(email_address__exact=""))
        if campaign.exclude_unsubscribed:
            qs = qs.filter(status="subscribed")

        return (qs.annotate(e=Lower("email_address"))
                 .values("e").distinct().count())


def _tracking_base() -> str:
    base = getattr(settings, "TRACKING_BASE_URL", None)
    if not base:
        raise RuntimeError("TRACKING_BASE_URL is not configured.")
    return base

def compile_links(campaign: Campaign) -> Dict:
        return link_compiler.compile_links_for_campaign(
            campaign=campaign,
            tracking_base= _tracking_base(),
        )

def should_compile(campaign: Campaign, validated: Dict, force: bool, old_html: Optional[str] = None) -> bool:
        """
        Compile if:
          - campaign has HTML after save AND
          - (content_html changed) OR (force is True)
        """
        if not campaign.content_html:
            return False
        
        if force or getattr(campaign, "compiled_at", None) is None:
            return True
        
        if "content_html" in validated:
            if old_html is not None:
                return validated["content_html"] != old_html
            return True
        return False

def build_payload(rep: Dict[str, Any], 
                  campaign: Campaign, 
                  compile_result: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    payload = {**rep}
    if "compiled_at" not in payload:
        compiled_at = getattr(campaign, "compiled_at", None)
    if compile_result:
        payload.update({
            "links_count": compile_result.get("links_count", 0),
            "links": compile_result.get("links", []),
            "compiled_html": compile_result.get("compiled_html", ""),
        })
    return payload


def validate_send_or_raise(campaign: Campaign) -> None:
    if campaign.status not in {CampaignStatus.Draft, CampaignStatus.Scheduled}:
        # 409 fits "invalid state transition"
        raise exceptions.InvalidState(f"Campaign already {campaign.status}.")
    if campaign.estimated_recipients == 0:
        raise exceptions.ZeroRecipients("Estimated recipients is 0.")
    return None


def send_campaign(*, campaign_id: str | None) -> SendResult:
        # Lock row to avoid double-send races under concurrent requests
        with transaction.atomic():
            campaign = Campaign.objects.select_for_update().get(pk=campaign_id)

            validate_send_or_raise(campaign)

            campaign.mark_sending()
            campaign.save(update_fields=["status", "started_sending_at"])

        task = kickoff_campaign_send.delay(str(campaign.id))
        return {"task_id": str(task.id)}
