class DomainError(Exception):
    """Base domain error."""

class InvalidState(DomainError):
    """Invalid state transition (409)."""

class ZeroRecipients(DomainError):
    """No recipients to send to (400)."""