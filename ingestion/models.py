from django.db import models
from django.db.models import JSONField


class Tenant(models.Model):
    """
    Multi-tenancy: every record belongs to a specific client company.
    In production this would tie into an auth system; here it's a simple FK.
    """
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    """
    Groups records that arrived together in a single upload/API pull.
    Provides source-of-truth tracking: which file, when, how many rows.
    """
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=20)
    file_name = models.CharField(max_length=255, blank=True, default='')
    ingested_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.tenant.name} | {self.source_type} | {self.file_name} ({self.ingested_at:%Y-%m-%d %H:%M})"


class EmissionRecord(models.Model):
    """
    The master normalized table for all ingested emissions/activity data.
    One row = one activity data point from any source.
    """
    SCOPE_CHOICES = [
        ('SCOPE_1', 'Scope 1 (Direct)'),
        ('SCOPE_2', 'Scope 2 (Indirect - Energy)'),
        ('SCOPE_3', 'Scope 3 (Value Chain)'),
    ]

    SOURCE_CHOICES = [
        ('SAP', 'SAP Flat File (Fuel/Procurement)'),
        ('UTILITY', 'Utility Portal CSV (Electricity)'),
        ('TRAVEL', 'Travel Platform JSON (Flights/Hotels/Ground)'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('FLAGGED', 'Suspicious / Flagged'),
        ('APPROVED', 'Approved by Analyst'),
        ('LOCKED', 'Locked for Audit'),
    ]

    # --- Multi-tenancy ---
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='records')

    # --- Lineage / Source-of-Truth ---
    batch = models.ForeignKey(
        IngestionBatch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='records',
        help_text="The upload batch that produced this row"
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    raw_data = JSONField(help_text="The exact, unmodified row as received from the source")

    # --- Normalization ---
    normalized_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    normalized_unit = models.CharField(
        max_length=50, null=True, blank=True,
        help_text="Standardized unit after conversion (kWh, liters, km, nights)"
    )
    original_unit = models.CharField(
        max_length=50, blank=True, default='',
        help_text="The unit as it appeared in the raw source before normalization"
    )

    # --- Categorization metadata ---
    description = models.CharField(max_length=255, blank=True, default='',
                                   help_text="Human-readable label, e.g. 'Diesel Fuel', 'JFK-LHR Flight'")
    flag_reason = models.CharField(max_length=255, blank=True, default='',
                                   help_text="Why this row was flagged (missing data, parse error, outlier)")

    # --- Workflow ---
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_edited = models.BooleanField(default=False, help_text="Has an analyst modified this after ingestion?")
    reviewed_by = models.CharField(max_length=100, blank=True, default='',
                                   help_text="Analyst who approved/locked this record")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant.name} | {self.source_type} | {self.description or 'N/A'} | {self.status}"