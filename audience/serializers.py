from rest_framework import serializers
from audience.models import Audience, Contact, Tag
import uuid


class TagSerialzer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ["id", "name"]

class TagDetailSerializer(serializers.ModelSerializer):
    contacts = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="email_address"
    )

    class Meta:
        model = Tag
        fields = ["id", "name", "contacts"]

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
    audience_id = serializers.PrimaryKeyRelatedField(required=True,
                                                    queryset=Audience.objects.all(),
                                                    source='audience')
    audience = serializers.SlugRelatedField(slug_field="name", read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    tags = TagSerialzer(many=True, read_only=True)

    contact_url = serializers.HyperlinkedIdentityField(
        view_name='audience:contact-detail',  # include namespace if you used one (e.g., 'api:contact-detail')
    )

    class Meta:
        model = Contact
        fields = [
            "contact_url","id", "audience", "audience_id", "email_address", "status", "signup_source", 
            "merge_fields", "language", "location", "created_at", "tags", "tag_names"
        ]


    def create(self, validated_data):
        tags_data = validated_data.pop("tag_names", [])
        print(tags_data)
        contact = Contact.objects.create(**validated_data)
        print(contact.tags)
        contact.tags.set(self._get_or_create_tags(tags_data))
        print(contact.tags)
        return contact

    def update(self, instance, validated_data):
        tags_data = validated_data.pop("tag_names", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags_data is not None:
            instance.tags.set(self._get_or_create_tags(tags_data))
        return instance

    def _get_or_create_tags(self, tags_data):
        tags = []
        for tag_value in tags_data:
            try:
                # لو قيمة UUID
                tag_uuid = uuid.UUID(tag_value)
                tag = Tag.objects.get(id=tag_uuid)
            except (ValueError, Tag.DoesNotExist):
                # لو مش UUID أو مش موجود → نعتبرها name
                tag, _ = Tag.objects.get_or_create(name=tag_value)
            tags.append(tag)
        return tags