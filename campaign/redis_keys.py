def recipients_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:recipients"

def inflight_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:inflight"

def lock_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:lock"