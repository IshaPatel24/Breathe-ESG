# Architectural Decisions & Defenses (DECISIONS.md)

This document defends the design and parser decisions made for the **Breathe ESG Ingestor** application.

---

## 1. Ingestion Channel Decisions & Defenses

### Source 1: SAP (Flat Files vs. IDoc XML / OData API)
- **Decision**: Flat file upload (.csv or IDoc-style .txt export).
- **Defense**: While SAP provides OData REST APIs and SOAP-based BAPIs, enterprise IT departments rarely open direct inbound/outbound ports to third-party sustainability applications due to strict security guidelines and risk mitigation. Standard IDoc XML exports are complex and have nested schemas that are highly custom to each SAP installation. CSV flat file exports are the universal handoff format because they are easy for SAP administrators to set up as automated nightly folder dumps, keeping integration tractable and highly realistic.

### Source 2: Utility Electricity (CSV vs. PDF Parsing / Green Button API)
- **Decision**: Customer portal CSV export uploads.
- **Defense**: Many sustainability apps try to use OCR/PDF scrapers (like Tabula or custom LLM prompts) to parse raw utility invoices. However, utility invoice formats change frequently, and billing layouts vary by regional provider, making PDF scrapers fragile and prone to silent failures. Direct API integration (like Green Button) is mostly limited to US utilities and rare globally. Portal CSV exports represent the sweet spot: they provide structured billing periods, meter IDs, and consumption metrics in a predictable, machine-readable format.

### Source 3: Corporate Travel (CSV vs. Navan/Concur API Integration)
- **Decision**: Travel manager CSV export uploads.
- **Defense**: While Concur and Navan provide robust REST APIs, establishing direct API connections requires corporate client OAuth approvals, API token provisioning, and custom developer accounts, which cannot be easily set up or tested in a sandbox or internship assignment. In practice, travel coordinators download travel reports as CSVs from their portal and hand them over, making CSV ingestion the most realistic and immediately testable delivery vector.

---

## 2. Business Rules & Logic Resolutions

### Handling Billing Periods Straddling Calendar Months
- **Problem**: Utility bills rarely align to neat calendar months (e.g. billing from Dec 18th to Jan 17th). Carbon reporting requires data allocated by calendar month.
- **Resolution**:
  - We store the raw dates (`period_start`, `period_end`) on the `ActivityRecord` verbatim to preserve the audit trail.
  - In a production calculations service, we implement a **pro-rata allocation algorithm** that splits the activity value based on the number of days belonging to each month. E.g. 13 days allocated to December and 17 days to January. This keeps data ingestion simple and accurate, leaving calculations to the downstream reporting layers.

### Handling Missing Flight Distances
- **Problem**: Corporate travel reports often miss flight distances, listing only origin and destination IATA codes.
- **Resolution**:
  - We implemented a **Great-Circle Distance Fallback** using the **Haversine Formula**.
  - We hardcoded a coordinate dictionary containing 50 major global airports (JFK, LHR, CDG, HND, SIN, etc.).
  - If a flight record is missing distance but has valid IATA codes, the parser computes the great-circle distance in kilometers.
  - If an IATA code is not in our dictionary, the row is **not** discarded; it is successfully imported but set to `FLAGGED` status with a reason `"Unknown IATA codes for distance fallback"`. This flags the record for manual analyst review in the UI instead of failing the batch.

---

## 3. Key Questions for the Product Manager (PM)

To move this application closer to production, we would present the following questions to the PM:

1. **Multi-Currency and Cost Context**:
   - *"Do clients always send data in the same currency? Some SAP and travel exports include costs. Do we need a currency exchange lookup service, or should we store all cost columns raw and ignore them for emissions scope reporting?"*
2. **Plant and Facility Mapping UI**:
   - *"Currently, plant codes (Werks) and utility Site IDs are mapped to facility names using hardcoded dictionaries. Since facilities change, should we build a Mapping UI where analysts can link unmapped site names/codes to corporate facilities interactively when an upload has unmapped entries?"*
3. **Audit Lock Irreversibility**:
   - *"Once a record is APPROVED or REJECTED, it is locked (`is_locked=True`) and cannot be edited. Is this lock irreversible for all users, or should we support a 'Super-Auditor' role that can unlock records to fix post-approval data entry errors?"*
4. **Anonymization and Verification**:
   - *"We are hashing Employee IDs using SHA-256 with a salt to protect PII. Does the sustainability manager need a way to de-anonymize the ID during audits to verify actual travel expenses, or is the one-way hash sufficient?"*
