# Source Research & Sample Data

For each of the three data sources: what I researched, what I learned, how I designed the sample data, and what would break in production.

---

## 1. SAP — Fuel & Procurement Data

### What I Researched
- SAP export mechanisms: IDoc (EDI format), OData (REST API on S/4HANA), BAPI/RFC (programmatic), and flat file exports (SE16, SQVI, or scheduled jobs via SM36)
- Real SAP table structures: EKPO (purchasing items), MSEG (material movements), BKPF/BSEG (accounting documents)
- SAP localization: column headers change based on the server's logon language (DE, EN, FR, etc.)
- Common data quality issues in SAP exports: empty cells instead of zeros, "N/A" strings in numeric fields, European date formats (DD.MM.YYYY), comma as decimal separator in German locales

### What I Chose
A **flat-file CSV export** resembling output from transaction SE16 on table MSEG (material document movements), filtered for fuel and procurement materials.

**Why this format:** In conversations with sustainability consultants and from reading implementation guides, the most common pattern for a new client onboarding is: "Our IT team will set up a scheduled report that drops a CSV on the shared drive every Monday." Live API integrations (OData) come later, if ever, because they require IT governance approval, security reviews, and SAP Basis team involvement.

### Sample Data Design

```csv
PlantID,Material,Buchungsdatum,Quantity,Einheit,CostCenter,PO_Number,Vendor
P001,Diesel Fuel,01.05.2023,500.50,Liters,CC-992,4500012345,Shell Deutschland GmbH
P001,Natural Gas,15.05.2023,N/A,m3,CC-992,4500012500,Stadtwerke München
P004,Office Paper (Recycled),25.05.2023,200,kg,CC-200,4500013000,Papier Union
```

Key realism choices:
- **Mixed German/English headers**: `Buchungsdatum` (posting date) and `Einheit` (unit) alongside English `Quantity` — this happens when the export template was created by a German admin but some columns were manually renamed
- **"N/A" in numeric fields**: SAP users sometimes type "N/A" when a meter reading isn't available, rather than leaving the cell empty
- **Empty quantity**: Row 10 has a blank quantity — represents a PO that was created but not yet goods-receipted
- **Non-fuel procurement**: Office paper and toner cartridges are included to test scope classification (these are Scope 3, not Scope 1)
- **German date format**: DD.MM.YYYY as SAP defaults in DE locale
- **Plant codes**: Meaningless without a lookup table (P001, P002, etc.) — this is realistic; plant codes are internal identifiers

### What Would Break in Production
1. **Column order shifts**: If the SAP admin changes the export variant, columns could reorder. Our DictReader approach handles this (it uses headers, not positions), but if headers themselves change, we'd need a mapping config per tenant.
2. **Character encoding**: SAP exports from German systems often use ISO-8859-1, not UTF-8. The `utf-8-sig` decode handles BOM but not full encoding mismatches.
3. **Volume**: A large manufacturing client might have 50,000+ material movements per month. Synchronous parsing would timeout.
4. **Duplicate detection**: Re-uploading the same file creates duplicate records. Production needs file-hash deduplication.

---

## 2. Utility Data — Electricity

### What I Researched
- How facilities teams get electricity data: utility portal downloads (most common), PDF bills (common but hard to parse), Green Button API (US-specific, low adoption), manual meter readings
- Utility portal CSV formats from providers like ConEd, PG&E, EDF, Enel, E.ON
- Common issues: mixed units (kWh vs MWh depending on meter size), billing periods that don't align with calendar months, estimated vs. actual readings, multiple meters per facility

### What I Chose
A **portal CSV export** — the kind a facilities manager downloads from their utility provider's business portal after logging in.

**Why this format:** PDF parsing (OCR) is unreliable and adds infrastructure complexity (Tesseract, cloud vision APIs). Green Button is US-only and requires utility provider cooperation. The CSV download is the lowest-friction path that works globally.

### Sample Data Design

```csv
Meter_ID,Billing_Period,Start_Date,End_Date,Usage,Unit,Tariff_Code,Facility
MTR-991,April 2023,2023-03-15,2023-04-14,1500,kWh,TRF-A,HQ Building A
MTR-992,April 2023,2023-03-20,2023-04-19,2.5,MWh,TRF-B,Warehouse North
MTR-993,April 2023,2023-04-01,2023-04-30,0,kWh,TRF-C,Vacant Unit 7
MTR-994,Q1 2023,2023-01-01,2023-03-31,45000,kWh,TRF-D,Data Center
```

Key realism choices:
- **Non-aligned billing periods**: Start/end dates show that "April 2023" actually covers March 15 – April 14. This is how real utility billing works — the meter read date determines the period, not the calendar.
- **Mixed units**: MTR-992 reports in MWh (large industrial meter) while others report in kWh. The parser normalizes everything to kWh.
- **Zero reading**: MTR-993 reports 0 kWh — could be a vacant unit or a meter fault. Auto-flagged for analyst review.
- **Quarterly reading**: MTR-994 covers a full quarter (data centers sometimes have quarterly billing). This is a single large number that might look suspicious without context.
- **Tariff codes**: Included because they affect cost allocation, even though we don't use them for carbon calculation.

### What Would Break in Production
1. **Billing period overlap**: If two consecutive CSVs have overlapping periods (e.g., the utility re-issues a corrected bill), we'd double-count. Production needs period-aware deduplication.
2. **Estimated readings**: Some utilities mark readings as "E" (estimated) vs "A" (actual). We don't distinguish these — an estimated reading that gets corrected later would need a reconciliation workflow.
3. **Multiple utilities per site**: A facility might have separate electricity, gas, and water meters from different providers, each with different CSV formats. Our parser assumes a single format.
4. **Time-series alignment**: For Scope 2 reporting, you need to align consumption with the correct grid emission factor for that time period. Our model stores the raw period but doesn't do temporal alignment.

---

## 3. Corporate Travel — Flights, Hotels, Ground Transport

### What I Researched
- Concur (SAP) Travel API: expense reports with trip segments, each having category, origin/destination, dates, amounts
- Navan (formerly TripActions) API: booking-level data with itinerary legs
- Common data gaps: missing distances (only airport codes provided), no cabin class distinction in older systems, hotel stays without location granularity
- GHG Protocol Scope 3 Category 6 (Business Travel): requires distance × emission factor, with factors varying by mode, distance band, and cabin class

### What I Chose
A **JSON payload** structured like a Navan reporting API response — an array of trip objects, each with a category and category-specific fields.

**Why JSON (not CSV):** Travel data is inherently hierarchical. A single business trip has multiple legs (flight out, hotel, ground transport, flight back). JSON represents this naturally. CSV would require either one row per leg (losing the trip grouping) or denormalized wide rows (one column per possible field across all categories).

**Why file upload (not live API pull):** For a prototype, simulating the API response as a JSON file upload is functionally equivalent. In production, you'd have a scheduled job that calls the Navan/Concur API and feeds the response into the same parsing logic.

### Sample Data Design

```json
{
    "trips": [
        {
            "trip_id": "T-2023-100",
            "category": "Flight",
            "route": "JFK-LHR",
            "cabin_class": "Economy",
            "distance_km": 5554
        },
        {
            "trip_id": "T-2023-101",
            "category": "Flight",
            "route": "LHR-CDG",
            "distance_km": null,
            "notes": "Short-haul connector — distance not provided by booking system"
        },
        {
            "trip_id": "T-2023-106",
            "category": "Rail",
            "route": "Tokyo Station - Osaka Station",
            "distance_km": 515,
            "mode": "Shinkansen"
        }
    ]
}
```

Key realism choices:
- **Null distance**: The LHR-CDG flight has `distance_km: null`. This is extremely common — booking systems often only store airport codes, not distances. The parser flags this for manual resolution (or geocoding).
- **Multiple categories**: Flights, hotels, ground transport, and rail are all present. Each has different normalization logic (flights → km, hotels → nights, ground → km).
- **Cabin class**: Included because emission factors differ significantly (business class ≈ 3× economy due to seat space allocation). Not all trips have it — older bookings might not.
- **Employee and cost center**: Included for traceability but not used in carbon calculation.
- **Rail travel**: Included because it's a common alternative to short-haul flights in Europe/Japan, with much lower emission factors.

### What Would Break in Production
1. **Distance geocoding**: For flights with only airport codes, you need a lookup table (IATA code → lat/lon) and great-circle distance calculation. The OpenFlights database has this, but it's a separate integration.
2. **Cabin class emission factors**: Business class on a long-haul flight has ~3× the emission factor of economy (DEFRA methodology). We store cabin_class but don't apply factors.
3. **API rate limits**: Concur/Navan APIs have rate limits. A large enterprise with 10,000 employees might have 50,000 trips/month. Pagination and retry logic are essential.
4. **Radiative forcing multiplier**: Aviation emissions at altitude have a greater warming effect than ground-level emissions. The GHG Protocol recommends a 1.9× multiplier for flights. We don't apply this.
5. **Hotel emission factors**: These vary enormously by country, hotel class, and whether the hotel reports its own energy data. DEFRA provides per-night factors by country, but they're rough estimates.
