from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantViewSet, EmissionRecordViewSet

# This router automatically creates all the standard API URLs for us
router = DefaultRouter()
router.register(r'tenants', TenantViewSet)
router.register(r'records', EmissionRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]