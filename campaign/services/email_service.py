from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models.functions import Lower
from django.db.models import F, QuerySet
from django.utils import timezone
from django.utils.html import strip_tags
from email.utils import formataddr
from typing import Iterable


from campaign.models import Campaign, CampaignStatus, ProviderStatus
from audience.models import Contact
from campaign.services import exceptions


def recipient_qs_for(campaign: Campaign) -> QuerySet[Contact]:
    qs = (Contact.objects
          .filter(audience=campaign.audience)
          .exclude(email_address__isnull=True)
          .exclude(email_address__exact=""))
    if campaign.exclude_unsubscribed:
        qs = qs.filter(status="subscribed")   # align with your actual status values
    return qs


def distinct_emails(qs: QuerySet[Contact]) -> list[str]:
    emails = list(qs.annotate(e=Lower("email_address"))
             .values_list("e", flat=True)
             .distinct())
    if not emails:
        raise exceptions.ZeroRecipients("No valid recipient emails found")
    return emails


def get_campaign_content(campaign: Campaign) -> tuple[str, str]:
    compiled = campaign.compiled_html or ""
    text_fallback = getattr(campaign, "content_text", "") or strip_tags(compiled)
    return compiled, text_fallback

def map_contacts_by_email(emails: list[str]) -> dict[str, str]:
    contacts = Contact.objects.filter(email_address__in=emails).values("id", "email_address")
    return {c["email_address"].lower(): str(c["id"]) for c in contacts}

def build_email_message(campaign: Campaign, email: str, contact_id: str, html: str, text_fallback: str, conn) -> EmailMultiAlternatives:
    html_for_recipient = html.replace("?r={recipient_id}", f"?r={contact_id}")
    msg = EmailMultiAlternatives(
        subject=campaign.subject_line,
        body=text_fallback,
        from_email=formataddr((campaign.from_name, campaign.from_email)),
        to=[email],
        connection=conn,
        headers=({"Reply-To": campaign.reply_to} if campaign.reply_to else None),
    )
    msg.attach_alternative(html_for_recipient, "text/html")
    return msg

def safe_send(msg, email: str) -> bool:
    try:
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"{email}: {e}")
        return False
