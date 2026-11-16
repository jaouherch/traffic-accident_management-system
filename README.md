# Traffic Accident Management System

A full-stack project for reporting, visualizing, and verifying traffic incidents on an interactive map. Developed as an **individual academic project** by **Jaouher Chouchane**.

## What it does

- Citizens can create an account and submit geolocated reports with severity, casualties, descriptions, and optional photos.
- The interactive Leaflet map displays incidents and a heatmap highlights areas with more reports.
- Officers can review reports and mark them as confirmed or false reports.
- Administrators can manage users, review officer applications, and access analytics.
- Comments, a leaderboard, and points support community engagement.
- Swagger UI documents the Flask API at `http://localhost:5000/swagger-ui`.

## Technology

| Layer | Tools |
| --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Leaflet / leaflet.heat |
| Backend | Python, Flask, Flask-Smorest, Flask-SQLAlchemy |
| Authentication | JWT access / refresh tokens, PBKDF2 password hashing, role-based access |
| Database | SQLite for local development; configurable via SQLAlchemy URI |
| Other | Docker Compose, REST endpoints, OpenAPI, optional SMTP notification |

## Structure

```text
traffic-accident-management-system/
├── backend/
│   ├── app.py                 # Flask factory and configuration
│   ├── bootstrap_admin.py     # First-admin initialization
│   ├── models/                # Database entities
│   ├── resources/             # API endpoints
│   ├── schemas/               # Request/response schemas
│   ├── tests/                 # Isolated API smoke tests
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/                   # Next.js routes
│   ├── components/            # Map, reports, dashboards
│   ├── lib/api.ts             # Typed API client
│   └── .env.example
├── docs/
│   └── PROJECT_OVERVIEW.md
└── .gitignore
```

## Run locally

Requirements: **Python 3.10+**, **Node.js 20+**, and npm.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env`. Set `JWT_SECRET_KEY` to a **new random key**, at least 32 characters long. For example, run:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `.env`; the example placeholder is deliberately rejected at startup. **Never commit `.env`.**

Initialize the first administrator (the command prompts privately for a strong password):

```bash
python bootstrap_admin.py --username admin
python app.py
```

The API runs at `http://localhost:5000`, with Swagger UI at `/swagger-ui`. The default SQLite database is created automatically in Flask's `backend/instance/` directory.

### 2. Frontend

Open a **second terminal**:

```bash
cd frontend
npm ci
```

Copy `frontend/.env.example` to `frontend/.env.local`. Set `NEXT_PUBLIC_API_URL=http://localhost:5000`, then run:

```bash
npm run dev
```

Open `http://localhost:3000`.

## Run the backend with Docker

Set up `backend/.env` first, then from `backend/`:

```bash
docker compose up --build
```

Docker Compose persists the SQLite database and user-uploaded images in named volumes, separate from Git. To initialize an admin in Docker, run `docker compose exec backend python bootstrap_admin.py --username admin` from an interactive terminal.

## Authentication and roles

Regular accounts are created through `/register`. Officer applications through `/apply-officer` remain pending until an existing administrator approves them. Admin registration through `/register-admin` is **disabled by default**; if `ADMIN_INVITE_CODE` is configured, registration creates a **pending** account which an approved admin must accept. The first admin is set up locally using `bootstrap_admin.py`.

Optional email notifications require `MAIL_USERNAME`, `MAIL_PASSWORD` and `ADMIN_NOTIFICATION_EMAIL` in `backend/.env`. Never paste an email app password into Python source code.

## Testing

Backend smoke tests (use temporary SQLite databases):

```bash
cd backend
python -m unittest discover -s tests -v
```

Frontend type checking:

```bash
cd frontend
npm ci
npm run typecheck
```

To validate a complete frontend build on your own computer, run `npm run build` after installing dependencies.

## Publish on GitHub

Create an **empty** GitHub repository named `traffic-accident-management-system`, then run the following from the extracted project folder (the folder containing this README):

```bash
git init
git add .
git commit -m "Added Traffic Accident Management System portfolio project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/traffic-accident-management-system.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your own GitHub username. Upload the **extracted source files**, not the ZIP as a single file. The repository's `.gitignore` prevents local credentials, dependencies, databases, and uploads from being committed.

## Screenshots and presentation

See [project overview](docs/PROJECT_OVERVIEW.md) for a concise description and architecture. You can add **sanitized screenshots** from your original presentation under `docs/screenshots/` (map, reporting form, administration view). The original presentation is not bundled because it contains unfinished slide-template text.

## Important notes

- This repository excludes machine-specific dependencies, compiled files, databases, user uploads, and development request exports.
- API credentials, JWT keys, and admin invitations are loaded from local environment variables.
- This is a **portfolio / academic demonstration**. The in-memory JWT blocklist, permissive local SQLite workflow, and uploaded-image handling require additional security review before public production deployment.
- Review [SECURITY.md](SECURITY.md) before publishing or deploying.

