# Breathe ESG Ingestor & Auditor

**Breathe ESG Ingestor** is a production-quality enterprise ESG (Environmental, Social, and Governance) data ingestion, normalization, and audit platform. It allows corporate teams to import raw activity files from multiple supply chain and operations sources, normalizes them into a unified audit-ready schema, and provides a review dashboard for sustainability analysts.

---

## 🚀 Key Features

- **Multi-Tenant Architecture**: Complete data isolation. All querysets are implicitly filtered by tenant header context (`X-Tenant-Slug`), preventing cross-tenant leakage.
- **Three Realistic Data Sources**:
  - **SAP (Procurement & Fuel)**: Ingests German column names, DD.MM.YYYY dates, European decimal commas (`1.234,56`), plant code lookups, and maps material categories to Scope 1 vs Scope 3.
  - **Utility Portal (Electricity)**: Converts energy units (kWh, MWh, kVAh), calculates consumption from cumulative readings, and flags rows with missing baselines (Scope 2).
  - **Corporate Travel (Concur/Navan)**: Anonymizes Employee IDs via SHA-256 hashing, normalizes categories, derives nights, and fallback calculates flight distance using the Haversine formula on coordinates (Scope 3).
- **Interactive Review Dashboard**: An elegant dark-themed UI featuring:
  - Metric summary cards with Scope totals.
  - Paginated data tables (50 rows/page) with inline actions (Approve, Reject, Flag).
  - Audit timeline modal showing detail states, diffs, and raw verbatim JSON.
- **Immutable Lock Enforcement**: Once a record is Approved or Rejected, it is locked (`is_locked=True`). The Django REST serializer validates this status and blocks any subsequent edits.

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.11+
- Node.js v20+ & npm

### 1. Installation
Clone the repository, initialize the virtual environment, and install dependencies:
```bash
# Setup backend dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup Database & Seed Data
Generate the database schema and seed it with pre-computed history and local CSV test files:
```bash
# Run migrations
python backend/manage.py migrate

# Seed database and generate test CSVs in seed_data/
python backend/manage.py seed_esg_data
```

### 3. Run the Application
Run the Django server (which serves both the REST API and the compiled React frontend):
```bash
python backend/manage.py runserver
```
Visit **[http://localhost:8000/](http://localhost:8000/)** in your browser. The frontend is automatically logged in as the analyst user.

### 4. Running Tests
Run the automated test suite covering Haversine distance, German parsing formats, cumulative readings, hashing, and audit logs:
```bash
python backend/manage.py test records
```

---

## 📂 Project Structure & Reference Documentation

Detailed architectural analyses are provided in the following reference documents:
- 📊 **[MODEL.md](MODEL.md)**: Database schemas, field choices, signals, and locking behavior.
- 📐 **[DECISIONS.md](DECISIONS.md)**: Justifications for CSV files, billing period overlaps, and PM design questions.
- ⚖️ **[TRADEOFFS.md](TRADEOFFS.md)**: Deliberate omissions (async queues, CO2e factors, and mapping pages) and their scaling costs.
- 🔍 **[SOURCES.md](SOURCES.md)**: Research details on real-world SAP, utility, and travel exports.
- 📦 **[Dockerfile](Dockerfile)**: Multi-stage Docker config to compile Vite assets and host both layers in a single container.
