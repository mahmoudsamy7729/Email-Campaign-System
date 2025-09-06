from typing import Mapping, Any, Dict, TypedDict, Optional, Type
from django.conf import settings
from django.db import transaction
from django.core.mail import EmailMultiAlternatives
from email.utils import formataddr

from rest_framework.serializers import Serializer

from campaign.models import Campaign, CampaignStatus
from campaign.tasks import kickoff_campaign_send
from campaign.services import exceptions
from tracking import link_compiler
from campaign.models import Campaign
from audience.models import Contact
from django.db.models.functions import Lower
from . import email_service
from campaign.tasks import dispatch_next_chunk



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
    print('Building payload')

    if compile_result:
        payload.update({
            "links_count": compile_result.get("links_count", 0),
            "links": compile_result.get("links", []),
            "compiled_html": compile_result.get("compiled_html", ""),
        })
    print ("finished")
    return payload


def validate_send_or_raise(campaign: Campaign) -> None:
    if campaign.status not in {CampaignStatus.Draft, CampaignStatus.Scheduled}:
        raise exceptions.InvalidState(f"Campaign already {campaign.status}.")
    if campaign.estimated_recipients == 0:
        raise exceptions.ZeroRecipients("Estimated recipients is 0.")
    return None


def send_campaign(*, campaign_id: str | None) -> SendResult:
        # Lock row to avoid double-send races under concurrent requests
        campaign = Campaign.objects.select_for_update().get(pk=campaign_id)
        validate_send_or_raise(campaign)
        options = {}
        if campaign.scheduled_at:
            options["eta"] = campaign.scheduled_at
        task = kickoff_campaign_send.apply_async(args=[str(campaign.id)], **options)
        return {"task_id": str(task.id)}

def send_test_email(*, campaign_id: str | None, test_email: Optional[str]) -> dict :
    campaign = Campaign.objects.get(pk=campaign_id)
    compiled, text_fallback = email_service.get_campaign_content(campaign)
    html_for_recipient = compiled.replace("?r={recipient_id}", f"?r=")
    if not test_email:
         test_email = "mahmoud.samy7729@gmail.com"
    msg = EmailMultiAlternatives(
        subject=campaign.subject_line,
        body=text_fallback,
        from_email=formataddr((campaign.from_name, campaign.from_email)),
        to=[test_email],
        reply_to = [campaign.reply_to] if getattr(campaign, "reply_to", None) else None
    )
    msg.attach_alternative(html_for_recipient, "text/html")
    msg.send(fail_silently=False)
    return {"sent_to": test_email}

def update_campaign(pk: str | None , validated_data: Dict[str, Any], viewset_get_queryset, serializer_class: Type[Serializer]) -> None:
    campaign = (
            viewset_get_queryset()
            .select_for_update(nowait=True)
            .get(pk=pk)
        )
    old_html = campaign.content_html
    compile_result: Dict = {}
    serializer = serializer_class(campaign, data=validated_data, partial=True)
    serializer.is_valid(raise_exception=True)
    campaign = serializer.save()
    if should_compile(campaign, serializer.validated_data, True, old_html):
        compile_result = compile_links(campaign)
    rep = serializer.to_representation(campaign)  
    print('Update Campaign',compile_result)
    build_payload(rep, campaign, compile_result)  
    return None
    

def pause_campaign(campaign_id: str | None) -> dict:
    with transaction.atomic():
        c = Campaign.objects.select_for_update().get(pk=campaign_id)
        if c.status == CampaignStatus.Completed:
            return {"detail": "Already completed"}
        c.mark_paused()
        c.save(update_fields=["status"])
    return {"detail": "Paused"}


def resume_campaign(campaign_id: str | None) -> dict:
    with transaction.atomic():
        c = Campaign.objects.select_for_update().get(pk=campaign_id)
        if c.status == CampaignStatus.Completed:
            return {"detail": "Already completed"}
        c.mark_sending()
        c.save(update_fields=["status", "started_sending_at"])
    # kick dispatcher to continue
    dispatch_next_chunk.delay(campaign_id)
    return {"detail": "Resumed"}
    