# Tradeoffs: What I Deliberately Did Not Build

---

## 1. Authentication & Role-Based Access Control

**What it would look like:** JWT or session-based auth, with roles like `analyst`, `admin`, `auditor`. Analysts can approve but not lock. Auditors can view locked records but not modify. Admins can unlock.

**Why I didn't build it:** 
- It's orthogonal to the core problem (data ingestion and normalization)
- Adding auth would consume 20-30% of the time budget on boilerplate (user model, login UI, token refresh, permission decorators) that doesn't demonstrate domain understanding
- The `reviewed_by` field on EmissionRecord is a placeholder for where auth would plug in — the model is ready for it

**What breaks without it:** Any user can approve any tenant's data. In production, this is a hard blocker before going live.

---

## 2. Asynchronous Processing (Celery + Redis)

**What it would look like:** File upload hits the API → file is stored in S3 → a Celery task picks it up → parses in the background → notifies the frontend via WebSocket or polling.

**Why I didn't build it:**
- The sample files are <100 rows. Synchronous processing completes in <200ms.
- Adding Celery requires Redis (or RabbitMQ), a worker process, and significantly complicates deployment on Render's free tier
- The architecture doesn't preclude it — the upload endpoints could be refactored to enqueue a task instead of processing inline, without changing the model or frontend

**What breaks without it:** A 50,000-row SAP export would timeout the HTTP request (Render's 30s limit). The user would get a 504 with no feedback. Production absolutely needs this.

---

## 3. Emission Factor Calculation

**What it would look like:** After normalization, multiply activity data by the appropriate emission factor:
- Diesel: 2.68 kg CO2e per liter (DEFRA 2023)
- Electricity: varies by grid (0.4 kg CO2e/kWh for India, 0.05 for France)
- Flights: varies by distance band and cabin class

**Why I didn't build it:**
- Emission factors are a separate domain with their own complexity (which factor database? DEFRA? EPA? GHG Protocol? Client-specific?)
- The assignment asks for ingestion, normalization, and review — not the full carbon calculation pipeline
- Mixing ingestion and calculation in the same service violates separation of concerns
- The `normalized_value` + `normalized_unit` fields are specifically designed to be the *input* to a downstream emission factor engine

**What breaks without it:** The dashboard shows activity data (liters, kWh, km) but not CO2e. An auditor would need the CO2e values. This would be the next service to build.

---

## Additional Things I Scoped Out

**PDF bill parsing:** Utility bills often arrive as PDFs. Parsing these requires OCR (Tesseract, AWS Textract, or similar). Too unreliable and infrastructure-heavy for a prototype. I chose the CSV portal export path instead.

**Airport code geocoding:** When a flight has no distance (just airport codes like LHR-CDG), you need a lookup table or API to calculate great-circle distance. I flag these records instead of guessing. In production, you'd integrate the OpenFlights database or a geocoding API.

**Multi-currency normalization:** SAP procurement data often includes costs in different currencies. I ignored the financial dimension entirely and focused on physical quantities (liters, kg, kWh) because carbon accounting operates on physical units, not monetary ones.

**Data deduplication:** If the same file is uploaded twice, you get duplicate records. Production would need batch-level deduplication (hash the file, check if we've seen it before) or row-level deduplication (composite unique constraints on source fields).
