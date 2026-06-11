# SpareTrack - Laptop Spare Parts Inventory Management System

SpareTrack is a FastAPI backend for uploading laptop spare parts Excel/CSV files, enriching part details, checking latest market prices, tracking price history, and generating processed Excel files.

## Features

- JWT authentication
- Brand CRUD
- Upload Excel/CSV against brand
- Detect part number column automatically
- Part master table
- Price history
- Processing logs
- Celery background processing
- Redis broker
- Mock lookup provider
- LangChain lookup provider structure
- Download processed Excel file
- Dashboard summary
- Docker support
- Swagger API documentation

## Tech Stack

Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, Pandas, OpenPyXL, Celery, Redis, LangChain, OpenAI, Docker.

## Local Setup

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Create PostgreSQL database:

```sql
CREATE DATABASE sparetrack_db;
```

Run migrations:

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

Run FastAPI:

```bash
uvicorn app.main:app --reload
```

Run Redis:

```bash
redis-server
```

Run Celery:

```bash
celery -A app.celery_app.celery worker --loglevel=info
```

Windows Celery:

```bash
celery -A app.celery_app.celery worker --loglevel=info --pool=solo
```

Swagger:

```text
http://localhost:8000/docs
```

## Docker Setup

For Docker, update `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/sparetrack_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

Run:

```bash
docker-compose up --build
```

Run migrations:

```bash
docker-compose exec backend alembic revision --autogenerate -m "initial tables"
docker-compose exec backend alembic upgrade head
```

Swagger:

```text
http://localhost:8000/docs
```

## Main API Endpoints

### Authentication

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`

### Brands

- `POST /api/brands/`
- `GET /api/brands/`
- `GET /api/brands/{brand_id}/`
- `PUT /api/brands/{brand_id}/`
- `DELETE /api/brands/{brand_id}/`

### Files

- `POST /api/files/upload/`
- `GET /api/files/`
- `GET /api/files/{file_id}/`
- `GET /api/files/{file_id}/download/`
- `GET /api/files/{file_id}/logs/`
- `DELETE /api/files/{file_id}/`

### Parts

- `GET /api/parts/`
- `GET /api/parts/{part_id}/`
- `GET /api/parts/by-brand/{brand_id}/`
- `GET /api/parts/search/?brand_id=1&part_number=KGTXJ`
- `PUT /api/parts/{part_id}/`
- `POST /api/parts/{part_id}/recheck-price/`
- `GET /api/parts/{part_id}/price-history/`

### Lookup

- `GET /api/lookup/new-part/`
- `GET /api/lookup/market-price/`

### Tasks

- `GET /api/tasks/{task_id}/`

### Dashboard

- `GET /api/dashboard/summary/`

## Upload Workflow

1. Register/login.
2. Create brand.
3. Upload `.xlsx` or `.csv` file with `brand_id`.
4. Celery processes file.
5. Existing parts check price only.
6. New parts fetch details and price.
7. Price history is saved.
8. Processed Excel is generated.
9. Download processed file.

## Accepted Part Number Columns

- `part number`
- `Part Number`
- `PART NUMBER`
- `part_no`
- `part no`
- `part_no.`
- `sku`
- `item code`

## Lookup Provider

Development:

```env
LOOKUP_PROVIDER=mock
```

Production-style:

```env
LOOKUP_PROVIDER=langchain
OPENAI_API_KEY=your-key
SERPAPI_API_KEY=your-key
```

or:

```env
LOOKUP_PROVIDER=langchain
OPENAI_API_KEY=your-key
GOOGLE_SEARCH_API_KEY=your-key
GOOGLE_SEARCH_ENGINE_ID=your-engine-id
```
