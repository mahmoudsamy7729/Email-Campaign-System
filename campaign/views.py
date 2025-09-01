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
from tracking.link_compiler import compile_links_for_campaign

# Be resilient if setting is missing during import
TRACKING_BASE_URL: Optional[str] = getattr(settings, "TRACKING_BASE_URL", None)


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

    

    # -----------------------
    # Helpers (private)
    # -----------------------
    def _tracking_base(self) -> str:
        if not TRACKING_BASE_URL:
            raise RuntimeError("TRACKING_BASE_URL is not configured.")
        return TRACKING_BASE_URL

    def _should_compile(self, instance: Campaign, validated: Dict, force: bool) -> bool:
        """
        Compile if:
          - campaign has HTML after save AND
          - (content_html changed) OR (force is True)
        """
        if not instance.content_html:
            return False
        html_in_payload = "content_html" in validated
        html_changed = html_in_payload and (validated["content_html"] != getattr(instance, "content_html", None))
        # Note: at this point instance.content_html is *new* value after save,
        # so compare against what was on the instance before save if you need to.
        # To keep it simple and safe, treat presence in validated payload as "potentially changed".
        return force or html_in_payload or bool(getattr(instance, "compiled_at", None) is None)

    def _compile_links(self, campaign: Campaign) -> Dict:
        return compile_links_for_campaign(
            campaign=campaign,
            tracking_base=self._tracking_base(),
        )

    def _build_payload(self, serializer: CampaignSerializer, campaign: Campaign, compile_result: Dict) -> Dict:
        payload = {
            **serializer.to_representation(campaign),
            "compiled_at": getattr(campaign, "compiled_at", None),
        }
        if compile_result:
            payload.update({
                "links_count": compile_result.get("links_count", 0),
                "links": compile_result.get("links", []),
                "compiled_html": compile_result.get("compiled_html", ""),
            })
        return payload

    # -----------------------
    # CRUD
    # -----------------------
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign: Campaign = serializer.save()

        compile_result: Dict = {}
        if campaign.content_html:
            compile_result = self._compile_links(campaign)

        headers = self.get_success_headers(serializer.data)
        payload = self._build_payload(serializer, campaign, compile_result)
        return Response(payload, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        force_recompile = bool(request.data.get("force_recompile"))

        instance: Campaign = self.get_object()
        # Capture pre-save HTML to detect real change precisely
        old_html = instance.content_html
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        campaign: Campaign = serializer.save()

        compile_result: Dict = {}
        html_in_payload = "content_html" in serializer.validated_data
        html_changed = html_in_payload and (serializer.validated_data["content_html"] != old_html)
        if campaign.content_html and (force_recompile or html_changed or not campaign.compiled_at):
            compile_result = self._compile_links(campaign)

        payload = self._build_payload(serializer, campaign, compile_result)
        return Response(payload, status=status.HTTP_200_OK)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    # -----------------------
    # Actions
    # -----------------------
    def _validate_send(self, campaign: Campaign) -> Optional[Response]:
        if campaign.status not in {CampaignStatus.Draft, CampaignStatus.Scheduled}:
            # 409 fits "invalid state transition"
            return Response(
                {"detail": f"Campaign already {campaign.status}."},
                status=status.HTTP_409_CONFLICT,
            )
        if campaign.estimated_recipients == 0:
            return Response(
                {"detail": "Estimated recipients is 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        # Lock row to avoid double-send races under concurrent requests
        with transaction.atomic():
            campaign = Campaign.objects.select_for_update().get(pk=pk)

            invalid = self._validate_send(campaign)
            if invalid:
                return invalid

            campaign.mark_sending()
            campaign.save(update_fields=["status", "started_sending_at"])

        # Fan-out outside the lock
        res = kickoff_campaign_send.delay(str(campaign.id))
        return Response(
            {"detail": "Sending started.", "task_id": str(res.id)},
            status=status.HTTP_202_ACCEPTED,
        )
