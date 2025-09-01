import hashlib, secrets, string
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from django.utils import timezone
from .models import CampaignLink
import markdown


ALPHABET = string.ascii_letters + string.digits


def generate_token(n: int = 22) -> str:
    # Short, URL-safe, no punctuation
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def is_trackable_href(href: str) -> bool:
    if not href:
        return False
    href = href.strip()
    print("href to check:", href)
    if href.startswith("#"):
        return False
    low = href.lower()
    print("low:", low)
    # Track only http/https
    if not (low.startswith("http://") or low.startswith("https://")):
        return False
    # Don’t wrap unsubscribe or mail/tel
    if low.startswith("mailto:") or low.startswith("tel:"):
        return False
    if "unsubscribe" in low:
        return False
    return True


def normalize_url(url: str) -> str:
    """Basic normalization: trim + keep as-is (MVP)."""
    print("Normalizing URL:", url.strip())
    return url.strip()

def fingerprint_url_list(urls: list[str]) -> str:
    joined = "\n".join(sorted(urls))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def compile_links_for_campaign(*, campaign, tracking_base: str) -> dict:
    """
    Parses campaign.content_html, upserts CampaignLink rows,
    replaces hrefs with tracking URLs, saves compiled_html/compiled_at/fingerprint.
    Returns {links, links_count, compiled_html}.
    """
    html = campaign.content_html or ""
    compiled_html = markdown.markdown(html) if html else None
    print("Compiling links for campaign:", compiled_html)
    soup = BeautifulSoup(str(compiled_html), "html.parser")
    
    seen = {}  # normalized_url -> token

    anchors = soup.find_all("a", href=True)
    for a in anchors:
        href = a.get("href")
        if not is_trackable_href(href):
            continue

        norm = normalize_url(href)
        # One link row per (campaign, url)
        link, created = CampaignLink.objects.get_or_create(
            campaign=campaign,
            original_url=norm,
            defaults={"token": generate_token()},
        )
        seen[norm] = link.token

        # Build tracking URL with recipient placeholder (fill at send time)
        # Example: https://t.example.com/c/<token>?r={recipient_id}
        tracking_url = f"{tracking_base.rstrip('/')}/c/{link.token}?r={{recipient_id}}"
        print("tracking url:", tracking_url)
        a["href"] = tracking_url  # keep other attributes intact

    campaign.compiled_html = str(soup)
    campaign.compiled_at = timezone.now()
    campaign.linkset_fingerprint = fingerprint_url_list(list(seen.keys()))
    campaign.save(update_fields=["compiled_html", "compiled_at", "linkset_fingerprint"])

    return {
        "links": [{"original_url": u, "token": t} for u, t in seen.items()],
        "links_count": len(seen),
        "compiled_html": compiled_html,
    }