from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, IngestionBatchViewSet, EmissionRecordViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet)
router.register(r'batches', IngestionBatchViewSet)
router.register(r'records', EmissionRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
