import json
import os
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .industry_features import JobApplication, JobVacancy
from .industry_portal import IndustryDemoCompany, IndustryDemoVacancy, IndustryVacancyDetails, JobVacancyRequirements
from .main import Industry, Skill, User, hash_password


DEMO_COMPANIES = [
    {
        "key": "tcs",
        "name": "Tata Consultancy Services (Demo)",
        "recruiter": "TCS Demo Recruiter",
        "category": "Information Technology",
        "description": "Sample company profile for demonstrating recruitment workflows. This is not an official company account or partnership.",
        "website": "https://www.tcs.com",
        "logo": "TCS",
        "job": {
            "key": "tcs-aiml-engineer",
            "title": "AI/ML Engineer — Sample Opening",
            "description": "DEMO SAMPLE OPENING. Simulated AI/ML role for demonstrating SkillBridge AI applications; not a verified or live vacancy.",
            "skills": {"Python": 4, "Machine Learning": 3, "Statistics": 3},
            "preferred": ["SQL", "Cloud"],
            "experience": "Entry level · 0–1 years",
            "employment": "Full-time",
            "location": "Hybrid · Bengaluru (sample)",
        },
    },
    {
        "key": "amazon",
        "name": "Amazon (Demo)",
        "recruiter": "Amazon Demo Recruiter",
        "category": "Technology and e-commerce",
        "description": "Sample company profile for demonstrating recruitment workflows. This is not an official company account or partnership.",
        "website": "https://www.amazon.jobs",
        "logo": "AMZ",
        "job": {
            "key": "amazon-python-developer",
            "title": "Python Developer — Sample Opening",
            "description": "DEMO SAMPLE OPENING. Simulated Python development role for demonstrating SkillBridge AI applications; not a verified or live vacancy.",
            "skills": {"Python": 4, "API Design": 3, "SQL": 3},
            "preferred": ["Git", "Problem Solving"],
            "experience": "Entry level · 0–2 years",
            "employment": "Full-time",
            "location": "Remote (sample)",
        },
    },
    {
        "key": "infosys",
        "name": "Infosys (Demo)",
        "recruiter": "Infosys Demo Recruiter",
        "category": "Information Technology",
        "description": "Sample company profile for demonstrating recruitment workflows. This is not an official company account or partnership.",
        "website": "https://www.infosys.com",
        "logo": "INF",
        "job": {
            "key": "infosys-software-engineer",
            "title": "Software Engineer — Sample Opening",
            "description": "DEMO SAMPLE OPENING. Simulated software engineering role for demonstrating SkillBridge AI applications; not a verified or live vacancy.",
            "skills": {"JavaScript": 3, "Git": 3, "Problem Solving": 3},
            "preferred": ["Python", "SQL"],
            "experience": "Entry level · 0–1 years",
            "employment": "Full-time",
            "location": "Hybrid · Pune (sample)",
        },
    },
    {
        "key": "microsoft",
        "name": "Microsoft (Demo)",
        "recruiter": "Microsoft Demo Recruiter",
        "category": "Software and cloud technology",
        "description": "Sample company profile for demonstrating recruitment workflows. This is not an official company account or partnership.",
        "website": "https://www.microsoft.com",
        "logo": "MS",
        "job": {
            "key": "microsoft-web-developer",
            "title": "Web Developer — Sample Opening",
            "description": "DEMO SAMPLE OPENING. Simulated web development role for demonstrating SkillBridge AI applications; not a verified or live vacancy.",
            "skills": {"React": 3, "JavaScript": 4, "API Design": 3},
            "preferred": ["Git", "Problem Solving"],
            "experience": "Entry level · 0–2 years",
            "employment": "Full-time",
            "location": "Hybrid · Hyderabad (sample)",
        },
    },
    {
        "key": "wipro",
        "name": "Wipro (Demo)",
        "recruiter": "Wipro Demo Recruiter",
        "category": "Information Technology",
        "description": "Sample company profile for demonstrating recruitment workflows. This is not an official company account or partnership.",
        "website": "https://www.wipro.com",
        "logo": "WIP",
        "job": {
            "key": "wipro-data-analyst",
            "title": "Data Analyst — Sample Opening",
            "description": "DEMO SAMPLE OPENING. Simulated data analysis role for demonstrating SkillBridge AI applications; not a verified or live vacancy.",
            "skills": {"SQL": 4, "Python": 3, "Power BI": 3},
            "preferred": ["Statistics", "Data Visualization"],
            "experience": "Entry level · 0–1 years",
            "employment": "Full-time",
            "location": "On-site · Chennai (sample)",
        },
    },
    {
        "key": "accenture",
        "name": "Accenture (Demo)",
        "recruiter": "Accenture Demo Recruiter",
        "category": "Professional services and technology",
        "description": "Sample company profile for demonstrating recruitment workflows. This is not an official company account or partnership.",
        "website": "https://www.accenture.com",
        "logo": "ACC",
        "job": {
            "key": "accenture-cloud-engineer",
            "title": "Cloud Engineer — Sample Opening",
            "description": "DEMO SAMPLE OPENING. Simulated cloud engineering role for demonstrating SkillBridge AI applications; not a verified or live vacancy.",
            "skills": {"Cloud": 4, "Python": 3, "Cybersecurity": 2},
            "preferred": ["Git", "Problem Solving"],
            "experience": "Entry level · 0–2 years",
            "employment": "Full-time",
            "location": "Hybrid · Mumbai (sample)",
        },
    },
]


def seed_demo_industry(db: Session, credentials: dict[str, tuple[str, str]]) -> dict[str, int]:
    missing = [company["key"] for company in DEMO_COMPANIES if company["key"] not in credentials]
    if missing:
        raise ValueError("Missing email/password environment configuration for all demo company keys.")
    required_skills = {
        skill
        for company in DEMO_COMPANIES
        for skill in (*company["job"]["skills"].keys(), *company["job"]["preferred"])
    }
    available_skills = set(db.scalars(select(Skill.name)).all())
    if not required_skills.issubset(available_skills):
        missing_skills = sorted(required_skills - available_skills)
        raise ValueError("The platform skill catalog is missing required demo skills: " + ", ".join(missing_skills))

    created_companies = 0
    created_vacancies = 0
    try:
        for company in DEMO_COMPANIES:
            email, password = credentials[company["key"]]
            email = email.strip().lower()
            if "@" not in email or len(password) < 12 or len(password) > 128:
                raise ValueError(f"Demo credentials for {company['key']} require a valid email and password of 12–128 characters.")

            demo_company = db.get(IndustryDemoCompany, company["key"])
            if demo_company is None:
                existing_user = db.scalar(select(User).where(User.email == email))
                if existing_user is not None:
                    raise ValueError(f"The configured demo email for {company['key']} already belongs to an account; existing accounts were not changed.")
                existing_company = db.scalar(select(Industry).where(Industry.company_name.ilike(company["name"])))
                if existing_company is not None:
                    raise ValueError(f"A company named {company['name']} already exists without a demo marker; it was not modified.")
                user = User(
                    name=company["recruiter"],
                    email=email,
                    password_hash=hash_password(password),
                    role="industry",
                )
                db.add(user)
                db.flush()
                industry = Industry(
                    user_id=user.id,
                    company_name=company["name"],
                    industry_type=company["category"],
                    description=company["description"],
                )
                db.add(industry)
                db.flush()
                demo_company = IndustryDemoCompany(
                    company_key=company["key"],
                    industry_id=industry.id,
                    company_name=company["name"],
                    category=company["category"],
                    description=company["description"],
                    website=company["website"],
                    logo_text=company["logo"],
                )
                db.add(demo_company)
                created_companies += 1
            else:
                industry = db.get(Industry, demo_company.industry_id)
                if industry is None or industry.company_name != demo_company.company_name:
                    raise ValueError(f"Demo company {company['key']} no longer matches its account; refusing to overwrite data.")
                if industry.user.email != email:
                    raise ValueError(f"Configured email for {company['key']} does not match its existing demo account.")

            vacancy_key = company["job"]["key"]
            vacancy_meta = db.scalar(select(IndustryDemoVacancy).where(IndustryDemoVacancy.vacancy_key == vacancy_key))
            if vacancy_meta is None:
                job = company["job"]
                vacancy = JobVacancy(
                    industry_id=demo_company.industry_id,
                    title=job["title"],
                    description=job["description"],
                    location=job["location"],
                    employment_type=job["employment"],
                    eligibility="Demo role for development and presentation use only.",
                    required_skill_levels=json.dumps(job["skills"]),
                    deadline="",
                    status="OPEN",
                )
                db.add(vacancy)
                db.flush()
                db.add(IndustryDemoVacancy(
                    vacancy_id=vacancy.id,
                    vacancy_key=vacancy_key,
                ))
                db.add(IndustryVacancyDetails(
                    vacancy_id=vacancy.id,
                    preferred_skills=json.dumps(job["preferred"]),
                    experience_level=job["experience"],
                ))
                db.add(JobVacancyRequirements(
                    vacancy_id=vacancy.id,
                    experience_requirement=job["experience"],
                    openings=1,
                    application_instructions="Sample application only. No real company recruitment process is represented.",
                ))
                created_vacancies += 1

        db.commit()
        return {"companies": created_companies, "vacancies": created_vacancies}
    except Exception:
        db.rollback()
        raise


def _credentials_from_env() -> dict[str, tuple[str, str]]:
    credentials = {}
    for company in DEMO_COMPANIES:
        prefix = f"SKILLBRIDGE_DEMO_{company['key'].upper()}"
        email = os.environ.get(f"{prefix}_EMAIL", "")
        password = os.environ.get(f"{prefix}_PASSWORD", "")
        if email and password:
            credentials[company["key"]] = (email, password)
    return credentials


def main() -> int:
    credentials = _credentials_from_env()
    if len(credentials) != len(DEMO_COMPANIES):
        print("Configure SKILLBRIDGE_DEMO_<COMPANY>_EMAIL and _PASSWORD for all six demo companies.", file=sys.stderr)
        return 2
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_demo_industry(db, credentials)
        print(f"Demo industry seed complete: {result['companies']} companies and {result['vacancies']} vacancies added.")
        return 0
    except ValueError as error:
        print(f"Demo industry seed failed without changing existing records: {error}", file=sys.stderr)
        return 1
    except IntegrityError:
        print("Demo industry seed failed because a database constraint was not satisfied; no credentials or existing records were displayed.", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
