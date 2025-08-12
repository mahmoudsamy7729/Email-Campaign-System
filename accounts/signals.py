from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
import logging
log = logging.getLogger("accounts")

def _ip(r): return r.META.get("HTTP_X_FORWARDED_FOR", r.META.get("REMOTE_ADDR"))

@receiver(user_logged_in)
def logged_in(sender, request, user, **kw):
    log.info("login ok user=%s ip=%s", user.id, _ip(request))

@receiver(user_logged_out)
def logged_out(sender, request, user, **kw): 
    log.info("logout user=%s ip=%s", getattr(user,"id",None), _ip(request))

@receiver(user_login_failed)
def login_failed(sender, credentials, request, **kw): 
    log.warning("login failed email=%s ip=%s", credentials.get("email"), _ip(request))
