from rest_framework import serializers
from .models import Tenant, EmissionRecord

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'

class EmissionRecordSerializer(serializers.ModelSerializer):
    # This extra line pulls the actual name of the company so our frontend 
    # doesn't just get a meaningless ID number (like Tenant #1)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = '__all__'