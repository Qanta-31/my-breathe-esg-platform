# Data Model Architecture

The core philosophy of this data model is **Source-of-Truth Preservation combined with Strict Normalization.**

Instead of creating disparate, fractured tables for every new data source, the architecture utilizes a single master `EmissionRecord` table. 

**Key Features:**
* **Multi-Tenancy:** Handled via a `Tenant` foreign key. Every ingested row is strictly bound to a client company, ensuring data isolation.
* **Scope Categorization:** Mapped via the `scope` field (Scope 1 for SAP Fuel, Scope 2 for Utility Electricity, Scope 3 for Travel).
* **Source-of-Truth Tracking:** The absolute, unedited row as it arrived from the client is saved securely in a `raw_data` JSON field. If an auditor ever questions a normalized value, we have cryptographic-level proof of the original input. 
* **Unit Normalization:** We extract only the mathematical values and standardize the units (e.g., converting MWh to kWh on the fly) into the `normalized_value` and `normalized_unit` fields.
* **Audit Trail:** The `is_edited` boolean and the `status` workflow (PENDING, FLAGGED, APPROVED) explicitly track the lifecycle of the data point and any analyst intervention.