from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import timezone
from django.core.cache import cache
from .models import CampaignLink
from .tasks import record_click_event
from django.conf import settings

# ---- Config (override in settings.py if you like) ----
TRACKING_LINK_CACHE_TTL = getattr(settings, "TRACKING_LINK_CACHE_TTL")  
TRACKING_DEDUPE_TTL = getattr(settings, "TRACKING_DEDUPE_TTL")               
TRACKING_BOT_UA = getattr(settings,"TRACKING_BOT_UA")



def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")

def _is_probable_bot(request):
    print(TRACKING_BOT_UA)
    if request.method != "GET":
        return True
    ua = (request.META.get("HTTP_USER_AGENT") or "")
    if not ua or len(ua) < 12:
        return True
    ual = ua.lower()
    return any(s in ual for s in TRACKING_BOT_UA)

def click_redirect(request, token: str):
    cache_key = f"link:{token}"
    payload = cache.get(cache_key)
    if payload is None:
        try:
            link = CampaignLink.objects.only("id","original_url","campaign_id").get(token=token)
        except CampaignLink.DoesNotExist:
            return HttpResponseBadRequest("Invalid link")
        payload = {"u": link.original_url, "l": str(link.id), "c": str(link.campaign.id)}
        cache.set(cache_key, payload, timeout=TRACKING_LINK_CACHE_TTL)  # 24h

    target = payload["u"]
    recipient_id = request.GET.get("r")
    
    if not recipient_id:
        # Still redirect, just don’t log (your model requires recipient)
        return HttpResponseRedirect(target)

    
    ip = _client_ip(request)
    dedupe_key = f"d:{recipient_id}:{payload['l']}"

    # Light dedupe for burst double-clicks (5s window)
    print("dddd")
    print(not _is_probable_bot(request))
    if cache.add(dedupe_key, 1, timeout=TRACKING_DEDUPE_TTL):
        record_click_event.delay(
            campaign_id=payload["c"],
            recipient_id=recipient_id,
            link_id=payload["l"],
            occurred_at=timezone.now().isoformat(),
            ip_address=ip,
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:512],
            referrer=(request.META.get("HTTP_REFERER") or "")[:512],
            source="redirect",
            count=not _is_probable_bot(request),
        )
    # Instant 302 to destination
    return HttpResponseRedirect(target)
