import csv
import io
import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Tenant, EmissionRecord
from .serializers import TenantSerializer, EmissionRecordSerializer

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

class EmissionRecordViewSet(viewsets.ModelViewSet):
    queryset = EmissionRecord.objects.all()
    serializer_class = EmissionRecordSerializer

    # This creates a custom URL specifically for uploading SAP files
    @action(detail=False, methods=['post'])
    def upload_sap(self, request):
        # 1. Check if a file was actually attached to the request
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        # 2. For this prototype, we'll auto-assign a default client company
        tenant, created = Tenant.objects.get_or_create(name="Acme Corp Enterprise")

        # 3. Read and decode the CSV file
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        
        # DictReader automatically uses the first row of the CSV as the column names
        reader = csv.DictReader(io_string)

        records_created = 0

        # 4. Loop through every row in the messy CSV
        for row in reader:
            # SAP Reality Check: We look for English headers, but fallback to German (Menge = Quantity)
            raw_qty = row.get('Quantity', row.get('Menge', 0))
            
            try:
                # Convert the text to a clean decimal number
                normalized_value = float(raw_qty)
            except (ValueError, TypeError):
                # If the data is garbage (e.g., "N/A"), we default to 0 to prevent a crash
                normalized_value = 0.0

            # 5. Save it securely to our master table
            EmissionRecord.objects.create(
                tenant=tenant,
                source_type='SAP',
                scope='SCOPE_1', # Fuel is typically Scope 1 (Direct)
                raw_data=row,    # We save the EXACT messy row here for the audit trail
                normalized_value=normalized_value,
                normalized_unit=row.get('Unit', row.get('Einheit', 'Unknown')),
                status='PENDING' # Goes to the analyst dashboard for review
            )
            records_created += 1

        return Response({"message": f"Successfully ingested {records_created} SAP records."}, status=status.HTTP_201_CREATED)
    # This creates a URL specifically for uploading Utility files
    @action(detail=False, methods=['post'])
    def upload_utility(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        tenant, _ = Tenant.objects.get_or_create(name="Acme Corp Enterprise")

        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        records_created = 0

        for row in reader:
            # Utility Reality Check: Look for usage or meter readings
            raw_usage = row.get('Usage', row.get('Meter_Reading', 0))
            raw_unit = row.get('Unit', 'kWh').strip().upper()
            
            try:
                usage_val = float(raw_usage)
            except (ValueError, TypeError):
                usage_val = 0.0

            # Normalization Engine: Convert MWh to kWh for a standardized database
            if raw_unit == 'MWH':
                normalized_value = usage_val * 1000
                normalized_unit = 'kWh'
            else:
                normalized_value = usage_val
                normalized_unit = 'kWh' # Defaulting to kWh for standard electricity

            # Save to master table
            EmissionRecord.objects.create(
                tenant=tenant,
                source_type='UTILITY',
                scope='SCOPE_2', # Electricity is Scope 2 (Indirect)
                raw_data=row,    # Preserves the weird billing periods/tariffs for the audit trail
                normalized_value=normalized_value,
                normalized_unit=normalized_unit,
                status='PENDING'
            )
            records_created += 1

        return Response({"message": f"Successfully ingested {records_created} Utility records."}, status=status.HTTP_201_CREATED)
    # This creates a URL specifically for uploading Travel JSON data
    @action(detail=False, methods=['post'])
    def upload_travel(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        tenant, _ = Tenant.objects.get_or_create(name="Acme Corp Enterprise")

        try:
            # Parse the JSON API mock
            data = json.load(file)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON format"}, status=status.HTTP_400_BAD_REQUEST)

        records_created = 0

        # Loop through the array of trips
        for item in data.get('trips', []):
            category = item.get('category', 'UNKNOWN').upper()
            raw_distance = item.get('distance_km', 0)
            
            try:
                normalized_value = float(raw_distance)
            except (ValueError, TypeError):
                normalized_value = 0.0

            # Logic check: If it's a flight but we have no distance (e.g., just airport codes), flag it!
            record_status = 'PENDING'
            if category == 'FLIGHT' and normalized_value == 0:
                record_status = 'FLAGGED'

            # Save to master table
            EmissionRecord.objects.create(
                tenant=tenant,
                source_type='TRAVEL',
                scope='SCOPE_3', # Travel is Scope 3 (Value Chain)
                raw_data=item,   # Preserves the raw airport codes for the audit trail
                normalized_value=normalized_value,
                normalized_unit='km',
                status=record_status
            )
            records_created += 1

        return Response({"message": f"Successfully ingested {records_created} Travel records."}, status=status.HTTP_201_CREATED)