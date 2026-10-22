# SkillBridge AI

SkillBridge AI is a full-stack skill intelligence prototype connecting students, institutions, mentors and industry. It follows a continuous loop: industry demand informs career skills; students assess gaps and follow a roadmap; project work is reviewed by mentors; verified evidence informs opportunity matching.

## What is included

- Role-based JWT sign-in for student, industry, mentor and institution workspaces.
- Student profile, career goal, diagnostic assessment, live skill gaps, personalized roadmap, progress and evidence-based Skill Passport.
- A student learning profile with self-reported skills and study preferences, transparent rule-based skill-gap analysis, trusted resource links and a versioned learning roadmap.
- Industry skill extraction using a local normalized dictionary, shared career-skill requirements, project publishing and talent discovery.
- Project applications, submissions, mentor scoring and verified skills persisted in SQLite.
- Opportunity matching ranked by skill proficiency and career relevance.
- Industry project and vacancy management, student applications, evidence-based candidate match explanations, and company-controlled shortlisting.
- Institution analytics derived from student, role, assessment and project records.
- FastAPI OpenAPI docs at `http://localhost:8000/docs`; the frontend consumes the same REST API.

## Architecture

```text
React + TypeScript + Vite
        │ Axios / JWT
        ▼
FastAPI + Pydantic
        │ SQLAlchemy
        ▼
SQLite (backend/skillbridge.db)
        │
        └── deterministic local skill extraction, gap analysis and matching
```

## Technology

- Frontend: React, Vite, TypeScript, Tailwind CSS, React Router, Axios, Recharts, Lucide React, React Hook Form and Zod.
- Backend: Python, FastAPI, SQLAlchemy, Pydantic, SQLite, Uvicorn and PyJWT.
- Authentication: salted PBKDF2-SHA256 password hashes; expiring JWT bearer tokens.
- AI: local deterministic skill dictionary and recommendation/matching algorithms. No external key is required.

## Database

SQLAlchemy creates missing tables at startup without dropping or replacing the SQLite database. The learning feature adds `learning_profiles`, `learning_plans` and `learning_tasks`; it does not overwrite the existing roadmap tables or student skill/evidence records. The seed script is for a new demo database only and explicitly drops existing tables, so do not run `python seed.py` when preserving local records.

The learning profile stores self-reported preferences and skill levels separately from mentor verification. Recommendations and readiness are deterministic, rule-based planning aids, not AI-generated output, hiring predictions or proof of proficiency. Roadmap task status is persisted independently and never automatically changes skill proficiency. Resources link to official documentation, learning references or clearly labeled platform searches.

Industry postings add four tables: `industry_project_criteria`, `project_application_reviews`, `job_vacancies` and `job_applications`. Existing projects and project applications are reused. Startup creates only missing tables through SQLAlchemy `create_all`; no existing tables or columns are changed. To preserve an existing database, start the backend normally and do not run `python seed.py`. To disable the feature later without losing its records, stop the backend and remove the industry feature router import/registration from `backend/app/main.py`; leave the additive tables in place. Do not drop them unless their records have been backed up and removal is explicitly intended.

Candidate matching is deterministic and advisory. It uses saved student skill levels, completed platform assessments and verified project evidence when present; it does not infer credentials or external profile activity, and a low match does not block applications. Companies control application statuses and final shortlisting decisions.

## Windows setup

Prerequisites: Python 3.11+ and Node.js 20+.

### Start both applications

From the project root, run `start.bat`. It creates the backend virtual environment and installs packages when needed, seeds demo data only if `backend\skillbridge.db` does not exist, then opens the API and Vite development server in separate terminals. Never run `python seed.py` on a database whose records you need to preserve.

### Start services separately

Backend (PowerShell):

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --port 8000
```

Frontend (a second PowerShell window):

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`; API docs are at `http://localhost:8000/docs`. If PowerShell blocks `npm`, use `npm.cmd` as shown.

Copy `backend\.env.example` to `backend\.env` and `frontend\.env.example` to `frontend\.env` only when changing defaults. Keep `SECRET_KEY` private outside local demos. The local AI works with an empty `AI_API_KEY`.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Student (Arun Kumar) | `student@skillbridge.demo` | `Student@123` |
| Industry | `industry@skillbridge.demo` | `Industry@123` |
| Mentor | `mentor@skillbridge.demo` | `Mentor@123` |
| Institution | `institution@skillbridge.demo` | `Institution@123` |

Additional seeded learners: `priya@skillbridge.demo`, `rahul@skillbridge.demo`, `aisha@skillbridge.demo`, and `kavya@skillbridge.demo` (all use `Student@123`). Additional demo partners are `greengrid@skillbridge.demo` and `brightpath@skillbridge.demo` (`Industry@123`); `dev@skillbridge.demo` and `leena@skillbridge.demo` (`Mentor@123`); and `ntc@skillbridge.demo` (`Institution@123`).

Running `python seed.py` resets the local demo database to its original state.

## API overview

- `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`
- `GET|PUT /api/student/profile`, `GET /api/student/dashboard`, `/api/student/skills`, `/api/student/career-roles`, `PUT /api/student/career`
- `GET|PUT /api/student/learning-profile`, `GET /api/student/skill-gap-analysis`, `GET /api/student/learning-roadmap`, `POST /api/student/learning-roadmap/refresh`, `PATCH /api/student/learning-roadmap/tasks/{id}`
- `GET /api/assessment`, `POST /api/assessment/submit`, `GET /api/skill-gap`, `GET /api/roadmap`, `POST /api/roadmap/tasks/{id}/complete`
- `GET /api/projects`, `POST /api/projects`, `POST /api/projects/{id}/apply`, `POST /api/projects/{id}/submit`
- `GET /api/mentor/submissions`, `POST /api/projects/submissions/{id}/evaluate`
- `GET /api/student/project-marketplace`, `POST /api/student/project-marketplace/{id}/applications`, `GET /api/student/applications`
- `GET|POST /api/industry/projects`, `PATCH /api/industry/projects/{id}`, `PATCH /api/industry/projects/{id}/status`
- `GET /api/industry/projects/{id}/applications`, `PATCH /api/industry/project-applications/{id}/review`
- `GET|POST /api/industry/job-vacancies`, `PATCH /api/industry/job-vacancies/{id}`, `PATCH /api/industry/job-vacancies/{id}/status`
- `GET /api/student/job-vacancies`, `POST /api/student/job-vacancies/{id}/applications`
- `GET /api/industry/job-vacancies/{id}/applications`, `PATCH /api/industry/job-applications/{id}`
- `GET /api/student/passport`, `/api/student/progress`, `/api/opportunities/matches`
- `POST /api/industry/skills/extract`, `POST /api/industry/requirements`, `GET /api/industry/dashboard`, `/api/industry/talent`
- `GET /api/institution/analytics`, `GET /api/mentor/dashboard`, `GET /api/health`

Success responses use `{ "success": true, "data": ... }`; request errors use `{ "success": false, "message": "..." }` with the appropriate HTTP status.

## SIH demonstration workflow

See [DEMO_GUIDE.md](./DEMO_GUIDE.md) for the student-to-mentor flow and a short presentation sequence. The seeded `Customer Churn Analysis` project is ready for application. After mentor evaluation, the project's required skills are marked verified on the student's Skill Passport.

## Troubleshooting

- **API unavailable:** start the backend first and check `http://localhost:8000/api/health`.
- **CORS:** the default frontend origins are `http://localhost:5173` and `http://127.0.0.1:5173`; adjust `CORS_ORIGINS` in `backend\.env` if Vite runs on another origin.
- **Database reset:** stop neither service; run `python seed.py` from `backend` to recreate demo data (this resets the database).
- **Frontend API URL:** set `VITE_API_URL` in `frontend\.env` and restart Vite.
- **PowerShell npm policy:** use `npm.cmd` rather than `npm`.

## Future scope

PostgreSQL deployment, institution-managed cohorts, richer learning-provider integrations and an optional LLM-backed extractor can be added behind the existing service/API boundaries.
