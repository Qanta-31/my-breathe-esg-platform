from django.contrib import admin
from .models import Tenant, IngestionBatch, EmissionRecord


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')


@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'source_type', 'file_name', 'row_count', 'error_count', 'ingested_at')
    list_filter = ('source_type', 'tenant')


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'source_type', 'scope', 'description', 'normalized_value', 'normalized_unit', 'status', 'created_at')
    list_filter = ('status', 'source_type', 'scope', 'tenant')
    search_fields = ('description', 'flag_reason')
    readonly_fields = ('raw_data', 'created_at', 'updated_at')
