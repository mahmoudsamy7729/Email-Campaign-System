from django.db import models
from django.utils import timezone
import uuid


# Create your models here.
class Status(models.TextChoices):
    SUBSCRIBED = "subscribed", "Subscribed"
    UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
    CLEANED = "cleaned", "Cleaned"           # invalid/hard-bounced
    PENDING = "Pending", "Pending"


class Source(models.TextChoices):
    IMPORT = "import", "Import"
    FORM = "form", "Form"
    API = "api", "API"
    MANUAL = "manual", "Manual"


class Audience(models.Model):
    """Audience List (list)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
    
class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    audience = models.ForeignKey(Audience, on_delete=models.CASCADE, related_name='contacts')

    email_address = models.EmailField()

    
    status = models.CharField(max_length=20, choices=Status.choices, default="subscribed", db_index=True)

    
    signup_source = models.CharField( max_length=20, choices=Source.choices, default="import")
    
    merge_fields = models.JSONField(default=dict, blank=True)

    language = models.CharField(max_length=10, blank=True, null=True)

    location = models.JSONField(default=dict, blank=True)  # e.g., {"country": "EG", "tz": "Africa/Cairo"}
    last_changed = models.DateTimeField(default=timezone.now ,blank=True, null=True)
    timestamp_signup = models.DateTimeField(blank=True, null=True)
    ip_signup = models.GenericIPAddressField(blank=True, null=True)
    timestamp_opt = models.DateTimeField(blank=True, null=True)
    ip_opt = models.GenericIPAddressField(blank=True, null=True)

    unsubscribed_at = models.DateTimeField(blank=True, null=True)
    unsubscribed_ip = models.GenericIPAddressField(blank=True, null=True)

    tags = models.ManyToManyField("Tag", related_name="contacts", blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        unique_together = [('audience', 'email_address')]

        indexes = [
            models.Index(fields=["audience", "created_at"]),
            models.Index(fields=["audience", "status", "created_at"]),
        ]

        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email_address} [{self.audience.name}]"
    
    @property
    def can_receive(self) -> bool:
        return self.status == Status.SUBSCRIBED
    
    def save(self, *args, **kwargs):
        # normalize email for reliable uniqueness across DBs
        if self.email_address:
            self.email_address = self.email_address.strip().lower()
        self.last_changed = timezone.now()
        super().save(*args, **kwargs)

    def mark_cleaned(self):
        if self.status != Status.CLEANED:
            self.status = Status.CLEANED
            self.save(update_fields=["status", "updated_at"])

    def mark_unsubscribed(self, ip=None, reason: str | None = None):
        if self.status != Status.UNSUBSCRIBED:
            self.status = Status.UNSUBSCRIBED
            self.unsubscribed_at = timezone.now()
            if ip:
                self.unsubscribed_ip = ip
            self.save(update_fields=["status", "unsubscribed_at", "unsubscribed_ip", "updated_at"])
    


class Tag(models.Model):
    """Simple label; unique per audience."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
        

class ContactNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="notes")
    note = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note for {self.contact.email_address}"


