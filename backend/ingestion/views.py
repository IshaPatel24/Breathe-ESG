from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from records.models import Tenant, DataSource, IngestionBatch, ActivityRecord, IngestionError
from ingestion.parsers.sap_parser import parse_sap_file
from ingestion.parsers.utility_parser import parse_utility_file
from ingestion.parsers.travel_parser import parse_travel_file
import uuid

class FileUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [FormParser, MultiPartParser]

    def post(self, request, format=None):
        source_type = request.data.get('source_type')
        uploaded_file = request.FILES.get('file')
        tenant_id = request.data.get('tenant_id')

        if not source_type:
            return Response({"error": "source_type is required (choices: SAP, UTILITY, TRAVEL)."}, status=status.HTTP_400_BAD_REQUEST)
        if not uploaded_file:
            return Response({"error": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not tenant_id:
            return Response({"error": "tenant_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        source_type = source_type.upper()
        if source_type not in ['SAP', 'UTILITY', 'TRAVEL']:
            return Response({"error": "Invalid source_type. Choices are SAP, UTILITY, TRAVEL."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Resolve Tenant
        tenant = None
        try:
            uuid.UUID(tenant_id)
            tenant = Tenant.objects.filter(pk=tenant_id).first()
        except ValueError:
            tenant = Tenant.objects.filter(slug=tenant_id).first()

        if not tenant:
            return Response({"error": f"Tenant '{tenant_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Find or create default DataSource
        ds_label = f"Default {source_type} Source"
        data_source, created = DataSource.objects.get_or_create(
            tenant=tenant,
            source_type=source_type,
            defaults={'label': ds_label}
        )

        # 3. Create Ingestion Batch
        batch = IngestionBatch.objects.create(
            data_source=data_source,
            uploaded_by=request.user,
            file_name=uploaded_file.name,
            status='PROCESSING'
        )

        try:
            file_content = uploaded_file.read()
            
            # 4. Invoke the appropriate parser
            if source_type == 'SAP':
                records, errors = parse_sap_file(batch, file_content)
            elif source_type == 'UTILITY':
                records, errors = parse_utility_file(batch, file_content)
            elif source_type == 'TRAVEL':
                records, errors = parse_travel_file(batch, file_content)
            
            # 5. Bulk create records & errors
            if records:
                ActivityRecord.objects.bulk_create(records)
            if errors:
                IngestionError.objects.bulk_create(errors)

            # 6. Update batch metrics
            batch.row_count = len(records) + len(errors)
            batch.error_count = len(errors)
            batch.status = 'DONE' if len(errors) < batch.row_count or batch.row_count == 0 else 'FAILED'
            if len(errors) > 0:
                batch.notes = f"Processed {batch.row_count} rows. {batch.error_count} rows failed with validation errors."
            else:
                batch.notes = f"Successfully parsed all {batch.row_count} rows."
            batch.save()

        except ValueError as e:
            # Catch bad file / syntax / header errors to return 400 Bad Request
            batch.status = 'FAILED'
            batch.notes = f"Validation failed: {str(e)}"
            batch.save()
            return Response({
                "error": str(e),
                "batch_id": batch.id
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # System error returns 500
            batch.status = 'FAILED'
            batch.notes = f"System error during parsing: {str(e)}"
            batch.save()
            return Response({
                "error": "Failed to parse file",
                "detail": str(e),
                "batch_id": batch.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Reload batch details
        batch.refresh_from_db()

        return Response({
            "batch_id": batch.id,
            "status": batch.status,
            "row_count": batch.row_count,
            "error_count": batch.error_count,
            "rows_parsed": batch.row_count,
            "rows_errored": batch.error_count,
            "notes": batch.notes
        }, status=status.HTTP_201_CREATED)
