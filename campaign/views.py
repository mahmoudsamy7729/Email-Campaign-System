from typing import Dict, Optional

from django.db import transaction
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


from .models import Campaign, CampaignStatus
from .serializers import CampaignSerializer
from .tasks import kickoff_campaign_send
from .services import campaigns as services
from .services import exceptions



class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().select_related("audience")
    serializer_class = CampaignSerializer
    permission_classes = [AllowAny]
    filterset_fields = {
        "audience": ["exact"],
        "status": ["exact"],
        "kind": ["exact"],
    }
    search_fields = ["title"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign: Campaign = serializer.save()

        compile_result: Dict = {}
        if campaign.content_html:
            compile_result = services.compile_links(campaign)

        headers = self.get_success_headers(serializer.data)
        payload = services.build_payload(serializer.data, campaign, compile_result)
        return Response(payload, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        force_recompile = bool(request.data.get("force_recompile")) #True / False

        instance: Campaign = self.get_object()
        # Capture pre-save HTML to detect real change precisely
        old_html = instance.content_html

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        campaign: Campaign = serializer.save()

        compile_result: Dict = {}
        if services.should_compile(campaign, serializer.validated_data, force_recompile, old_html):
            compile_result = services.compile_links(campaign)

        rep = serializer.to_representation(campaign)        
        payload = services.build_payload(rep, campaign, compile_result)
        return Response(payload, status=status.HTTP_200_OK)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def send(self, request, pk: str | None = None) -> Response:
        try:
            result = services.send_campaign(campaign_id=pk) 
        except Campaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except exceptions.InvalidState as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except exceptions.ZeroRecipients as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": "Sending started.", "task_id": str(result["task_id"])},
            status=status.HTTP_202_ACCEPTED,
        )
    
    @action(detail=True, methods=["post"], url_path="test-email")
    def send_test(self, request, pk: str | None = None):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        to_email = serializer.validated_data.get("test_email")
        result = services.send_test_email(campaign_id=pk, test_email=to_email)
        return Response({"detail": "Test email sent.", **result}, status=status.HTTP_200_OK)
