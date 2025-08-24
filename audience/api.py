from rest_framework import viewsets, request
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Q
from django.db import connection
from rest_framework.fields import BooleanField
from rest_framework.exceptions import ValidationError

from .models import Audience, Contact, Tag, Status
from .api_serializers import AudienceSerialzer, ContactSerializer, TagSerialzer, TagDetailSerializer, AudienceDetailSerializer

class AudienceViewSet(viewsets.ModelViewSet):
    queryset = Audience.objects.annotate(contacts_count = Count('contacts')).all()
    permission_classes = [AllowAny]
    pagination_class = None

    def _want_include_contacts(self) -> bool:
        """Robust boolean parsing for query params."""
        raw = self.request.query_params.get("include_contacts")
        if raw is None:
            return False
        try:
            return BooleanField().to_internal_value(raw)
        except ValidationError:
            return False  # or raise to enforce strictness
        
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve" and self._want_include_contacts():
            queryset = queryset.prefetch_related("contacts")
        return queryset
    
    def get_serializer_class(self):
        if self.action == "retrieve"  and self._want_include_contacts():
            return AudienceDetailSerializer
        return AudienceSerialzer


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.select_related("audience").all()
    permission_classes = [AllowAny]
    filterset_fields = ["audience"]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]

    def _want_include_contacts(self) -> bool:
        """Robust boolean parsing for query params."""
        raw = self.request.query_params.get("include_contacts")
        if raw is None:
            return False
        try:
            return BooleanField().to_internal_value(raw)
        except ValidationError:
            return False  # or raise to enforce strictness

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve" and self._want_include_contacts():
            queryset = queryset.prefetch_related("contacts")
        return queryset
    
    def get_serializer_class(self):
        if self.action == "retrieve"  and self._want_include_contacts():
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
    def list(self, request, *args, **kwargs):
        print("Contacts List called")
        response = super().list(request, *args, **kwargs)
        print(f"SQL queries for this request: {len(connection.queries)}")
        return response
    