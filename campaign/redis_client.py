from django_redis import get_redis_connection
import uuid, time
from contextlib import contextmanager


@contextmanager
def redis_lock(name: str, ttl: int = 15):
    k = f"lock:{name}"
    v = str(uuid.uuid4())
    conn = r()
    acquired = conn.set(k, v, nx=True, ex=ttl)
    try:
        if not acquired:
            yield False
        else:
            yield True
    finally:
        # best-effort release
        try:
            if conn.get(k) == v.encode():
                conn.delete(k)
        except Exception:
            pass


def r():
    # default cache alias; adjust if needed
    return get_redis_connection("default")