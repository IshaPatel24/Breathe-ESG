"""
URL configuration for breathe_esg project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from records.views import (
    TenantViewSet, DataSourceViewSet, IngestionBatchViewSet,
    ActivityRecordViewSet, DashboardSummaryView
)
from ingestion.views import FileUploadView

# Default DRF Router
router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'data-sources', DataSourceViewSet, basename='data-source')
router.register(r'batches', IngestionBatchViewSet, basename='batch')
router.register(r'records', ActivityRecordViewSet, basename='record')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/ingestion/upload/', FileUploadView.as_view(), name='ingestion_upload'),
    path('api/dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),

    # SPA support: serve React template for front-end pages
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('<path:path>', TemplateView.as_view(template_name='index.html')),
]
