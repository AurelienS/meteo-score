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

## License

[Add your license here]

## Contributors

[Add contributors here]
