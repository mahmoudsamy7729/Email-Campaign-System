from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from faker import Faker
import random

from audience.models import (
    Audience, Contact, Tag, ContactTag, ContactNote, Status, Source
)


class Command(BaseCommand):
    help = "Populate Audience/Contact/Tag tables with dummy data."

    def add_arguments(self, parser):
        parser.add_argument("--audiences", type=int, default=2, help="Number of audiences to create")
        parser.add_argument("--contacts", type=int, default=200, help="Contacts per audience")
        parser.add_argument("--tags", type=int, default=6, help="Tags per audience")
        parser.add_argument(
            "--notes-per-contact", type=int, default=1,
            help="Max notes per contact (random 0..N). Use 0 for none."
        )
        parser.add_argument("--clear", action="store_true", help="Delete existing data first")
        parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    @transaction.atomic
    def handle(self, *args, **opts):
        rng = random.Random(opts["seed"])
        fake = Faker(["en_US", "ar_EG"])
        Faker.seed(opts["seed"])

        if opts["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data…"))
            ContactTag.objects.all().delete()
            ContactNote.objects.all().delete()
            Tag.objects.all().delete()
            Contact.objects.all().delete()
            Audience.objects.all().delete()

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding data…"))

        total_contacts = 0
        for a_idx in range(opts["audiences"]):
            audience_name = f"Audience {a_idx+1}"
            audience, _ = Audience.objects.get_or_create(name=audience_name)

            # --- Tags ---
            tag_names = self._default_tag_names(opts["tags"])
            tags = [Tag(audience=audience, name=name) for name in tag_names]
            Tag.objects.bulk_create(tags, ignore_conflicts=True)
            tags = list(Tag.objects.filter(audience=audience))  # reload with ids

            # --- Contacts ---
            contacts_payload = []
            fake.unique.clear()
            now = timezone.now()

            for i in range(opts["contacts"]):
                first = fake.first_name()
                last = fake.last_name()
                # email guaranteed unique per audience by adding counter
                local_part = f"{first}.{last}.{a_idx}-{i}".lower()
                domain = "example.com"
                email = f"{local_part}@{domain}"

                # signup time within last 365 days
                signed_days_ago = rng.randint(0, 365)
                ts_signup = now - timezone.timedelta(days=signed_days_ago, hours=rng.randint(0, 23))
                ip_signup = fake.ipv4_public()

                status = self._weighted_status(rng)   # 70% subscribed, 20% unsubscribed, 10% cleaned
                signup_source = rng.choice([Source.IMPORT, Source.FORM, Source.API, Source.MANUAL])

                # Optional opt-in and unsubscribe timestamps respecting your model rules
                ts_opt = None
                ip_opt = None
                if status == Status.SUBSCRIBED:
                    ts_opt = ts_signup + timezone.timedelta(minutes=rng.randint(1, 720))  # within 12h
                    ip_opt = fake.ipv4_public()

                unsubscribed_at = None
                unsub_ip = None
                if status == Status.UNSUBSCRIBED:
                    unsubscribed_at = ts_signup + timezone.timedelta(days=rng.randint(0, 300))
                    unsub_ip = fake.ipv4_public()

                # simple merge_fields
                merge_fields = {
                    "FNAME": first,
                    "LNAME": last,
                    "PHONE": fake.msisdn()[:15],
                    "BIRTHDAY": str(fake.date_of_birth(minimum_age=18, maximum_age=60)),
                }

                # basic location
                location = {
                    "country": fake.country_code(),
                    "tz": fake.timezone(),
                }

                contacts_payload.append(Contact(
                    audience=audience,
                    email_address=email,
                    status=status,
                    signup_source=signup_source,
                    merge_fields=merge_fields,
                    language=rng.choice(["en", "ar"]),
                    location=location,
                    last_changed=ts_signup,
                    timestamp_signup=ts_signup,
                    ip_signup=ip_signup,
                    timestamp_opt=ts_opt,
                    ip_opt=ip_opt,
                    unsubscribed_at=unsubscribed_at,
                    unsubscribed_ip=unsub_ip,
                    created_at=ts_signup,
                    # updated_at is auto_now; set by save()
                ))

            # bulk create contacts
            Contact.objects.bulk_create(contacts_payload, batch_size=1000)
            contacts = list(Contact.objects.filter(audience=audience).order_by("created_at"))
            total_contacts += len(contacts)

            # --- Tag assignments (through model) ---
            ct_payload = []
            for c in contacts:
                # each contact gets 0..3 tags
                k = rng.randint(0, min(3, len(tags)))
                if k:
                    for tag in rng.sample(tags, k):
                        ct_payload.append(ContactTag(
                            contact=c,
                            tag=tag,
                            date_added=c.created_at + timezone.timedelta(days=rng.randint(0, 30)),
                        ))
            ContactTag.objects.bulk_create(ct_payload, batch_size=1000, ignore_conflicts=True)

            # --- Notes ---
            if opts["notes_per_contact"] > 0:
                notes_payload = []
                for c in contacts:
                    n = rng.randint(0, opts["notes_per_contact"])
                    for _ in range(n):
                        notes_payload.append(ContactNote(
                            contact=c,
                            note=fake.sentence(nb_words=12),
                            created_at=c.created_at + timezone.timedelta(days=rng.randint(0, 60)),
                        ))
                ContactNote.objects.bulk_create(notes_payload, batch_size=1000)

            self.stdout.write(self.style.SUCCESS(
                f"Audience '{audience.name}': {len(contacts)} contacts, "
                f"{len(tags)} tags, {ContactTag.objects.filter(contact__audience=audience).count()} links"
            ))

        self.stdout.write(self.style.SUCCESS(f"Done. Created/ensured {opts['audiences']} audiences, {total_contacts} contacts."))

    # --- helpers ---

    def _weighted_status(self, rng: random.Random) -> str:
        # Adjust weights as you wish
        return rng.choices(
            population=[Status.SUBSCRIBED, Status.UNSUBSCRIBED, Status.CLEANED],
            weights=[0.7, 0.2, 0.1],
            k=1,
        )[0]

    def _default_tag_names(self, count: int):
        base = ["Customer", "Lead", "Newsletter", "Promo", "VIP", "Webinar", "BlackFriday", "FromCSV", "Trial"]
        if count <= len(base):
            return base[:count]
        # pad with generic labels if more requested
        extra = [f"Tag{i}" for i in range(1, count - len(base) + 1)]
        return base + extra