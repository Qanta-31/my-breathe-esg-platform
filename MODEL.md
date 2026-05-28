# Data Model

## Philosophy

The model is built around a single normalized `EmissionRecord` table rather than separate tables per source type. This is a deliberate choice: in carbon accounting, the downstream consumer (an auditor, a reporting engine) doesn't care whether a data point came from SAP or a utility portal — they care about the activity value, its unit, its scope classification, and whether it's been reviewed.

Separate source-specific tables would mean every new data source requires schema changes, new serializers, and new frontend components. A single table with a `raw_data` JSON field preserves source fidelity without coupling the schema to any particular vendor format.

## Tables

### Tenant
| Field | Type | Purpose |
|-------|------|---------|
| id | BigAutoField | PK |
| name | CharField(255), unique | Client company name |
| created_at | DateTimeField | When the tenant was onboarded |

Every record belongs to exactly one tenant. This is the multi-tenancy boundary. In production, this would integrate with an auth system (tenant scoping via middleware or row-level security). For this prototype, it's a simple FK.

### IngestionBatch
| Field | Type | Purpose |
|-------|------|---------|
| id | BigAutoField | PK |
| tenant | FK → Tenant | Which client this batch belongs to |
| source_type | CharField(20) | SAP / UTILITY / TRAVEL |
| file_name | CharField(255) | Original filename as uploaded |
| ingested_at | DateTimeField (auto) | When this batch was processed |
| row_count | PositiveIntegerField | Total rows parsed |
| error_count | PositiveIntegerField | Rows that were flagged during parse |

This table answers the question: "Which file produced this row, and when was it ingested?" Without it, you can't trace a suspicious record back to its source file — a hard requirement for audit.

### EmissionRecord
| Field | Type | Purpose |
|-------|------|---------|
| id | BigAutoField | PK |
| tenant | FK → Tenant | Multi-tenancy |
| batch | FK → IngestionBatch (nullable) | Lineage tracking |
| source_type | CharField(20) | SAP / UTILITY / TRAVEL |
| scope | CharField(20) | SCOPE_1 / SCOPE_2 / SCOPE_3 |
| raw_data | JSONField | The exact, unmodified row from the source |
| normalized_value | Decimal(15,4) | The cleaned numeric value after unit conversion |
| normalized_unit | CharField(50) | Standardized unit (kWh, liters, km, nights) |
| original_unit | CharField(50) | Unit as it appeared in the raw source |
| description | CharField(255) | Human-readable label for the analyst |
| flag_reason | CharField(255) | Why this row was auto-flagged |
| status | CharField(20) | PENDING → FLAGGED → APPROVED → LOCKED |
| is_edited | BooleanField | Whether an analyst modified this post-ingestion |
| reviewed_by | CharField(100) | Who approved/locked it |
| reviewed_at | DateTimeField (nullable) | When the review action happened |
| created_at | DateTimeField (auto) | Row creation timestamp |
| updated_at | DateTimeField (auto) | Last modification timestamp |

## Design Decisions

**Why a single table instead of polymorphic models?**
Carbon accounting normalizes everything to activity data × emission factor = CO2e. The "activity data" is always: a numeric value, a unit, a scope, and a source. That's the same shape regardless of whether it came from SAP or a travel API. Polymorphism would add complexity without adding analytical value.

**Why store `raw_data` as JSON?**
Because source formats change. If SAP adds a column next quarter, or the travel API changes its schema, the raw_data field captures whatever arrived without requiring a migration. The normalized fields are what the system operates on; raw_data is the audit trail.

**Why `original_unit` alongside `normalized_unit`?**
An auditor needs to verify the conversion. If we only store "kWh" but the source said "MWh", there's no way to validate the ×1000 multiplication happened correctly. Both are stored.

**Why `IngestionBatch` as a separate table?**
Batch-level metadata (file name, timestamp, error rate) doesn't belong on every row. It's a natural grouping that enables questions like "show me everything from the May 15th SAP upload" or "which batch had the highest error rate?"

**Status workflow: PENDING → APPROVED → LOCKED**
- PENDING: Just ingested, awaiting analyst review
- FLAGGED: Auto-flagged by the parser (bad data) or manually flagged by analyst (suspicious)
- APPROVED: Analyst has reviewed and confirmed the data point
- LOCKED: Frozen for audit — no further modifications allowed

The LOCKED state is intentionally irreversible in this prototype. In production, only an admin with explicit justification should be able to unlock a record (with a full audit log entry).

## Scope Classification Logic

| Source | Default Scope | Rationale |
|--------|--------------|-----------|
| SAP — fuel materials | Scope 1 | Direct combustion of owned/controlled fuels |
| SAP — procurement (non-fuel) | Scope 3 | Purchased goods fall under value chain |
| Utility — electricity | Scope 2 | Purchased energy (location-based) |
| Travel — all categories | Scope 3 | Business travel is Scope 3 Category 6 |

## What's Missing (Production Gaps)

- **Row-level permissions**: Currently any API consumer can modify any tenant's data. Production needs tenant-scoped auth middleware.
- **Emission factor application**: This model stores activity data only. The multiplication by emission factors (e.g., kWh × grid carbon intensity) would happen in a downstream calculation service.
- **Versioning**: If an analyst edits a normalized_value, the old value is lost. Production would need a history table or Django-reversion.
- **Soft deletes**: Records are hard-deleted. Production should use a `deleted_at` field.
