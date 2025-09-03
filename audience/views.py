from rest_framework import viewsets , serializers
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from django.db.models import Prefetch, QuerySet


from .models import Audience, Contact, Tag
from .serializers import AudienceSerialzer, ContactSerializer, TagSerialzer, TagDetailSerializer, AudienceDetailSerializer
from audience.services import services


class AudienceViewSet(viewsets.ModelViewSet):
    queryset = Audience.objects.annotate(contacts_count = Count('contacts')).all()
    permission_classes = [AllowAny]

    def get_queryset(self) -> QuerySet[Audience]:
        queryset = super().get_queryset()
        if self.action == "retrieve" and services.include_contacts(self.request.query_params.get("include_contacts")):
            contacts_qs = Contact.objects.only("id", "email_address")
            queryset = queryset.prefetch_related(Prefetch("contacts", queryset=contacts_qs))
        return queryset
    
    def get_serializer_class(self) -> type[serializers.ModelSerializer]:
        if self.action == "retrieve"  and services.include_contacts(self.request.query_params.get("include_contacts")):
            return AudienceDetailSerializer
        return AudienceSerialzer


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.select_related("audience").all()
    permission_classes = [AllowAny]
    filterset_fields = ["audience"]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self) -> QuerySet[Tag]:
        queryset = super().get_queryset()
        if self.action == "retrieve" and services.include_contacts(self.request.query_params.get("include_contacts")):
            contacts_qs = Contact.objects.only("id", "email_address")
            queryset = queryset.prefetch_related(Prefetch("contacts", queryset=contacts_qs))
        return queryset
    
    def get_serializer_class(self) -> type[serializers.ModelSerializer]:
        if self.action == "retrieve"  and services.include_contacts(self.request.query_params.get("include_contacts")):
            return TagDetailSerializer
        return TagSerialzer
    

class ContactViewSet(viewsets.ModelViewSet):
    queryset = (
        Contact.objects
        .select_related("audience")
        .prefetch_related("tags")
        .all()
    )
    serializer_class = ContactSerializer
    permission_classes = [AllowAny]  # or remove if you want auth
    # this cause 14 sql queries
    filterset_fields = {
        "audience": ["exact"],
        "status": ["exact"],
        "tags": ["exact"],
        "language": ["exact"],
        "signup_source": ["exact"],
        "created_at": ["date__gte", "date__lte"],
    }
    search_fields = ["email_address"]  # add more if you need
    ordering_fields = ["created_at", "email_address", "status"]
    ordering = ["-created_at"]
    