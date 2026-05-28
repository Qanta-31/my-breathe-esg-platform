from django.db import models
from django.db.models import JSONField

class Tenant(models.Model):
    """
    Handles Multi-Tenancy. Every record will belong to a specific client company.
    """
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class EmissionRecord(models.Model):
    """
    The master table for all ingested data.
    """
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1 (Direct)'),
        ('SCOPE_2', 'Scope 2 (Indirect - Utilities)'),
        ('SCOPE_3', 'Scope 3 (Value Chain - Travel/Procurement)'),
    ]

    SOURCE_CHOICES = [
        ('SAP', 'SAP ERP (Fuel/Procurement)'),
        ('UTILITY', 'Utility Portal (Electricity)'),
        ('TRAVEL', 'Travel API (Concur/Navan)'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('FLAGGED', 'Suspicious / Flagged'),
        ('APPROVED', 'Approved by Analyst'),
        ('LOCKED', 'Locked for Audit'),
    ]

    # Multi-tenancy
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='records')
    
    # Categorization
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    
    # Source of Truth & Audit Trail
    raw_data = JSONField(help_text="The exact, unedited row as it arrived from the source")
    is_edited = models.BooleanField(default=False, help_text="Has an analyst modified this after ingestion?")
    
    # Normalization
    normalized_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    normalized_unit = models.CharField(max_length=50, null=True, blank=True, help_text="e.g., kg CO2e, kWh")
    
    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Timestamps for auditing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.name} - {self.source_type} - {self.status}"