from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Tenant, DataSource, IngestionBatch, ActivityRecord, AuditLog, IngestionError

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at']

class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'tenant', 'source_type', 'label', 'created_at', 'config']

class IngestionErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionError
        fields = ['id', 'batch', 'row_number', 'raw_row', 'error_message', 'created_at']

class IngestionBatchSerializer(serializers.ModelSerializer):
    errors = IngestionErrorSerializer(many=True, read_only=True)
    class Meta:
        model = IngestionBatch
        fields = ['id', 'data_source', 'uploaded_by', 'uploaded_at', 'file_name', 'status', 'row_count', 'error_count', 'notes', 'errors']

class ActivityRecordSerializer(serializers.ModelSerializer):
    reviewed_by_detail = UserSerializer(source='reviewed_by', read_only=True)
    batch_detail = IngestionBatchSerializer(source='batch', read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            'id', 'tenant', 'batch', 'batch_detail', 'source_type', 'scope', 'category',
            'activity_value', 'activity_unit', 'activity_value_original', 'activity_unit_original',
            'period_start', 'period_end', 'facility_code', 'raw_data', 'status', 'flag_reason',
            'reviewed_by', 'reviewed_by_detail', 'reviewed_at', 'is_locked', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'tenant', 'batch', 'source_type', 'scope', 'category',
            'activity_value', 'activity_unit', 'activity_value_original', 'activity_unit_original',
            'period_start', 'period_end', 'facility_code', 'raw_data', 'reviewed_by', 'reviewed_at', 'is_locked',
            'created_at', 'updated_at'
        ]

    def validate(self, attrs):
        # Prevent any edits to locked records
        if self.instance and self.instance.is_locked:
            raise serializers.ValidationError("This record is locked for audit and cannot be modified.")
        return attrs

class ActivityRecordUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer used specifically for partial updates (PATCH) on ActivityRecords.
    """
    class Meta:
        model = ActivityRecord
        fields = ['status', 'flag_reason']

    def validate(self, attrs):
        if self.instance and self.instance.is_locked:
            raise serializers.ValidationError("This record is locked for audit and cannot be modified.")
        return attrs

class AuditLogSerializer(serializers.ModelSerializer):
    changed_by_detail = UserSerializer(source='changed_by', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'activity_record', 'changed_by', 'changed_by_detail', 'changed_at', 'action', 'before_state', 'after_state']
