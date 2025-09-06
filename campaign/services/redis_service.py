from __future__ import annotations
from contextlib import contextmanager
from typing import List
import uuid
from django_redis import get_redis_connection

# ------------ Keys ------------
def recipients_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:recipients"

def inflight_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:inflight"

def lock_key(campaign_id: str) -> str:
    return f"campaign:{campaign_id}:lock"

# ------------ Conn ------------
def conn():
    return get_redis_connection("default")

# ------------ Lock ------------
@contextmanager
def redis_lock(name: str, ttl: int = 15):
    k = f"lock:{name}"
    v = str(uuid.uuid4())
    c = conn()
    acquired = c.set(k, v, nx=True, ex=ttl)
    try:
        yield bool(acquired)
    finally:
        try:
            if c.get(k) == (v.encode()):
                c.delete(k)
        except Exception:
            pass

# ------------ State ops ------------
def init_state(campaign_id: str, emails: List[str]) -> None:
    c = conn()
    rk, ik = recipients_key(campaign_id), inflight_key(campaign_id)
    p = c.pipeline()
    p.delete(rk)
    p.delete(ik)
    if emails:
        p.rpush(rk, *emails)
    p.set(ik, 0)
    p.execute()

def cleanup(campaign_id: str) -> None:
    c = conn()
    c.delete(recipients_key(campaign_id))
    c.delete(inflight_key(campaign_id))

def queue_len(campaign_id: str) -> int:
    return int(conn().llen(recipients_key(campaign_id)))

def get_inflight(campaign_id: str) -> int:
    raw = conn().get(inflight_key(campaign_id)) or b"0"
    return int(raw if isinstance(raw, bytes) else str(raw))

def incr_inflight(campaign_id: str) -> int:
    return int(conn().incr(inflight_key(campaign_id)))

def decr_inflight(campaign_id: str) -> int:
    c = conn()
    nv = int(c.decr(inflight_key(campaign_id)))
    if nv < 0:
        c.set(inflight_key(campaign_id), 0)
        nv = 0
    return nv

def pop_chunk(campaign_id: str, chunk_size: int) -> List[str]:
    """
    Atomically pop up to chunk_size from the head.
    Uses LPOP count if available; falls back to LRANGE+LTRIM.
    """
    c = conn()
    try:
        vals = c.lpop(recipients_key(campaign_id), chunk_size) or []
        if isinstance(vals, (bytes, str)):  # single item case
            vals = [vals]
    except TypeError:
        # redis-py without LPOP count
        p = c.pipeline()
        p.lrange(recipients_key(campaign_id), 0, chunk_size - 1)
        p.ltrim(recipients_key(campaign_id), chunk_size, -1)
        vals, _ = p.execute()

    return [v.decode() if isinstance(v, bytes) else v for v in (vals or [])]

def push_back_front(campaign_id: str, emails: List[str]) -> None:
    """Push remainder back to the front preserving order."""
    if not emails:
        return
    c = conn()
    c.lpush(recipients_key(campaign_id), *list(reversed(emails)))