# Source Research & Sample Data Justification

**1. SAP (Fuel & Procurement)**
* *Research:* Modeled as a CSV flat file. SAP exports frequently suffer from localized headers and inconsistent empty values. 
* *Sample Data:* Included German headers (`Buchungsdatum`, `Einheit`) and "N/A" strings.
* *Deployment Risk:* If a client changes their export variant in SAP GUI, the column index could shift, breaking hardcoded parsers. 

**2. Utility Data (Electricity)**
* *Research:* Modeled as a Facility Portal CSV export. Utilities notoriously mix units (kWh vs MWh) depending on the scale of the facility.
* *Sample Data:* Included a mix of kWh and MWh to demonstrate the backend's dynamic mathematical normalization engine.
* *Deployment Risk:* Billing periods often overlap calendar months (e.g., April 14 - May 13). Time-series queries would need to account for prorated daily usage.

**3. Corporate Travel (API)**
* *Research:* Modeled as a Navan/Concur JSON payload. The biggest issue with travel data is incomplete records (e.g., missing distances for multi-leg flights).
* *Sample Data:* Included a flight with missing distance data but valid airport codes.
* *Deployment Risk:* API rate limits from vendors, and the complexity of calculating great-circle distances from airport codes if the vendor API fails to provide the mileage.