from rest_framework import serializers
from audience.models import Audience, Contact, Tag


class TagSerialzer(serializers.ModelSerializer):
    audience = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "name", "audience"]

class TagDetailSerializer(serializers.ModelSerializer):
    contacts = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="email_address"
    )
    audience = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Tag
        fields = ["id", "name", "audience", "contacts"]

class AudienceSerialzer(serializers.ModelSerializer):
    contacts_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Audience
        fields = ["id", "name", "created_at", "contacts_count"]

class AudienceDetailSerializer(serializers.ModelSerializer):
    contacts = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="email_address"
    )
    contacts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Audience
        fields = ["id", "name", "contacts_count", "contacts", "created_at"]
    
class ContactSerializer(serializers.HyperlinkedModelSerializer):
    audience_id = serializers.PrimaryKeyRelatedField(required=True,queryset=Audience.objects.all(), source='audience')
    audience = serializers.SlugRelatedField(slug_field="name", read_only=True)
    tags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    contact_url = serializers.HyperlinkedIdentityField(
        view_name='audience:contact-detail',  # include namespace if you used one (e.g., 'api:contact-detail')
    )

    class Meta:
        model = Contact
        fields = [
            "contact_url","id", "audience", "audience_id", "email_address", "status", "signup_source", 
            "merge_fields", "language", "location", "created_at", "tags",
        ]