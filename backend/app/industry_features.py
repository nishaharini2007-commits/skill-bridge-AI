import json
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import Session, mapped_column, relationship

from .database import Base, get_db
from .services.candidate_matching import match_candidate

router = APIRouter()


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IndustryProjectCriteria(Base):
    __tablename__ = "industry_project_criteria"
    project_id = mapped_column(ForeignKey("projects.id"), primary_key=True)
    eligibility = mapped_column(Text, default="")
    required_skill_levels = mapped_column(Text, default="{}")


class ProjectApplicationReview(Base):
    __tablename__ = "project_application_reviews"
    project_application_id = mapped_column(ForeignKey("project_applications.id"), primary_key=True)
    status = mapped_column(String(30), default="APPLIED", nullable=False)
    note = mapped_column(Text, default="")
    updated_at = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)


class JobVacancy(Base):
    __tablename__ = "job_vacancies"
    id = mapped_column(Integer, primary_key=True)
    industry_id = mapped_column(ForeignKey("industries.id"), nullable=False, index=True)
    title = mapped_column(String(180), nullable=False)
    description = mapped_column(Text, nullable=False)
    location = mapped_column(String(160), default="Remote")
    employment_type = mapped_column(String(60), default="Full-time")
    eligibility = mapped_column(Text, default="")
    required_skill_levels = mapped_column(Text, default="{}")
    deadline = mapped_column(String(50), default="")
    status = mapped_column(String(20), default="OPEN", nullable=False)
    created_at = mapped_column(DateTime, default=_utc_now)


class JobApplication(Base):
    __tablename__ = "job_applications"
    id = mapped_column(Integer, primary_key=True)
    vacancy_id = mapped_column(ForeignKey("job_vacancies.id"), nullable=False, index=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    status = mapped_column(String(30), default="APPLIED", nullable=False)
    note = mapped_column(Text, default="")
    applied_at = mapped_column(DateTime, default=_utc_now)
    updated_at = mapped_column(DateTime, default=_utc_now, onupdate=_utc_now)
    student = relationship("Student")
    __table_args__ = (UniqueConstraint("vacancy_id", "student_id"),)


class VacancyInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=12000)
    location: str = Field(default="Remote", max_length=160)
    employment_type: Literal["Full-time", "Part-time", "Internship", "Contract"] = "Full-time"
    eligibility: str = Field(default="", max_length=2000)
    required_skill_levels: dict[str, int] = Field(default_factory=dict, max_length=40)
    deadline: str = Field(default="", max_length=50)

    @field_validator("required_skill_levels")
    @classmethod
    def validate_required_skill_levels(cls, value: dict[str, int]):
        if any(not skill.strip() or len(skill.strip()) > 100 for skill in value):
            raise ValueError("Skill names must contain 1 to 100 characters")
        if any(level < 1 or level > 5 for level in value.values()):
            raise ValueError("Required skill levels must be between 1 and 5")
        return {skill.strip(): level for skill, level in value.items()}

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, value: str):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Deadline must use YYYY-MM-DD format") from exc
        return value


class IndustryProjectInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=12000)
    domain: str = Field(default="Technology", max_length=100)
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Intermediate"
    required_skills: list[str] = Field(default_factory=list, max_length=40)
    expected_outcome: str = Field(default="", max_length=4000)
    evaluation_criteria: str = Field(default="", max_length=4000)
    deadline: str = Field(default="", max_length=50)
    eligibility: str = Field(default="", max_length=2000)
    required_skill_levels: dict[str, int] = Field(default_factory=dict, max_length=40)

    @field_validator("deadline")
    @classmethod
    def validate_project_deadline(cls, value: str):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Deadline must use YYYY-MM-DD format") from exc
        return value

    @field_validator("required_skill_levels")
    @classmethod
    def validate_required_skill_levels(cls, value: dict[str, int]):
        if any(not skill.strip() or len(skill.strip()) > 100 for skill in value):
            raise ValueError("Skill names must contain 1 to 100 characters")
        if any(level < 1 or level > 5 for level in value.values()):
            raise ValueError("Required skill levels must be between 1 and 5")
        return {skill.strip(): level for skill, level in value.items()}


class ProjectReviewInput(BaseModel):
    status: Literal["REVIEWING", "SHORTLISTED", "INTERVIEW", "SELECTED", "NOT_SELECTED"]
    note: str = Field(default="", max_length=2000)


class JobApplicationStatusInput(BaseModel):
    status: Literal["REVIEWING", "SHORTLISTED", "INTERVIEW", "SELECTED", "NOT_SELECTED"]
    note: str = Field(default="", max_length=2000)


class ListingStatusInput(BaseModel):
    status: Literal["OPEN", "CLOSED"]


def _main():
    from . import main
    return main


def _industry_for(db: Session, user):
    main = _main()
    industry = db.scalar(select(main.Industry).where(main.Industry.user_id == user.id))
    if industry is None:
        main.fail("Industry profile not found", 404)
    return industry


def _requirements(db: Session, values: dict[str, int]) -> dict[str, int]:
    main = _main()
    requirements = {}
    for name, level in values.items():
        skill = main.skill_by_name(db, name)
        if skill is None:
            main.fail(f"Skill '{name}' is not in the platform skill catalog", 422)
        requirements[skill.name] = level
    return requirements


def _deadline_passed(value: str) -> bool:
    if not value:
        return False
    try:
        deadline = date.fromisoformat(value)
    except ValueError:
        _main().fail("This listing has an invalid deadline; contact the company", 409)
    return deadline < date.today()


def _student_match(db: Session, student, requirements: dict[str, int]) -> dict:
    main = _main()
    assessed = {}
    results = db.scalars(
        select(main.AssessmentResult)
        .join(main.Assessment)
        .where(
            main.Assessment.student_id == student.id,
            main.Assessment.completed_at.is_not(None),
        )
    ).all()
    for result in results:
        key = result.skill.name.casefold()
        assessed[key] = max(assessed.get(key, 0), result.proficiency)
    verified_projects = {
        item.skill.name.casefold()
        for item in student.skills
        if item.verification_status == "VERIFIED"
    }
    return match_candidate(
        requirements,
        [
            {
                "name": item.skill.name,
                "proficiency": item.proficiency,
                "verification_status": item.verification_status,
            }
            for item in student.skills
        ],
        assessed,
        verified_projects,
    )


def _criteria(db: Session, project_id: int) -> tuple[str, dict[str, int]]:
    criteria = db.get(IndustryProjectCriteria, project_id)
    if criteria is None:
        return "", {}
    try:
        required = json.loads(criteria.required_skill_levels or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid skill requirement data for project {project_id}") from exc
    if not isinstance(required, dict):
        raise ValueError(f"Invalid skill requirement data for project {project_id}")
    return criteria.eligibility, required


def _project_payload(db: Session, project, student=None) -> dict:
    main = _main()
    eligibility, levels = _criteria(db, project.id)
    requirements = levels or {
        skill: 1 for skill in project.required_skills.split(",") if skill.strip()
    }
    requirements = {skill.strip(): level for skill, level in requirements.items()}
    payload = main.project_payload(project, student)
    payload["eligibility"] = eligibility
    payload["required_skill_levels"] = requirements
    payload["candidate_match"] = _student_match(db, student, requirements) if student else None
    return payload


def _vacancy_payload(db: Session, vacancy, student=None) -> dict:
    main = _main()
    try:
        requirements = json.loads(vacancy.required_skill_levels or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid skill requirement data for vacancy {vacancy.id}") from exc
    application = None
    if student is not None:
        application = db.scalar(
            select(JobApplication).where(
                JobApplication.vacancy_id == vacancy.id,
                JobApplication.student_id == student.id,
            )
        )
    industry = db.get(main.Industry, vacancy.industry_id)
    application_count = db.scalar(
        select(func.count(JobApplication.id)).where(JobApplication.vacancy_id == vacancy.id)
    )
    return {
        "id": vacancy.id,
        "title": vacancy.title,
        "description": vacancy.description,
        "location": vacancy.location,
        "employment_type": vacancy.employment_type,
        "eligibility": vacancy.eligibility,
        "required_skill_levels": requirements,
        "deadline": vacancy.deadline,
        "status": vacancy.status,
        "company": industry.company_name if industry else "",
        "application_count": application_count or 0,
        "application_status": application.status if application else None,
        "company_note": application.note if application else "",
        "candidate_match": _student_match(db, student, requirements) if student else None,
    }


def _owned_project(db: Session, user, project_id: int):
    main = _main()
    industry = _industry_for(db, user)
    project = db.scalar(
        select(main.Project).where(
            main.Project.id == project_id,
            main.Project.industry_id == industry.id,
        )
    )
    if project is None:
        main.fail("Project not found", 404)
    return project


def _owned_vacancy(db: Session, user, vacancy_id: int):
    main = _main()
    industry = _industry_for(db, user)
    vacancy = db.scalar(
        select(JobVacancy).where(
            JobVacancy.id == vacancy_id,
            JobVacancy.industry_id == industry.id,
        )
    )
    if vacancy is None:
        main.fail("Job vacancy not found", 404)
    return vacancy


@router.get("/api/student/project-marketplace")
def student_project_marketplace(
    user: Annotated[object, Depends(_main().require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    student = main.student_for(db, user)
    projects = db.scalars(
        select(main.Project).where(main.Project.status == "OPEN").order_by(main.Project.id.desc())
    ).all()
    return main.ok([_project_payload(db, project, student) for project in projects])


@router.post("/api/student/project-marketplace/{project_id}/applications", status_code=201)
def apply_to_marketplace_project(
    project_id: int,
    user: Annotated[object, Depends(_main().require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    student = main.student_for(db, user)
    project = db.scalar(
        select(main.Project).where(main.Project.id == project_id, main.Project.status == "OPEN")
    )
    if project is None:
        main.fail("Project is not available", 404)
    if _deadline_passed(project.deadline):
        main.fail("The application deadline has passed", 409)
    existing = db.scalar(
        select(main.ProjectApplication).where(
            main.ProjectApplication.project_id == project.id,
            main.ProjectApplication.student_id == student.id,
        )
    )
    if existing:
        main.fail("You have already applied to this project", 409)
    application = main.ProjectApplication(project_id=project.id, student_id=student.id)
    db.add(application)
    db.commit()
    return main.ok({"application_id": application.id, "status": application.status})


@router.get("/api/industry/projects")
def industry_projects(
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    industry = _industry_for(db, user)
    projects = db.scalars(
        select(main.Project).where(main.Project.industry_id == industry.id).order_by(main.Project.id.desc())
    ).all()
    return main.ok([_project_payload(db, project) for project in projects])


@router.post("/api/industry/projects", status_code=201)
def create_industry_project(
    payload: IndustryProjectInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    industry = _industry_for(db, user)
    required_names = payload.required_skills
    requested_levels = payload.required_skill_levels
    requirements = _requirements(db, {
        name: requested_levels.get(name, 1) for name in required_names
    })
    project = main.Project(
        industry_id=industry.id,
        title=payload.title,
        description=payload.description,
        domain=payload.domain,
        difficulty=payload.difficulty,
        required_skills=", ".join(requirements),
        expected_outcome=payload.expected_outcome,
        evaluation_criteria=payload.evaluation_criteria,
        deadline=payload.deadline,
        status="OPEN",
    )
    db.add(project)
    db.flush()
    criteria = IndustryProjectCriteria(
        project_id=project.id,
        eligibility=payload.eligibility.strip(),
        required_skill_levels=json.dumps(requirements),
    )
    db.add(criteria)
    db.commit()
    db.refresh(project)
    return main.ok(_project_payload(db, project))


@router.patch("/api/industry/projects/{project_id}")
def update_industry_project(
    project_id: int,
    payload: IndustryProjectInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    project = _owned_project(db, user, project_id)
    levels = _requirements(db, {
        name: payload.required_skill_levels.get(name, 1) for name in payload.required_skills
    })
    project.title = payload.title
    project.description = payload.description
    project.domain = payload.domain
    project.difficulty = payload.difficulty
    project.required_skills = ", ".join(levels)
    project.expected_outcome = payload.expected_outcome
    project.evaluation_criteria = payload.evaluation_criteria
    project.deadline = payload.deadline
    criteria = db.get(IndustryProjectCriteria, project.id)
    if criteria is None:
        criteria = IndustryProjectCriteria(project_id=project.id)
        db.add(criteria)
    criteria.eligibility = payload.eligibility.strip()
    criteria.required_skill_levels = json.dumps(levels)
    db.commit()
    return main.ok(_project_payload(db, project))


@router.patch("/api/industry/projects/{project_id}/status")
def update_project_status(
    project_id: int,
    payload: ListingStatusInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    project = _owned_project(db, user, project_id)
    project.status = payload.status
    db.commit()
    return main.ok(_project_payload(db, project))


@router.get("/api/industry/projects/{project_id}/applications")
def project_applications(
    project_id: int,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    project = _owned_project(db, user, project_id)
    applications = db.scalars(
        select(main.ProjectApplication)
        .where(main.ProjectApplication.project_id == project.id)
        .order_by(main.ProjectApplication.applied_at.desc())
    ).all()
    output = []
    eligibility, levels = _criteria(db, project.id)
    requirements = levels or {skill.strip(): 1 for skill in project.required_skills.split(",") if skill.strip()}
    for application in applications:
        review = db.get(ProjectApplicationReview, application.id)
        student = application.student
        output.append({
            "application_id": application.id,
            "student_id": student.id,
            "student_name": student.user.name,
            "college": student.college,
            "department": student.department,
            "career_goal": student.career_goal,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
            "project_status": application.status,
            "review_status": review.status if review else "APPLIED",
            "company_note": review.note if review else "",
            "submission": {
                "description": application.submission.description,
                "github_url": application.submission.github_url,
                "evidence": application.submission.evidence,
            } if application.submission else None,
            "candidate_match": _student_match(db, student, requirements),
            "eligibility": eligibility,
        })
    return main.ok(output)


@router.patch("/api/industry/project-applications/{application_id}/review")
def review_project_application(
    application_id: int,
    payload: ProjectReviewInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    industry = _industry_for(db, user)
    application = db.scalar(
        select(main.ProjectApplication)
        .join(main.Project)
        .where(
            main.ProjectApplication.id == application_id,
            main.Project.industry_id == industry.id,
        )
    )
    if application is None:
        main.fail("Project application not found", 404)
    review = db.get(ProjectApplicationReview, application.id)
    if review is None:
        review = ProjectApplicationReview(project_application_id=application.id)
        db.add(review)
    review.status = payload.status
    review.note = payload.note.strip()
    db.commit()
    return main.ok({"application_id": application.id, "status": review.status, "note": review.note})


@router.get("/api/industry/job-vacancies")
def industry_job_vacancies(
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    industry = _industry_for(db, user)
    vacancies = db.scalars(
        select(JobVacancy).where(JobVacancy.industry_id == industry.id).order_by(JobVacancy.id.desc())
    ).all()
    return main.ok([_vacancy_payload(db, vacancy) for vacancy in vacancies])


@router.post("/api/industry/job-vacancies", status_code=201)
def create_job_vacancy(
    payload: VacancyInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    industry = _industry_for(db, user)
    requirements = _requirements(db, payload.required_skill_levels)
    vacancy = JobVacancy(
        industry_id=industry.id,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        employment_type=payload.employment_type,
        eligibility=payload.eligibility,
        required_skill_levels=json.dumps(requirements),
        deadline=payload.deadline,
        status="OPEN",
    )
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    return main.ok(_vacancy_payload(db, vacancy))


@router.patch("/api/industry/job-vacancies/{vacancy_id}")
def update_job_vacancy(
    vacancy_id: int,
    payload: VacancyInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    vacancy = _owned_vacancy(db, user, vacancy_id)
    requirements = _requirements(db, payload.required_skill_levels)
    vacancy.title = payload.title
    vacancy.description = payload.description
    vacancy.location = payload.location
    vacancy.employment_type = payload.employment_type
    vacancy.eligibility = payload.eligibility
    vacancy.required_skill_levels = json.dumps(requirements)
    vacancy.deadline = payload.deadline
    db.commit()
    return main.ok(_vacancy_payload(db, vacancy))


@router.patch("/api/industry/job-vacancies/{vacancy_id}/status")
def update_job_vacancy_status(
    vacancy_id: int,
    payload: ListingStatusInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    vacancy = _owned_vacancy(db, user, vacancy_id)
    vacancy.status = payload.status
    db.commit()
    return main.ok(_vacancy_payload(db, vacancy))


@router.get("/api/student/job-vacancies")
def student_job_vacancies(
    user: Annotated[object, Depends(_main().require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    student = main.student_for(db, user)
    vacancies = db.scalars(
        select(JobVacancy).where(JobVacancy.status == "OPEN").order_by(JobVacancy.id.desc())
    ).all()
    return main.ok([_vacancy_payload(db, vacancy, student) for vacancy in vacancies])


@router.post("/api/student/job-vacancies/{vacancy_id}/applications", status_code=201)
def apply_job_vacancy(
    vacancy_id: int,
    user: Annotated[object, Depends(_main().require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    student = main.student_for(db, user)
    vacancy = db.get(JobVacancy, vacancy_id)
    if vacancy is None or vacancy.status != "OPEN":
        main.fail("Job vacancy is not available", 404)
    if _deadline_passed(vacancy.deadline):
        main.fail("The application deadline has passed", 409)
    existing = db.scalar(
        select(JobApplication).where(
            JobApplication.vacancy_id == vacancy.id,
            JobApplication.student_id == student.id,
        )
    )
    if existing:
        main.fail("You have already applied to this vacancy", 409)
    application = JobApplication(vacancy_id=vacancy.id, student_id=student.id)
    db.add(application)
    db.commit()
    return main.ok({"application_id": application.id, "status": application.status})


@router.get("/api/industry/job-vacancies/{vacancy_id}/applications")
def vacancy_applications(
    vacancy_id: int,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    vacancy = _owned_vacancy(db, user, vacancy_id)
    requirements = json.loads(vacancy.required_skill_levels or "{}")
    applications = db.scalars(
        select(JobApplication).where(JobApplication.vacancy_id == vacancy.id).order_by(JobApplication.applied_at.desc())
    ).all()
    return main.ok([
        {
            "application_id": application.id,
            "student_id": application.student_id,
            "student_name": application.student.user.name,
            "college": application.student.college,
            "department": application.student.department,
            "career_goal": application.student.career_goal,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
            "status": application.status,
            "note": application.note,
            "candidate_match": _student_match(db, application.student, requirements),
        }
        for application in applications
    ])


@router.patch("/api/industry/job-applications/{application_id}")
def update_job_application(
    application_id: int,
    payload: JobApplicationStatusInput,
    user: Annotated[object, Depends(_main().require_role("industry"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    industry = _industry_for(db, user)
    application = db.scalar(
        select(JobApplication)
        .join(JobVacancy)
        .where(
            JobApplication.id == application_id,
            JobVacancy.industry_id == industry.id,
        )
    )
    if application is None:
        main.fail("Job application not found", 404)
    application.status = payload.status
    application.note = payload.note.strip()
    application.updated_at = _utc_now()
    db.commit()
    return main.ok({"application_id": application.id, "status": application.status, "note": application.note})


@router.get("/api/student/applications")
def student_applications(
    user: Annotated[object, Depends(_main().require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    main = _main()
    student = main.student_for(db, user)
    project_apps = db.scalars(
        select(main.ProjectApplication)
        .where(main.ProjectApplication.student_id == student.id)
        .order_by(main.ProjectApplication.applied_at.desc())
    ).all()
    job_apps = db.scalars(
        select(JobApplication).where(JobApplication.student_id == student.id).order_by(JobApplication.applied_at.desc())
    ).all()
    projects = []
    for application in project_apps:
        review = db.get(ProjectApplicationReview, application.id)
        projects.append({
            "kind": "project",
            "id": application.id,
            "listing_id": application.project_id,
            "title": application.project.title,
            "company": application.project.industry.company_name,
            "status": review.status if review else application.status,
            "company_note": review.note if review else "",
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
            "evaluation_feedback": application.submission.evaluation.feedback if application.submission and application.submission.evaluation else "",
        })
    jobs = []
    for application in job_apps:
        vacancy = db.get(JobVacancy, application.vacancy_id)
        industry = db.get(main.Industry, vacancy.industry_id)
        jobs.append({
            "kind": "job",
            "id": application.id,
            "listing_id": vacancy.id,
            "title": vacancy.title,
            "company": industry.company_name if industry else "",
            "status": application.status,
            "company_note": application.note,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
            "evaluation_feedback": "",
        })
    return main.ok(sorted(projects + jobs, key=lambda item: item["applied_at"] or "", reverse=True))
