from rest_framework import serializers
from .models import Tenant, IngestionBatch, EmissionRecord


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'


class IngestionBatchSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = IngestionBatch
        fields = '__all__'


class EmissionRecordSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    batch_file = serializers.CharField(source='batch.file_name', read_only=True, default='')

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'tenant', 'tenant_name', 'batch', 'batch_file',
            'source_type', 'scope', 'raw_data',
            'normalized_value', 'normalized_unit', 'original_unit',
            'description', 'flag_reason',
            'status', 'is_edited', 'reviewed_by', 'reviewed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
