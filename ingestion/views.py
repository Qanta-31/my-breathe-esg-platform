import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Tenant, IngestionBatch, EmissionRecord
from .serializers import TenantSerializer, IngestionBatchSerializer, EmissionRecordSerializer


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer


class IngestionBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IngestionBatch.objects.all().order_by('-ingested_at')
    serializer_class = IngestionBatchSerializer


class EmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = EmissionRecord.objects.select_related('tenant', 'batch').all()
    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Allow filtering by source_type, scope, status via query params
        source = self.request.query_params.get('source_type')
        scope = self.request.query_params.get('scope')
        record_status = self.request.query_params.get('status')
        if source:
            qs = qs.filter(source_type=source)
        if scope:
            qs = qs.filter(scope=scope)
        if record_status:
            qs = qs.filter(status=record_status)
        return qs

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Analyst approves a PENDING or FLAGGED record."""
        record = self.get_object()
        if record.status == 'LOCKED':
            return Response({"error": "Cannot modify a locked record."}, status=status.HTTP_400_BAD_REQUEST)
        record.status = 'APPROVED'
        record.is_edited = True
        record.reviewed_by = request.data.get('analyst', 'analyst')
        record.reviewed_at = timezone.now()
        record.save()
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock an approved record for audit. Irreversible in this prototype."""
        record = self.get_object()
        if record.status != 'APPROVED':
            return Response(
                {"error": "Only approved records can be locked for audit."},
                status=status.HTTP_400_BAD_REQUEST
            )
        record.status = 'LOCKED'
        record.reviewed_by = request.data.get('analyst', record.reviewed_by)
        record.reviewed_at = timezone.now()
        record.save()
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """Analyst flags a record as suspicious."""
        record = self.get_object()
        if record.status == 'LOCKED':
            return Response({"error": "Cannot modify a locked record."}, status=status.HTTP_400_BAD_REQUEST)
        record.status = 'FLAGGED'
        record.flag_reason = request.data.get('reason', '')
        record.is_edited = True
        record.reviewed_by = request.data.get('analyst', 'analyst')
        record.reviewed_at = timezone.now()
        record.save()
        return Response(EmissionRecordSerializer(record).data)

    # ------------------------------------------------------------------
    # Ingestion endpoints
    # ------------------------------------------------------------------

    @action(detail=False, methods=['post'])
    def upload_sap(self, request):
        """
        Ingest an SAP flat-file CSV export (fuel & procurement).
        Handles German/English headers, inconsistent units, and garbage values.
        """
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        tenant, _ = Tenant.objects.get_or_create(name="Acme Corp Enterprise")

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type='SAP',
            file_name=file.name,
        )

        decoded = file.read().decode('utf-8-sig')  # utf-8-sig handles BOM from SAP GUI exports
        reader = csv.DictReader(io.StringIO(decoded))

        records_created = 0
        errors = 0

        for row in reader:
            # SAP reality: headers may be German or English depending on server locale
            raw_qty = row.get('Quantity', row.get('Menge', ''))
            raw_unit = row.get('Unit', row.get('Einheit', 'Unknown'))
            material = row.get('Material', row.get('Materialkurztext', ''))
            plant = row.get('PlantID', row.get('Werk', ''))

            # Determine scope: fuel = Scope 1, procurement materials = Scope 3
            scope = 'SCOPE_1'
            fuel_keywords = ['diesel', 'fuel', 'gas', 'petrol', 'lpg', 'coal', 'natural gas']
            if material and not any(kw in material.lower() for kw in fuel_keywords):
                scope = 'SCOPE_3'

            # Parse quantity with graceful degradation
            flag_reason = ''
            try:
                # Handle European decimal format (comma as decimal separator)
                cleaned = str(raw_qty).replace(',', '.').strip()
                normalized_value = Decimal(cleaned)
            except (InvalidOperation, ValueError):
                normalized_value = Decimal('0')
                flag_reason = f"Could not parse quantity: '{raw_qty}'"

            record_status = 'FLAGGED' if flag_reason else 'PENDING'

            EmissionRecord.objects.create(
                tenant=tenant,
                batch=batch,
                source_type='SAP',
                scope=scope,
                raw_data=row,
                normalized_value=normalized_value,
                normalized_unit=raw_unit.strip(),
                original_unit=raw_unit.strip(),
                description=f"{material} ({plant})" if plant else material,
                flag_reason=flag_reason,
                status=record_status,
            )
            records_created += 1
            if flag_reason:
                errors += 1

        batch.row_count = records_created
        batch.error_count = errors
        batch.save()

        return Response({
            "message": f"Ingested {records_created} SAP records ({errors} flagged).",
            "batch_id": batch.id,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def upload_utility(self, request):
        """
        Ingest a utility portal CSV export (electricity meter readings).
        Normalizes MWh → kWh. Flags missing or zero readings.
        """
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        tenant, _ = Tenant.objects.get_or_create(name="Acme Corp Enterprise")

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type='UTILITY',
            file_name=file.name,
        )

        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        records_created = 0
        errors = 0

        for row in reader:
            raw_usage = row.get('Usage', row.get('Meter_Reading', row.get('Consumption', '')))
            raw_unit = row.get('Unit', 'kWh').strip()
            meter_id = row.get('Meter_ID', row.get('Meter', ''))
            billing_period = row.get('Billing_Period', row.get('Period', ''))

            flag_reason = ''
            try:
                usage_val = Decimal(str(raw_usage).replace(',', '.').strip())
            except (InvalidOperation, ValueError):
                usage_val = Decimal('0')
                flag_reason = f"Could not parse usage value: '{raw_usage}'"

            # Normalize to kWh
            original_unit = raw_unit
            if raw_unit.upper() in ('MWH', 'MW·H', 'MEGAWATT-HOUR'):
                normalized_value = usage_val * 1000
                normalized_unit = 'kWh'
            elif raw_unit.upper() in ('GWH',):
                normalized_value = usage_val * 1_000_000
                normalized_unit = 'kWh'
            else:
                normalized_value = usage_val
                normalized_unit = 'kWh'

            # Flag zero or suspiciously high readings
            if not flag_reason and normalized_value == 0:
                flag_reason = "Zero usage reported — possible meter fault or vacant period"
            elif not flag_reason and normalized_value > 500_000:
                flag_reason = f"Unusually high reading ({normalized_value} kWh) — verify with facility"

            record_status = 'FLAGGED' if flag_reason else 'PENDING'

            EmissionRecord.objects.create(
                tenant=tenant,
                batch=batch,
                source_type='UTILITY',
                scope='SCOPE_2',
                raw_data=row,
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
                original_unit=original_unit,
                description=f"Meter {meter_id} — {billing_period}",
                flag_reason=flag_reason,
                status=record_status,
            )
            records_created += 1
            if flag_reason:
                errors += 1

        batch.row_count = records_created
        batch.error_count = errors
        batch.save()

        return Response({
            "message": f"Ingested {records_created} Utility records ({errors} flagged).",
            "batch_id": batch.id,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def upload_travel(self, request):
        """
        Ingest a corporate travel platform JSON export (Navan/Concur style).
        Handles flights, hotels, and ground transport with different normalization.
        Flags flights with missing distance data.
        """
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        tenant, _ = Tenant.objects.get_or_create(name="Acme Corp Enterprise")

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type='TRAVEL',
            file_name=file.name,
        )

        try:
            data = json.load(file)
        except json.JSONDecodeError:
            batch.delete()
            return Response({"error": "Invalid JSON format."}, status=status.HTTP_400_BAD_REQUEST)

        trips = data.get('trips', data.get('bookings', []))
        records_created = 0
        errors = 0

        for item in trips:
            category = item.get('category', item.get('type', 'UNKNOWN')).upper()
            flag_reason = ''

            if category == 'FLIGHT':
                raw_distance = item.get('distance_km', item.get('distance', None))
                route = item.get('route', item.get('origin', '') + '-' + item.get('destination', ''))
                try:
                    normalized_value = Decimal(str(raw_distance))
                except (InvalidOperation, TypeError, ValueError):
                    normalized_value = Decimal('0')
                    flag_reason = f"Missing distance for route {route} — needs geocoding from airport codes"
                normalized_unit = 'km'
                description = f"Flight: {route}"

            elif category == 'HOTEL':
                nights = item.get('nights', item.get('duration_nights', 0))
                location = item.get('location', item.get('city', 'Unknown'))
                try:
                    normalized_value = Decimal(str(nights))
                except (InvalidOperation, TypeError, ValueError):
                    normalized_value = Decimal('0')
                    flag_reason = f"Could not parse hotel nights"
                normalized_unit = 'nights'
                description = f"Hotel: {location} ({nights} nights)"

            elif category in ('GROUND', 'RAIL', 'TAXI', 'CAR'):
                raw_distance = item.get('distance_km', item.get('distance', 0))
                mode = item.get('mode', category.title())
                try:
                    normalized_value = Decimal(str(raw_distance))
                except (InvalidOperation, TypeError, ValueError):
                    normalized_value = Decimal('0')
                    flag_reason = f"Could not parse ground transport distance"
                normalized_unit = 'km'
                description = f"Ground ({mode}): {item.get('route', 'N/A')}"

            else:
                normalized_value = Decimal('0')
                normalized_unit = 'unknown'
                description = f"Unknown travel category: {category}"
                flag_reason = f"Unrecognized travel category '{category}'"

            record_status = 'FLAGGED' if flag_reason else 'PENDING'

            EmissionRecord.objects.create(
                tenant=tenant,
                batch=batch,
                source_type='TRAVEL',
                scope='SCOPE_3',
                raw_data=item,
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
                original_unit=normalized_unit,
                description=description,
                flag_reason=flag_reason,
                status=record_status,
            )
            records_created += 1
            if flag_reason:
                errors += 1

        batch.row_count = records_created
        batch.error_count = errors
        batch.save()

        return Response({
            "message": f"Ingested {records_created} Travel records ({errors} flagged).",
            "batch_id": batch.id,
        }, status=status.HTTP_201_CREATED)
