# Deliberate Omissions & Tradeoffs (TRADEOFFS.md)

This document outlines the three key engineering compromises made in **Breathe ESG Ingestor v1** and describes the architectural patterns required for production scaling.

---

## 1. Synchronous File Ingestion (vs. Celery/Redis Async Tasks)

### What was built
- Ingestion runs synchronously inside the `FileUploadView` thread. When a user uploads a file, the HTTP connection is kept open until the entire file is parsed, records are validated, and database inserts are committed.

### Why it is fine for the prototype
- For prototype seed files (50–100 rows), database insertion and parsing finish in under 300ms. Keep-alive timeouts are not a risk, and setup complexity is minimized because we do not require extra infrastructure processes (Redis, Celery workers) running locally.

### What breaks at enterprise scale
- If a client uploads a yearly utility export containing **100,000+ rows**, processing will exceed the web server's request timeout (typically 30–60 seconds). The connection will terminate, leaving the batch in a corrupted, half-ingested state. It also blocks the web server's event loop, degrading dashboard responsiveness.

### Production Solution
- **Async Workers**: Implement a task queue (Celery + Redis/SQS).
- **Non-blocking Ingestion Flow**:
  1. The API receives the file, saves it to secure storage (e.g. AWS S3), spawns a Celery task, and immediately returns a `202 Accepted` response with the `batch_id` and status `PROCESSING`.
  2. The Celery worker downloads the file, parses it, and writes chunks to the database.
  3. The frontend polls `/api/batches/:id/` or listens to a WebSocket event to show a real-time progress bar.

---

## 2. Activity Data Ingestion Only (vs. Direct CO2e Emissions Calculation)

### What was built
- The system stores normalized activity data only (Liters of Diesel, kWh of Electricity, kilometers flown). It does **not** compute Carbon Dioxide Equivalent (CO2e) emissions.

### Why it is the right boundary for v1
- Storing accurate, audited activity values is the critical prerequisite for any carbon reporting. By separating ingestion from calculations, we preserve the audit trail. In calculations, emission factors (e.g. DEFRA, EPA, Ecoinvent) change annually and vary by geographic grid, so applying them during ingestion creates rigid data structures that cannot be recalculated if emission factors are updated retrospectively.

### Production Solution
- **Decoupled Calculation Engine**:
  - Store activity records as the "source of truth".
  - Implement a secondary **Calculations Engine** that runs asynchronously.
  - This engine looks up the appropriate emission factor based on:
    1. Activity category (e.g., electricity, business flight).
    2. Geographic location (e.g., Germany grid vs US grid).
    3. Year of the activity (matching factors for 2025 vs 2026).
  - This ensures that if the EPA publishes an updated 2026 factor, we can trigger a recalculation across the database without modifying the underlying raw activity records.

---

## 3. Hardcoded Plant/Meter Mappings (vs. Dynamic Mapping UI)

### What was built
- SAP plant codes (`Werks`) and utility meter names are resolved to facility names using hardcoded dictionaries (`PLANT_MAPPING` and `UTILITY_SITE_MAPPING`) inside `constants.py`.

### Why it is fine for the prototype
- Simulates the mapping lookup logic and provides clean, human-readable facility names on the review dashboard without the overhead of creating mapping views.

### What breaks at enterprise scale
- Every client has distinct plant numbering schemes, and new sites are opened constantly. Relying on code changes to update mapping tables is unsustainable and blocks operations when unmapped codes appear.

### Production Solution
- **Mapping Tables & Fallback UI**:
  - Design a database model `FacilityMapping` with fields: `raw_identifier`, `facility_fk`, `source_type`.
  - When the parser encounters an unknown `Werks` or `Meter ID`, it creates an `ActivityRecord` in `PENDING_MAPPING` status.
  - A dedicated **Mapping Dashboard** in the frontend shows all unmapped identifiers. The analyst can select a corporate facility from a dropdown to link them.
  - Once mapped, the system saves the mapping rule and automatically reprocessing any pending records.
