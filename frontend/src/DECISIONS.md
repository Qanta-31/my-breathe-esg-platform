# Architectural Decisions & Ambiguity Resolution

* **Handling SAP Ambiguity:** SAP exports can take many forms (IDocs, OData). I chose to model a **Batch CSV Flat File** export. Why? Because in legacy enterprise environments, scheduled flat-file drops via SFTP are still overwhelmingly the standard for procurement data. 
* **Fallback Logic:** I implemented German-to-English fallback parsing (e.g., looking for `Quantity`, then falling back to `Menge`) because SAP column headers are notoriously localized based on the server configuration.
* **Graceful Degradation:** Instead of rejecting entire files when a single row has a string like "N/A" instead of a number, the ingestion engine defaults the mathematical value to `0.0` but flags the record status, allowing the analyst to fix it without halting the pipeline.
* **Questions for the PM:** 1. What is our target SLA for ingestion? (Does this need to be real-time, or is a nightly batch job acceptable?)
  2. How do we want to handle carbon emission factors (e.g., multiplying the normalized kWh by the local grid's carbon intensity)? Should that live in this microservice or a downstream computation engine?