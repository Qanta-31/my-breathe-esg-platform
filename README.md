# Breathe ESG — Data Ingestion & Review Platform

A Django REST + React prototype that ingests emissions data from three source types (SAP, Utility, Travel), normalizes it, and surfaces an analyst review dashboard for approval before audit lock.

---

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Git

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/my-breathe-esg-platform.git
cd my-breathe-esg-platform
```

### 2. Backend (Django)

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create a superuser (optional, for Django admin)
python manage.py createsuperuser

# Start the backend server
python manage.py runserver
```

The API will be available at **http://localhost:8000/api/**

Django admin at **http://localhost:8000/admin/**

### 3. Frontend (React)

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at **http://localhost:5173/**

### 4. Configure the API URL

By default the frontend points to the deployed Render backend. For local development, create/edit `frontend/.env`:

```
VITE_API_URL=http://localhost:8000/api
```

Then restart the frontend dev server.

---

## Usage

### Uploading Data

1. Open the dashboard at http://localhost:5173
2. Use the upload buttons at the top:
   - **Upload SAP CSV** — use `ingestion/sap_export.csv` as a sample
   - **Upload Utility CSV** — use `ingestion/utility_bill.csv` as a sample
   - **Upload Travel JSON** — use `ingestion/travel_api.json` as a sample
3. Records will appear in the table below

### Reviewing Data

- **Pending** records can be Approved or Flagged
- **Flagged** records show the reason and can still be Approved
- **Approved** records can be Locked for audit (irreversible)
- **Locked** records are frozen — no further changes allowed
- Click **▼ Raw** to inspect the original source data for any record

### Filtering

Use the dropdowns to filter by:
- Source type (SAP / Utility / Travel)
- Status (Pending / Flagged / Approved / Locked)
- Scope (1 / 2 / 3)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/records/` | List all records (supports `?source_type=`, `?status=`, `?scope=` filters) |
| GET | `/api/records/{id}/` | Get a single record |
| POST | `/api/records/upload_sap/` | Upload SAP CSV file |
| POST | `/api/records/upload_utility/` | Upload Utility CSV file |
| POST | `/api/records/upload_travel/` | Upload Travel JSON file |
| POST | `/api/records/{id}/approve/` | Approve a record |
| POST | `/api/records/{id}/flag/` | Flag a record (body: `{"reason": "..."}`) |
| POST | `/api/records/{id}/lock/` | Lock an approved record for audit |
| GET | `/api/batches/` | List all ingestion batches |
| GET | `/api/tenants/` | List all tenants |

---

## Deployment (Render)

The app is configured for Render deployment:

1. **Backend** — Create a Web Service pointing to the repo root
   - Build command: `./build.sh`
   - Start command: `gunicorn config.wsgi:application`
   - Environment variables: `SECRET_KEY`, `RENDER=true`

2. **Frontend** — Create a Static Site pointing to `frontend/`
   - Build command: `npm install && npm run build`
   - Publish directory: `dist`
   - Environment variable: `VITE_API_URL=https://<your-backend>.onrender.com/api`

---

## Project Structure

```
my-breathe-esg-platform/
├── config/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── ingestion/              # Django app — models, views, parsers
│   ├── models.py           # Tenant, IngestionBatch, EmissionRecord
│   ├── views.py            # Upload endpoints + workflow actions
│   ├── serializers.py
│   ├── admin.py
│   ├── sap_export.csv      # Sample SAP data
│   ├── utility_bill.csv    # Sample utility data
│   └── travel_api.json     # Sample travel data
├── frontend/               # React + Vite dashboard
│   ├── src/
│   │   ├── App.jsx         # Main dashboard component
│   │   ├── App.css         # Dashboard styles
│   │   └── main.jsx
│   ├── .env                # API URL config
│   └── package.json
├── MODEL.md                # Data model documentation
├── DECISIONS.md            # Ambiguity resolution log
├── TRADEOFFS.md            # What was deliberately not built
├── SOURCES.md              # Source research & sample data justification
├── requirements.txt        # Python dependencies (pinned)
├── Procfile                # Render process config
├── build.sh                # Render build script
└── manage.py
```

---

## Sample Data Files

The `ingestion/` folder contains realistic sample files ready to upload:

- **sap_export.csv** — 10 rows mimicking an SAP SE16 flat-file export with German headers, N/A values, and mixed fuel/procurement materials
- **utility_bill.csv** — 7 rows with non-aligned billing periods, mixed kWh/MWh units, and a zero reading
- **travel_api.json** — 8 trips (flights, hotels, ground, rail) with a missing-distance flight that gets auto-flagged
