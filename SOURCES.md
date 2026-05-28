# Inbound Data Sources Reference (SOURCES.md)

This document describes the research, realistic formats, and failure points for each of the three ingestion sources integrated into **Breathe ESG Ingestor**.

---

## SOURCE 1: SAP (ERP Procurement & Fuel Exports)

### 1. Research & Industry Reality
In large enterprises, SAP is the central system of record for inventory movements (Material Documents) and financial accounting (accounting documents).
- **German Column Headers**: SAP was developed in Germany, and many standard databases preserve the original German column names (e.g. `Matnr` for Material Number, `Werks` for Plant, `Menge` for Quantity, `Meins` for Unit of Measure, `Datum` for Date, `Belnr` for Bill/Document Number).
- **Decimal Commas & Thousands Separator**: European exports use a comma `,` for decimals and a dot `.` for thousands (e.g., `12.500,50` instead of `12,500.50`).
- **Standard SAP Units**: SAP uses standard ISO-derived units (e.g., `L` for Liters, `KG` for Kilograms, `M3` for Cubic Meters, `TO` for Tonnes).

### 2. Sample Data Design
Our generated `sap_seed.csv` reflects these features:
- Columns: `Belnr`, `Matnr`, `Werks`, `Menge`, `Meins`, `Datum`, `Kostl`.
- Decimals: Formatted as `"1.250,50"`.
- Dates: Formatted as `DD.MM.YYYY` (e.g., `15.01.2026`).
- Materials: Seeded with 20 materials, separating fuels (`MAT001` - `MAT006`) from procurement goods (`MAT101` - `MAT120`).

### 3. Production Failure Modes (What would break?)
- **Custom Z-Fields**: Many companies implement custom fields (e.g., `ZZ_MENGE`) instead of standard column names.
- **Varying Date Formats**: If an administrator changes their locale settings, SAP may export dates in `YYYY-MM-DD` or `YYYY/MM/DD`, breaking our `strptime("%d.%m.%Y")` parser.
- **Multiple Units for the Same Material**: If a factory records fuel in gallons but the catalog specifies Liters, the parser must convert units relative to material density.

---

## SOURCE 2: Utility Electricity (Discom Billing Reports)

### 1. Research & Industry Reality
Utility portals globally (e.g., PG&E, Engie, EDF) let commercial clients download CSV billing histories.
- **Billing Cycles**: Bills rarely align with clean calendar months (e.g., a cycle might run from November 18 to December 17).
- **Energy Units**: Consumption values are usually listed in `kWh` for smaller sites, but energy-heavy manufacturing plants use `MWh` (Megawatt-hours) or `kVAh` (apparent energy).
- **Cumulative Readings**: Some providers supply cumulative meter readings (e.g., `Previous Reading: 10,000`, `Current Reading: 12,000`) instead of direct usage, requiring delta calculations.

### 2. Sample Data Design
Our generated `utility_seed.csv` reflects these features:
- Columns: `Meter ID`, `Start Date`, `End Date`, `Consumption`, `Current Reading`, `Previous Reading`, `Unit`, `Site`, `Tariff`.
- Mixed units: Ingestion supports `kWh`, `MWh` (scaled by 1000), and `kVAh` (scaled by 0.9 Power Factor).
- Reading Types: Evaluates direct `Consumption` values and calculates delta from `Current Reading` - `Previous Reading` columns.

### 3. Production Failure Modes (What would break?)
- **Meter Replacements**: If a physical meter is replaced at a site, the cumulative reading resets to zero. Our cumulative delta lookup would calculate a massive negative usage (which we flag as a rollover but requires human adjustment).
- **Reactive Energy**: Large plants are billed on reactive energy (kVARh) and peak demand (kW). Simply multiplying apparent energy by a static `0.9` power factor is an approximation that can introduce errors under variable loads.

---

## SOURCE 3: Corporate Travel (Concur/Navan Exports)

### 1. Research & Industry Reality
Corporate travel reports consolidate flights, hotel bookings, and ground logistics.
- **PII Protection**: Storing raw employee names or IDs violates data privacy policies (GDPR/CCPA). Hashing is necessary.
- **Flight Distances**: Many flight exports list only origin and destination IATA codes (e.g., `LHR`, `JFK`) without recording distances. Great-circle distance calculation is needed.
- **Inconsistent Categories**: Different travel booking systems use different category strings for the same travel mode (e.g., `Flight`, `Air`, `Flights`).

### 2. Sample Data Design
Our generated `travel_seed.csv` reflects these features:
- Columns: `Trip ID`, `Category`, `Origin`, `Destination`, `Distance`, `Distance Unit`, `Cabin Class`, `Check-in Date`, `Check-out Date`, `Nights`, `Employee ID`, `Cost Center`.
- Normalization: Casing-agnostic alias mapping (e.g. `Air` -> `flight`, `Rental` -> `car_rental`).
- PII Protection: Hashing Employee IDs using SHA-256 with a salt, replacing raw values in `raw_data`.
- IATA fallbacks: Calculates missing distances using the Haversine formula on coordinates.

### 3. Production Failure Modes (What would break?)
- **Multi-leg Trips**: If a trip has layovers (e.g., `JFK -> LHR -> DEL`), it is often exported as a single row with comma-separated IATA codes. Our parser expects simple pairs and would fail.
- **Airport Coordinates**: If an employee flies out of a small regional airport not in our 50-airport lookup table, the row is flagged and falls back to a distance of 0.0, requiring manual distance entry.
