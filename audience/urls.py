from rest_framework.routers import DefaultRouter
from .api import ContactViewSet, TagViewSet, AudienceViewSet

app_name = "audience"

router = DefaultRouter()
router.register(r"audiences", AudienceViewSet, basename="audience")
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"tags", TagViewSet, basename="tag")


urlpatterns = router.urls
