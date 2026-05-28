import uuid
from django.db import models
from django.contrib.auth.models import User

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class DataSource(models.Model):
    SOURCE_TYPES = [
        ('SAP', 'SAP'),
        ('UTILITY', 'Utility Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='data_sources')
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    label = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.label} ({self.source_type}) - {self.tenant.name}"

class IngestionBatch(models.Model):
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='batches')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_batches')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PROCESSING')
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Batch {self.id} ({self.data_source.source_type}) - {self.status}"

class ActivityRecord(models.Model):
    STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED', 'Flagged'),
    ]

    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1'),
        ('SCOPE_2', 'Scope 2'),
        ('SCOPE_3', 'Scope 3'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='activity_records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='records')
    source_type = models.CharField(max_length=50, choices=DataSource.SOURCE_TYPES)
    scope = models.CharField(max_length=50, choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100) # e.g. fuel_combustion, electricity, business_travel, procurement
    
    activity_value = models.DecimalField(max_digits=18, decimal_places=4)
    activity_unit = models.CharField(max_length=50) # normalized, e.g., kWh, L, km
    
    activity_value_original = models.DecimalField(max_digits=18, decimal_places=4)
    activity_unit_original = models.CharField(max_length=50)
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    facility_code = models.CharField(max_length=100) # raw site/plant code
    raw_data = models.JSONField(default=dict)
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    flag_reason = models.TextField(blank=True, null=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    is_locked = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_type} {self.category} ({self.activity_value} {self.activity_unit}) - {self.status}"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATED', 'Created'),
        ('EDITED', 'Edited'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED', 'Flagged'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_record = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name='audit_logs')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_actions')
    changed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    before_state = models.JSONField(default=dict)
    after_state = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.action} on Record {self.activity_record_id} by {self.changed_by} at {self.changed_at}"

class IngestionError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='errors')
    row_number = models.IntegerField()
    raw_row = models.JSONField(default=dict)
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error in Batch {self.batch_id} Row {self.row_number}: {self.error_message[:50]}"
