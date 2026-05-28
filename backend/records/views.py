import uuid
from django.utils import timezone
from django.db.models import Count, Sum, Q
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Tenant, DataSource, IngestionBatch, ActivityRecord, AuditLog, IngestionError
from .serializers import (
    TenantSerializer, DataSourceSerializer, IngestionBatchSerializer,
    ActivityRecordSerializer, ActivityRecordUpdateSerializer,
    AuditLogSerializer, IngestionErrorSerializer
)

def get_tenant_from_request(request):
    """
    Helper to resolve a Tenant from headers or query parameters.
    """
    tenant_id_header = request.headers.get('X-Tenant-Id')
    tenant_slug_header = request.headers.get('X-Tenant-Slug')
    tenant_param = request.query_params.get('tenant')

    if tenant_id_header:
        return Tenant.objects.filter(pk=tenant_id_header).first()
    if tenant_slug_header:
        return Tenant.objects.filter(slug=tenant_slug_header).first()

    if tenant_param:
        try:
            # Check if it's a UUID
            uuid.UUID(tenant_param)
            return Tenant.objects.filter(pk=tenant_param).first()
        except ValueError:
            return Tenant.objects.filter(slug=tenant_param).first()

    return None


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'


class TenantIsolatedViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet enforcing tenant isolation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_tenant(self):
        tenant = get_tenant_from_request(self.request)
        return tenant

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        if not tenant:
            raise Response({"error": "Tenant context required."}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(tenant=tenant)


class DataSourceViewSet(TenantIsolatedViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer

    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return self.queryset.none()
        return self.queryset.filter(tenant=tenant)


class IngestionBatchViewSet(viewsets.ModelViewSet):
    queryset = IngestionBatch.objects.all().order_by('-uploaded_at')
    serializer_class = IngestionBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = get_tenant_from_request(self.request)
        if not tenant:
            return self.queryset.none()
        return self.queryset.filter(data_source__tenant=tenant)

    @action(detail=True, methods=['get'])
    def errors(self, request, pk=None):
        batch = self.get_object()
        errors = batch.errors.all().order_by('row_number')
        serializer = IngestionErrorSerializer(errors, many=True)
        return Response(serializer.data)


class ActivityRecordViewSet(TenantIsolatedViewSet):
    queryset = ActivityRecord.objects.all().order_by('-created_at')
    serializer_class = ActivityRecordSerializer

    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return self.queryset.none()
        
        queryset = self.queryset.filter(tenant=tenant)

        # Filters
        status_filter = self.request.query_params.get('status')
        scope_filter = self.request.query_params.get('scope')
        source_filter = self.request.query_params.get('source_type')
        batch_filter = self.request.query_params.get('batch_id')
        start_date = self.request.query_params.get('period_start')
        end_date = self.request.query_params.get('period_end')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if scope_filter:
            queryset = queryset.filter(scope=scope_filter)
        if source_filter:
            queryset = queryset.filter(source_type=source_filter)
        if batch_filter:
            queryset = queryset.filter(batch_id=batch_filter)
        if start_date:
            queryset = queryset.filter(period_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(period_end__lte=end_date)

        return queryset

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ActivityRecordUpdateSerializer
        return ActivityRecordSerializer

    def perform_update(self, serializer):
        # Attach the current user to the instance so the signals can log it in AuditLog
        serializer.instance._changed_by = self.request.user
        serializer.save()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({"error": "This record is locked and cannot be modified."}, status=status.HTTP_400_BAD_REQUEST)
        
        record._changed_by = request.user
        record.status = 'APPROVED'
        record.is_locked = True
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()
        
        serializer = ActivityRecordSerializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({"error": "This record is locked and cannot be modified."}, status=status.HTTP_400_BAD_REQUEST)
        
        record._changed_by = request.user
        record.status = 'REJECTED'
        record.is_locked = True
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()
        
        serializer = ActivityRecordSerializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        record = self.get_object()
        if record.is_locked:
            return Response({"error": "This record is locked and cannot be modified."}, status=status.HTTP_400_BAD_REQUEST)
        
        flag_reason = request.data.get('flag_reason')
        if not flag_reason or not flag_reason.strip():
            return Response({"error": "A flag reason must be provided."}, status=status.HTTP_400_BAD_REQUEST)

        record._changed_by = request.user
        record.status = 'FLAGGED'
        record.flag_reason = flag_reason
        record.is_locked = False  # Keep unlocked so they can edit or approve/reject later
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()

        serializer = ActivityRecordSerializer(record)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='audit-log')
    def audit_log(self, request, pk=None):
        record = self.get_object()
        audit_logs = record.audit_logs.all().order_by('-changed_at')
        serializer = AuditLogSerializer(audit_logs, many=True)
        return Response(serializer.data)


class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = get_tenant_from_request(request)
        if not tenant:
            return Response({"error": "Tenant context is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_qs = ActivityRecord.objects.filter(tenant=tenant)

        # Status counts
        status_counts = base_qs.values('status').annotate(count=Count('id'))
        status_data = {
            'PENDING_REVIEW': 0,
            'APPROVED': 0,
            'REJECTED': 0,
            'FLAGGED': 0
        }
        for item in status_counts:
            status_data[item['status']] = item['count']

        # Scope counts
        scope_counts = base_qs.values('scope').annotate(count=Count('id'))
        scope_data = {
            'SCOPE_1': 0,
            'SCOPE_2': 0,
            'SCOPE_3': 0
        }
        for item in scope_counts:
            scope_data[item['scope']] = item['count']

        # Source type counts
        source_counts = base_qs.values('source_type').annotate(count=Count('id'))
        source_data = {
            'SAP': 0,
            'UTILITY': 0,
            'TRAVEL': 0
        }
        for item in source_counts:
            source_data[item['source_type']] = item['count']

        # Activity values by scope (summing normalized values where status is APPROVED)
        # Note: In a complete system, we sum all, but let's sum APPROVED for total audit-ready or total records.
        # Let's return both total active sum and approved sum to make it premium.
        activity_by_scope = base_qs.values('scope').annotate(
            total_value=Sum('activity_value'),
            approved_value=Sum('activity_value', filter=Q(status='APPROVED'))
        )
        activity_data = {
            'SCOPE_1': {'total': 0.0, 'approved': 0.0, 'unit': 'L/kg/m3/tonnes'},
            'SCOPE_2': {'total': 0.0, 'approved': 0.0, 'unit': 'kWh'},
            'SCOPE_3': {'total': 0.0, 'approved': 0.0, 'unit': 'km/nights'}
        }
        for item in activity_by_scope:
            sc = item['scope']
            activity_data[sc]['total'] = float(item['total_value'] or 0.0)
            activity_data[sc]['approved'] = float(item['approved_value'] or 0.0)

        # Let's count batches
        batch_count = IngestionBatch.objects.filter(data_source__tenant=tenant).count()

        return Response({
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'slug': tenant.slug
            },
            'status_counts': status_data,
            'scope_counts': scope_data,
            'source_counts': source_data,
            'activity_by_scope': activity_data,
            'batch_count': batch_count
        })
