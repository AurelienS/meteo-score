# Meteo Score - Meteorological Forecast Scoring System

## Description

Meteo Score is a comprehensive system for collecting, analyzing, and scoring meteorological forecasts. It compares weather predictions from various sources against actual observations to provide accuracy metrics and insights.

## Tech Stack

### Backend
- **Python 3.11** - Core language
- **FastAPI** - REST API framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Primary database
- **Alembic** - Database migrations
- **APScheduler** - Task scheduling
- **Pandas & XArray** - Data processing
- **cfgrib** - GRIB file processing

### Frontend
- **Solid.js** - Reactive UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Tailwind CSS 4.0** - Utility-first CSS
- **D3.js** - Data visualization library
- **Geist Fonts** - Typography (Sans & Mono)

### DevOps
- **Docker & Docker Compose** - Containerization
- **pytest** - Backend testing
- **ESLint & Prettier** - Code quality

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker and Docker Compose
- PostgreSQL 15+ (or use Docker)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd meteo-score
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Database Setup

```bash
# Using Docker Compose
docker-compose up -d postgres

# Run migrations
cd backend
alembic upgrade head
```

### 6. Run the Application

**Backend:**
```bash
cd backend
uvicorn api.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Access the application at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 7. Docker Compose Setup (Recommended)

Run all services with Docker Compose for full infrastructure:

**⚠️ Note:** Full application functionality requires:
- Story 1.3: Database schema and migrations
- Story 1.4: Backend API implementation (currently stub for healthcheck only)
- Story 1.5: Frontend components (currently basic Solid.js template)

The infrastructure (containers, networking, volumes) is fully configured and operational.

**Start all services:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f
docker-compose logs -f backend  # Specific service
```

**Stop services:**
```bash
docker-compose down
```

**Rebuild and restart:**
```bash
docker-compose up -d --build
```

**Execute commands in containers:**
```bash
docker-compose exec backend bash
docker-compose exec postgres psql -U meteo_user -d meteo_score
```

**Service URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Adminer (DB UI): http://localhost:8080
- Traefik Dashboard: http://localhost:8888

## Project Structure

```
meteo-score/
├── backend/
│   ├── collectors/       # Data collection modules
│   ├── core/            # Core business logic
│   ├── api/             # FastAPI routes and endpoints
│   ├── db/              # Database models and migrations
│   ├── scheduler/       # Task scheduling
│   └── tests/           # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page components
│   │   ├── lib/         # Utilities and helpers
│   │   └── styles/      # Global styles
│   └── public/          # Static assets
├── _bmad/               # Project management and documentation
└── docker-compose.yml   # Docker services configuration
```

## Development

### Backend Code Quality

```bash
cd backend
ruff check .           # Linting
black .                # Formatting
mypy .                 # Type checking
pytest                 # Run tests
```

### Frontend Code Quality

```bash
cd frontend
npm run lint           # ESLint
npm run format         # Prettier
npm run type-check     # TypeScript check
```

## CLI Commands

The backend includes a CLI for database operations and manual data collection. These commands are useful for administration, debugging, and initial setup.

### Running CLI Commands

**In Docker (recommended):**
```bash
docker-compose exec backend python -m cli <command>
```

**Locally:**
```bash
cd backend
python -m cli <command>
```

### Available Commands

| Command | Description | Options |
|---------|-------------|---------|
| `seed` | Seed database with initial data (sites, models, parameters) | `--force` to override non-empty check |
| `migrate` | Run database migrations (alembic upgrade head) | - |
| `stats` | Display database statistics (record counts) | - |
| `collect-forecasts` | Manually trigger forecast collection | - |
| `collect-observations` | Manually trigger observation collection | - |

### Examples

```bash
# Initial database setup
docker-compose exec backend python -m cli migrate
docker-compose exec backend python -m cli seed

# Force re-seed (overwrites existing data)
docker-compose exec backend python -m cli seed --force

# View database statistics
docker-compose exec backend python -m cli stats

# Manual data collection
docker-compose exec backend python -m cli collect-forecasts
docker-compose exec backend python -m cli collect-observations
```

## Deployment

The application is deployed using a branch-based workflow. Pushing to the `prod` branch triggers deployment to production.

### Deploy to Production

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Push main to prod branch
git push origin main:prod
```

This will:
1. Push all commits from `main` to the `prod` branch
2. Trigger the production deployment pipeline

### Deployment Notes

- Always ensure `main` is stable and tested before deploying
- The `prod` branch should only be updated via pushes from `main`
- Monitor the deployment logs after pushing to verify successful deployment

## License

[Add your license here]

## Contributors

[Add contributors here]
