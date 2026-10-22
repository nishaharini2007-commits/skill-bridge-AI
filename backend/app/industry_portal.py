import json
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Session, mapped_column

from .database import Base, get_db

router = APIRouter()


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _main():
    from . import main
    return main


class IndustryCompanyDetails(Base):
    __tablename__ = "industry_company_details"
    industry_id = mapped_column(ForeignKey("industries.id"), primary_key=True)
    website = mapped_column(String(500), default="")
    company_email = mapped_column(String(255), default="")
    contact_person = mapped_column(String(120), default="")
    contact_title = mapped_column(String(120), default="")
    phone = mapped_column(String(60), default="")
    logo_url = mapped_column(String(500), default="")
    verification_status = mapped_column(String(30), default="UNVERIFIED", nullable=False)
    updated_at = mapped_column(DateTime, default=_now, onupdate=_now)


class IndustryDemoCompany(Base):
    __tablename__ = "industry_demo_companies"
    company_key = mapped_column(String(40), primary_key=True)
    industry_id = mapped_column(ForeignKey("industries.id"), unique=True, nullable=False)
    company_name = mapped_column(String(180), nullable=False)
    category = mapped_column(String(120), nullable=False)
    description = mapped_column(Text, nullable=False)
    website = mapped_column(String(500), default="")
    logo_text = mapped_column(String(12), default="")
    account_status = mapped_column(String(20), default="DEMO", nullable=False)


class IndustryDemoDirectoryCompany(Base):
    __tablename__ = "industry_demo_company_directory"
    company_key = mapped_column(String(40), primary_key=True)
    company_name = mapped_column(String(180), unique=True, nullable=False)
    category = mapped_column(String(120), nullable=False)
    description = mapped_column(Text, nullable=False)
    website = mapped_column(String(500), default="")
    logo_text = mapped_column(String(12), default="")
    demo_label = mapped_column(String(40), default="DEMO COMPANY", nullable=False)


class IndustryDemoVacancy(Base):
    __tablename__ = "industry_demo_vacancies"
    vacancy_id = mapped_column(ForeignKey("job_vacancies.id"), primary_key=True)
    vacancy_key = mapped_column(String(80), unique=True, nullable=False)
    demo_label = mapped_column(String(80), default="DEMO SAMPLE OPENING", nullable=False)


class IndustryVacancyDetails(Base):
    __tablename__ = "industry_vacancy_details"
    vacancy_id = mapped_column(ForeignKey("job_vacancies.id"), primary_key=True)
    preferred_skills = mapped_column(Text, default="[]", nullable=False)
    experience_level = mapped_column(String(80), default="Entry level", nullable=False)


class StudentProfileSharing(Base):
    __tablename__ = "student_profile_sharing"
    student_id = mapped_column(ForeignKey("students.id"), primary_key=True)
    share_social_links = mapped_column(Boolean, default=False, nullable=False)
    updated_at = mapped_column(DateTime, default=_now, onupdate=_now)


class JobApplicationProfileConsent(Base):
    __tablename__ = "job_application_profile_consents"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    industry_id = mapped_column(ForeignKey("industries.id"), nullable=False, index=True)
    job_application_id = mapped_column(ForeignKey("job_applications.id"), unique=True, nullable=False, index=True)
    requested_profile_types = mapped_column(Text, default="[]", nullable=False)
    granted_profile_types = mapped_column(Text, default="[]", nullable=False)
    status = mapped_column(String(20), default="NOT_GRANTED", nullable=False)
    created_at = mapped_column(DateTime, default=_now, nullable=False)
    updated_at = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)
    revoked_at = mapped_column(DateTime)


class IndustryProjectDetails(Base):
    __tablename__ = "industry_project_details"
    project_id = mapped_column(ForeignKey("projects.id"), primary_key=True)
    category = mapped_column(String(100), default="")
    deliverables = mapped_column(Text, default="[]")
    instructions = mapped_column(Text, default="")
    duration_weeks = mapped_column(Integer)
    participation = mapped_column(String(20), default="Individual")
    team_size_min = mapped_column(Integer, default=1)
    team_size_max = mapped_column(Integer, default=1)
    references = mapped_column(Text, default="[]")


class IndustrySubmissionDetails(Base):
    __tablename__ = "industry_submission_details"
    submission_id = mapped_column(ForeignKey("project_submissions.id"), primary_key=True)
    summary = mapped_column(Text, default="")
    demo_url = mapped_column(String(500), default="")
    report_url = mapped_column(String(500), default="")
    skills_used = mapped_column(Text, default="[]")


class IndustrySubmissionRevision(Base):
    __tablename__ = "industry_submission_revisions"
    id = mapped_column(Integer, primary_key=True)
    submission_id = mapped_column(ForeignKey("project_submissions.id"), nullable=False, index=True)
    revision_number = mapped_column(Integer, nullable=False)
    submitted_at = mapped_column(DateTime, default=_now, nullable=False)
    summary = mapped_column(Text, default="")
    description = mapped_column(Text, default="")
    github_url = mapped_column(String(500), default="")
    demo_url = mapped_column(String(500), default="")
    report_url = mapped_column(String(500), default="")
    evidence = mapped_column(Text, default="")
    skills_used = mapped_column(Text, default="[]")


class IndustrySubmissionReview(Base):
    __tablename__ = "industry_submission_reviews"
    id = mapped_column(Integer, primary_key=True)
    submission_id = mapped_column(ForeignKey("project_submissions.id"), nullable=False, index=True)
    reviewer_user_id = mapped_column(ForeignKey("users.id"), nullable=False)
    decision = mapped_column(String(30), nullable=False)
    overall_feedback = mapped_column(Text, default="")
    technical_feedback = mapped_column(Text, default="")
    code_quality_feedback = mapped_column(Text, default="")
    problem_solving_feedback = mapped_column(Text, default="")
    strengths = mapped_column(Text, default="")
    improvement_areas = mapped_column(Text, default="")
    recommended_skills = mapped_column(Text, default="[]")
    rating = mapped_column(Integer)
    revision_instructions = mapped_column(Text, default="")
    reviewed_at = mapped_column(DateTime, default=_now, nullable=False)


class JobVacancyRequirements(Base):
    __tablename__ = "job_vacancy_requirements"
    vacancy_id = mapped_column(ForeignKey("job_vacancies.id"), primary_key=True)
    mandatory_education = mapped_column(String(180), default="")
    mandatory_department = mapped_column(String(120), default="")
    mandatory_certifications = mapped_column(Text, default="[]")
    experience_requirement = mapped_column(String(255), default="")
    internship_duration = mapped_column(String(100), default="")
    openings = mapped_column(Integer, default=1)
    application_instructions = mapped_column(Text, default="")


class IndustryApplicationStatusHistory(Base):
    __tablename__ = "industry_application_status_history"
    id = mapped_column(Integer, primary_key=True)
    job_application_id = mapped_column(ForeignKey("job_applications.id"), nullable=False, index=True)
    recruiter_user_id = mapped_column(ForeignKey("users.id"), nullable=False)
    previous_status = mapped_column(String(30), default="")
    status = mapped_column(String(30), nullable=False)
    note = mapped_column(Text, default="")
    changed_at = mapped_column(DateTime, default=_now, nullable=False)


class IndustryPortalNotification(Base):
    __tablename__ = "industry_portal_notifications"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title = mapped_column(String(180), nullable=False)
    message = mapped_column(Text, default="")
    kind = mapped_column(String(40), default="UPDATE")
    read = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime, default=_now, nullable=False)


class CompanyProfileInput(BaseModel):
    company_name: str = Field(min_length=2, max_length=180)
    industry_type: str = Field(default="Technology", max_length=120)
    description: str = Field(default="", max_length=4000)
    website: str = Field(default="", max_length=500)
    company_email: str = Field(default="", max_length=255)
    contact_person: str = Field(default="", max_length=120)
    contact_title: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=60)
    logo_url: str = Field(default="", max_length=500)

    @field_validator("website", "logo_url")
    @classmethod
    def validate_urls(cls, value: str):
        value = value.strip()
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("Website and logo links must be valid http or https URLs")
        return value


class SharingInput(BaseModel):
    share_social_links: bool


ProfileType = Literal["linkedin", "github", "leetcode"]


class ApplicationConsentInput(BaseModel):
    profile_types: list[ProfileType] = Field(default_factory=list, max_length=3)
    consent_decision: Literal["GRANTED", "DECLINED"]


class ProfileAccessRequestInput(BaseModel):
    profile_types: list[ProfileType] = Field(min_length=1, max_length=3)


class ProfileAccessDecisionInput(BaseModel):
    granted_profile_types: list[ProfileType] = Field(default_factory=list, max_length=3)
    decision: Literal["GRANTED", "DECLINED"]


class RevokeProfileAccessInput(BaseModel):
    profile_types: list[ProfileType] | None = Field(default=None, max_length=3)


def _consent_profile_types(consent: JobApplicationProfileConsent, field: str) -> list[str]:
    values = json.loads(getattr(consent, field) or "[]")
    return values if isinstance(values, list) else []


def _profile_consent_payload(consent: JobApplicationProfileConsent | None):
    if consent is None:
        return {"profile_access_status": "NOT_GRANTED", "requested_profile_types": [], "granted_profile_types": []}
    granted = _consent_profile_types(consent, "granted_profile_types") if consent.revoked_at is None else []
    return {
        "profile_access_status": consent.status,
        "requested_profile_types": _consent_profile_types(consent, "requested_profile_types"),
        "granted_profile_types": granted,
        "consent_created_at": consent.created_at.isoformat() if consent.created_at else None,
        "consent_updated_at": consent.updated_at.isoformat() if consent.updated_at else None,
        "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
    }


class PortalProjectInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=12000)
    category: str = Field(default="Technology", max_length=100)
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = "Intermediate"
    required_skill_levels: dict[str, int] = Field(default_factory=dict, max_length=40)
    expected_outcome: str = Field(default="", max_length=4000)
    acceptance_criteria: str = Field(default="", max_length=4000)
    instructions: str = Field(default="", max_length=12000)
    deliverables: list[str] = Field(default_factory=list, max_length=30)
    references: list[str] = Field(default_factory=list, max_length=20)
    deadline: str = Field(default="", max_length=50)
    duration_weeks: int | None = Field(default=None, ge=1, le=104)
    participation: Literal["Individual", "Team"] = "Individual"
    team_size_min: int = Field(default=1, ge=1, le=50)
    team_size_max: int = Field(default=1, ge=1, le=50)
    eligibility: str = Field(default="", max_length=2000)
    publication_status: Literal["DRAFT", "PUBLISHED", "CLOSED"] = "PUBLISHED"

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, value: str):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Deadline must use YYYY-MM-DD format") from exc
        return value

    @field_validator("required_skill_levels")
    @classmethod
    def validate_skill_levels(cls, value: dict[str, int]):
        if any(not name.strip() or not 1 <= level <= 5 for name, level in value.items()):
            raise ValueError("Skills must have a name and a required level from 1 to 5")
        return {name.strip(): level for name, level in value.items()}

    @field_validator("deliverables", "references")
    @classmethod
    def validate_text_items(cls, value: list[str]):
        if any(not item.strip() or len(item.strip()) > 500 for item in value):
            raise ValueError("List items must be non-empty and no longer than 500 characters")
        return [item.strip() for item in value]

    @field_validator("team_size_max")
    @classmethod
    def validate_team_size(cls, value: int, info):
        minimum = info.data.get("team_size_min", 1)
        if value < minimum:
            raise ValueError("Maximum team size cannot be smaller than minimum team size")
        return value


class PortalSubmissionInput(BaseModel):
    summary: str = Field(min_length=3, max_length=2000)
    description: str = Field(min_length=10, max_length=12000)
    github_url: str = Field(default="", max_length=500)
    demo_url: str = Field(default="", max_length=500)
    report_url: str = Field(default="", max_length=500)
    evidence: str = Field(default="", max_length=4000)
    skills_used: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("github_url", "demo_url", "report_url")
    @classmethod
    def validate_external_url(cls, value: str):
        value = value.strip()
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("Links must be valid http or https URLs")
        return value


class SubmissionReviewInput(BaseModel):
    decision: Literal["NEEDS_REVISION", "ACCEPTED", "REJECTED"]
    overall_feedback: str = Field(min_length=3, max_length=4000)
    technical_feedback: str = Field(default="", max_length=3000)
    code_quality_feedback: str = Field(default="", max_length=3000)
    problem_solving_feedback: str = Field(default="", max_length=3000)
    strengths: str = Field(default="", max_length=3000)
    improvement_areas: str = Field(default="", max_length=3000)
    recommended_skills: list[str] = Field(default_factory=list, max_length=30)
    rating: int | None = Field(default=None, ge=1, le=5)
    revision_instructions: str = Field(default="", max_length=3000)


class JobRequirementInput(BaseModel):
    mandatory_education: str = Field(default="", max_length=180)
    mandatory_department: str = Field(default="", max_length=120)
    mandatory_certifications: list[str] = Field(default_factory=list, max_length=30)
    experience_requirement: str = Field(default="", max_length=255)
    internship_duration: str = Field(default="", max_length=100)
    openings: int = Field(default=1, ge=1, le=10000)
    application_instructions: str = Field(default="", max_length=3000)


class PortalVacancyInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=10, max_length=12000)
    location: str = Field(default="Remote", max_length=160)
    employment_type: Literal["Full-time", "Part-time", "Internship", "Contract"] = "Full-time"
    eligibility: str = Field(default="", max_length=2000)
    required_skill_levels: dict[str, int] = Field(default_factory=dict, max_length=40)
    preferred_skills: list[str] = Field(default_factory=list, max_length=40)
    experience_level: str = Field(default="Entry level", max_length=80)
    deadline: str = Field(default="", max_length=50)
    status: Literal["DRAFT", "OPEN", "CLOSED"] = "OPEN"

    @field_validator("required_skill_levels")
    @classmethod
    def validate_skill_levels(cls, value: dict[str, int]):
        if any(not name.strip() or len(name.strip()) > 100 or not 1 <= level <= 5 for name, level in value.items()):
            raise ValueError("Skills must have a name and a required level from 1 to 5")
        return {name.strip(): level for name, level in value.items()}

    @field_validator("preferred_skills")
    @classmethod
    def validate_preferred_skills(cls, value: list[str]):
        if any(not item.strip() or len(item.strip()) > 100 for item in value):
            raise ValueError("Preferred skills must be non-empty and no longer than 100 characters")
        return list(dict.fromkeys(item.strip() for item in value))

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, value: str):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("Deadline must use YYYY-MM-DD format") from exc
        return value


def _industry_for(db: Session, user):
    main = _main()
    industry = db.scalar(select(main.Industry).where(main.Industry.user_id == user.id))
    if industry is None:
        main.fail("Industry profile not found", 404)
    return industry


def _notify(db: Session, user_id: int, title: str, message: str, kind: str):
    db.add(IndustryPortalNotification(user_id=user_id, title=title, message=message, kind=kind))


def _company_details(db: Session, industry_id: int):
    details = db.get(IndustryCompanyDetails, industry_id)
    if details is None:
        details = IndustryCompanyDetails(industry_id=industry_id)
        db.add(details)
        db.flush()
    return details


def _save_vacancy_details(db: Session, vacancy_id: int, preferred_skills: list[str], experience_level: str):
    details = db.get(IndustryVacancyDetails, vacancy_id)
    if details is None:
        details = IndustryVacancyDetails(vacancy_id=vacancy_id)
        db.add(details)
    details.preferred_skills = json.dumps(preferred_skills)
    details.experience_level = experience_level.strip()
    return details


def _company_payload(industry, details):
    return {
        "company_name": industry.company_name,
        "industry_type": industry.industry_type,
        "description": industry.description,
        "website": details.website,
        "company_email": details.company_email,
        "contact_person": details.contact_person,
        "contact_title": details.contact_title,
        "phone": details.phone,
        "logo_url": details.logo_url,
        "verification_status": details.verification_status,
    }


def _project_details(db: Session, project_id: int):
    details = db.get(IndustryProjectDetails, project_id)
    if details is None:
        return {
            "category": "",
            "deliverables": [],
            "instructions": "",
            "duration_weeks": None,
            "participation": "Individual",
            "team_size_min": 1,
            "team_size_max": 1,
            "references": [],
            "publication_status": "PUBLISHED",
        }
    return {
        "category": details.category,
        "deliverables": json.loads(details.deliverables or "[]"),
        "instructions": details.instructions,
        "duration_weeks": details.duration_weeks,
        "participation": details.participation,
        "team_size_min": details.team_size_min,
        "team_size_max": details.team_size_max,
        "references": json.loads(details.references or "[]"),
        "publication_status": "PUBLISHED",
    }


def _portal_project_payload(db: Session, project, student=None):
    from .industry_features import _project_payload

    payload = _project_payload(db, project, student)
    details = db.get(IndustryProjectDetails, project.id)
    payload.update(_project_details(db, project.id))
    if project.status == "DRAFT":
        payload["publication_status"] = "DRAFT"
    elif project.status == "CLOSED":
        payload["publication_status"] = "CLOSED"
    else:
        payload["publication_status"] = "PUBLISHED"
    if details is not None:
        payload["category"] = details.category
    return payload


def _store_project_details(details: IndustryProjectDetails, payload: PortalProjectInput):
    details.category = payload.category
    details.deliverables = json.dumps(payload.deliverables)
    details.instructions = payload.instructions
    details.duration_weeks = payload.duration_weeks
    details.participation = payload.participation
    details.team_size_min = payload.team_size_min
    details.team_size_max = payload.team_size_max
    details.references = json.dumps(payload.references)


def _latest_decision(db: Session, submission_id: int):
    return db.scalar(
        select(IndustrySubmissionReview)
        .where(IndustrySubmissionReview.submission_id == submission_id)
        .order_by(IndustrySubmissionReview.reviewed_at.desc(), IndustrySubmissionReview.id.desc())
    )


def _submission_payload(db: Session, submission, include_reviews=False):
    application = submission.application
    student = application.student
    details = db.get(IndustrySubmissionDetails, submission.id)
    reviews = db.scalars(
        select(IndustrySubmissionReview)
        .where(IndustrySubmissionReview.submission_id == submission.id)
        .order_by(IndustrySubmissionReview.reviewed_at.desc(), IndustrySubmissionReview.id.desc())
    ).all()
    output = {
        "id": submission.id,
        "project_id": application.project_id,
        "project_title": application.project.title,
        "student_id": student.id,
        "student_name": student.user.name,
        "college": student.college,
        "department": student.department,
        "year": student.year,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "summary": details.summary if details else "",
        "description": submission.description,
        "github_url": submission.github_url,
        "demo_url": details.demo_url if details else "",
        "report_url": details.report_url if details else "",
        "evidence": submission.evidence,
        "skills_used": json.loads(details.skills_used or "[]") if details else [],
        "status": application.status,
        "decision": reviews[0].decision if reviews else None,
        "revision_count": db.query(IndustrySubmissionRevision).filter_by(submission_id=submission.id).count(),
    }
    if include_reviews:
        output["reviews"] = [
            {
                "reviewer": db.get(_main().User, review.reviewer_user_id).name,
                "decision": review.decision,
                "overall_feedback": review.overall_feedback,
                "technical_feedback": review.technical_feedback,
                "code_quality_feedback": review.code_quality_feedback,
                "problem_solving_feedback": review.problem_solving_feedback,
                "strengths": review.strengths,
                "improvement_areas": review.improvement_areas,
                "recommended_skills": json.loads(review.recommended_skills or "[]"),
                "rating": review.rating,
                "revision_instructions": review.revision_instructions,
                "reviewed_at": review.reviewed_at.isoformat(),
            }
            for review in reviews
        ]
    return output


@router.get("/api/industry/company-profile")
def get_company_profile(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    payload = _company_payload(industry, _company_details(db, industry.id))
    demo_company = db.scalar(select(IndustryDemoCompany).where(IndustryDemoCompany.industry_id == industry.id))
    payload["is_demo"] = demo_company is not None
    payload["account_status"] = "DEMO" if demo_company else "UNVERIFIED"
    return _main().ok(payload)


@router.put("/api/industry/company-profile")
def update_company_profile(payload: CompanyProfileInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    details = _company_details(db, industry.id)
    industry.company_name = payload.company_name.strip()
    industry.industry_type = payload.industry_type.strip()
    industry.description = payload.description.strip()
    for field in ("website", "company_email", "contact_person", "contact_title", "phone", "logo_url"):
        setattr(details, field, getattr(payload, field).strip())
    db.commit()
    return _main().ok(_company_payload(industry, details))


@router.get("/api/student/profile-sharing")
def get_profile_sharing(user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = _main().student_for(db, user)
    sharing = db.get(StudentProfileSharing, student.id)
    return _main().ok({"share_social_links": sharing.share_social_links if sharing else False})


@router.put("/api/student/profile-sharing")
def update_profile_sharing(payload: SharingInput, user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = _main().student_for(db, user)
    sharing = db.get(StudentProfileSharing, student.id)
    if sharing is None:
        sharing = StudentProfileSharing(student_id=student.id)
        db.add(sharing)
    sharing.share_social_links = payload.share_social_links
    db.commit()
    return _main().ok({"share_social_links": sharing.share_social_links})


@router.get("/api/student/job-profile-access")
def student_job_profile_access(user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = _main().student_for(db, user)
    features = _industry_features()
    consents = db.scalars(
        select(JobApplicationProfileConsent)
        .join(features.JobApplication, JobApplicationProfileConsent.job_application_id == features.JobApplication.id)
        .join(features.JobVacancy, features.JobApplication.vacancy_id == features.JobVacancy.id)
        .where(JobApplicationProfileConsent.student_id == student.id)
        .where(features.JobApplication.student_id == student.id)
        .where(JobApplicationProfileConsent.industry_id == features.JobVacancy.industry_id)
        .order_by(JobApplicationProfileConsent.updated_at.desc())
    ).all()
    result = []
    for consent in consents:
        application = db.get(features.JobApplication, consent.job_application_id)
        vacancy = db.get(features.JobVacancy, application.vacancy_id) if application else None
        industry = db.get(_main().Industry, consent.industry_id)
        result.append({
            "job_application_id": consent.job_application_id,
            "job_title": vacancy.title if vacancy else "Unavailable job",
            "company": industry.company_name if industry else "Unavailable company",
            **_profile_consent_payload(consent),
        })
    return _main().ok(result)


@router.post("/api/student/job-applications/{application_id}/profile-access-response")
def respond_to_profile_access(application_id: int, payload: ProfileAccessDecisionInput, user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = _main().student_for(db, user)
    features = _industry_features()
    application = db.scalar(
        select(features.JobApplication).where(
            features.JobApplication.id == application_id,
            features.JobApplication.student_id == student.id,
        )
    )
    if application is None:
        _main().fail("Job application not found", 404)
    consent = db.scalar(select(JobApplicationProfileConsent).where(
        JobApplicationProfileConsent.job_application_id == application.id
    ))
    vacancy = db.get(features.JobVacancy, application.vacancy_id)
    if consent is None or consent.student_id != student.id or consent.industry_id != vacancy.industry_id:
        _main().fail("Profile access record does not match this application", 409)
    if consent.status != "REQUESTED":
        _main().fail("There is no pending profile access request", 409)
    requested = set(_consent_profile_types(consent, "requested_profile_types"))
    granted = set(_consent_profile_types(consent, "granted_profile_types")) if consent.revoked_at is None else set()
    if payload.decision == "GRANTED":
        if not set(payload.granted_profile_types).issubset(requested):
            _main().fail("Only requested profile types can be granted", 422)
        granted.update(payload.granted_profile_types)
    consent.granted_profile_types = json.dumps(sorted(granted))
    consent.status = "GRANTED" if granted else "DENIED"
    consent.updated_at = _now()
    if granted:
        consent.revoked_at = None
    industry = db.get(_main().Industry, consent.industry_id)
    _notify(
        db,
        industry.user_id,
        "Student profile access decision",
        f"The applicant responded to the profile access request for {db.get(features.JobVacancy, application.vacancy_id).title}.",
        "PROFILE_ACCESS",
    )
    db.commit()
    return _main().ok(_profile_consent_payload(consent))


@router.post("/api/student/job-applications/{application_id}/profile-access-revoke")
def revoke_job_profile_access(application_id: int, payload: RevokeProfileAccessInput, user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = _main().student_for(db, user)
    consent = db.scalar(
        select(JobApplicationProfileConsent).where(
            JobApplicationProfileConsent.job_application_id == application_id,
            JobApplicationProfileConsent.student_id == student.id,
        )
    )
    if consent is None:
        _main().fail("Profile access consent not found", 404)
    granted = set(_consent_profile_types(consent, "granted_profile_types"))
    revoked = set(payload.profile_types) if payload.profile_types is not None else granted
    granted.difference_update(revoked)
    consent.granted_profile_types = json.dumps(sorted(granted))
    consent.status = "GRANTED" if granted else "REVOKED"
    consent.updated_at = _now()
    if not granted:
        consent.revoked_at = _now()
    db.commit()
    return _main().ok(_profile_consent_payload(consent))


@router.get("/api/industry/portal/projects")
def list_portal_projects(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    projects = db.scalars(select(_main().Project).where(_main().Project.industry_id == industry.id).order_by(_main().Project.id.desc())).all()
    return _main().ok([_portal_project_payload(db, project) for project in projects])


@router.post("/api/industry/portal/projects", status_code=201)
def create_portal_project(payload: PortalProjectInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    main = _main()
    industry = _industry_for(db, user)
    if payload.participation == "Individual" and payload.team_size_max != 1:
        main.fail("Individual projects must have a team size of one", 422)
    requirements = _industry_features()._requirements(db, payload.required_skill_levels)
    status = {"DRAFT": "DRAFT", "PUBLISHED": "OPEN", "CLOSED": "CLOSED"}[payload.publication_status]
    project = main.Project(
        industry_id=industry.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        domain=payload.category.strip() or "Technology",
        difficulty=payload.difficulty,
        required_skills=", ".join(requirements),
        expected_outcome=payload.expected_outcome.strip(),
        evaluation_criteria=payload.acceptance_criteria.strip(),
        deadline=payload.deadline,
        status=status,
    )
    db.add(project)
    db.flush()
    details = IndustryProjectDetails(project_id=project.id)
    _store_project_details(details, payload)
    db.add(details)
    db.add(_industry_features().IndustryProjectCriteria(
        project_id=project.id,
        eligibility=payload.eligibility.strip(),
        required_skill_levels=json.dumps(requirements),
    ))
    db.commit()
    db.refresh(project)
    return main.ok(_portal_project_payload(db, project))


def _industry_features():
    from . import industry_features
    return industry_features


@router.put("/api/industry/portal/projects/{project_id}")
def update_portal_project(project_id: int, payload: PortalProjectInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    main = _main()
    project = _industry_features()._owned_project(db, user, project_id)
    if payload.participation == "Individual" and payload.team_size_max != 1:
        main.fail("Individual projects must have a team size of one", 422)
    requirements = _industry_features()._requirements(db, payload.required_skill_levels)
    project.title = payload.title.strip()
    project.description = payload.description.strip()
    project.domain = payload.category.strip() or "Technology"
    project.difficulty = payload.difficulty
    project.required_skills = ", ".join(requirements)
    project.expected_outcome = payload.expected_outcome.strip()
    project.evaluation_criteria = payload.acceptance_criteria.strip()
    project.deadline = payload.deadline
    project.status = {"DRAFT": "DRAFT", "PUBLISHED": "OPEN", "CLOSED": "CLOSED"}[payload.publication_status]
    details = db.get(IndustryProjectDetails, project.id)
    if details is None:
        details = IndustryProjectDetails(project_id=project.id)
        db.add(details)
    _store_project_details(details, payload)
    criteria = db.get(_industry_features().IndustryProjectCriteria, project.id)
    if criteria is None:
        criteria = _industry_features().IndustryProjectCriteria(project_id=project.id)
        db.add(criteria)
    criteria.eligibility = payload.eligibility.strip()
    criteria.required_skill_levels = json.dumps(requirements)
    db.commit()
    return main.ok(_portal_project_payload(db, project))


@router.patch("/api/industry/portal/projects/{project_id}/status")
def update_portal_project_status(project_id: int, publication_status: Literal["DRAFT", "PUBLISHED", "CLOSED"], user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    project = _industry_features()._owned_project(db, user, project_id)
    project.status = {"DRAFT": "DRAFT", "PUBLISHED": "OPEN", "CLOSED": "CLOSED"}[publication_status]
    db.commit()
    return _main().ok(_portal_project_payload(db, project))


@router.post("/api/projects/{project_id}/submission", status_code=201)
def submit_or_resubmit_project(project_id: int, payload: PortalSubmissionInput, user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    main = _main()
    student = main.student_for(db, user)
    application = db.scalar(select(main.ProjectApplication).where(main.ProjectApplication.project_id == project_id, main.ProjectApplication.student_id == student.id))
    if application is None:
        main.fail("Apply to this project before submitting", 409)
    submission = application.submission
    now = _now()
    if submission:
        last_review = _latest_decision(db, submission.id)
        if last_review is None or last_review.decision != "NEEDS_REVISION":
            main.fail("A submission can only be updated after revisions are requested", 409)
        current_details = db.get(IndustrySubmissionDetails, submission.id)
        db.add(IndustrySubmissionRevision(
            submission_id=submission.id,
            revision_number=db.query(IndustrySubmissionRevision).filter_by(submission_id=submission.id).count() + 1,
            summary=current_details.summary if current_details else "",
            description=submission.description,
            github_url=submission.github_url,
            demo_url=current_details.demo_url if current_details else "",
            report_url=current_details.report_url if current_details else "",
            evidence=submission.evidence,
            skills_used=current_details.skills_used if current_details else "[]",
        ))
        submission.description = payload.description.strip()
        submission.github_url = payload.github_url
        submission.evidence = payload.evidence.strip()
        submission.submitted_at = now
    else:
        submission = main.ProjectSubmission(
            application_id=application.id,
            description=payload.description.strip(),
            github_url=payload.github_url,
            evidence=payload.evidence.strip(),
            submitted_at=now,
        )
        db.add(submission)
        db.flush()
    details = db.get(IndustrySubmissionDetails, submission.id)
    if details is None:
        details = IndustrySubmissionDetails(submission_id=submission.id)
        db.add(details)
    details.summary = payload.summary.strip()
    details.demo_url = payload.demo_url
    details.report_url = payload.report_url
    details.skills_used = json.dumps(payload.skills_used)
    application.status = "SUBMITTED"
    _notify(db, application.project.industry.user_id, "Project submission received", f"A student submitted work for {application.project.title}.", "PROJECT_SUBMISSION")
    db.commit()
    return main.ok({"submission_id": submission.id, "status": "SUBMITTED", "submitted_at": submission.submitted_at.isoformat()})


@router.get("/api/industry/project-submissions")
def list_project_submissions(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)], status_filter: str | None = None, project_id: int | None = None):
    industry = _industry_for(db, user)
    query = select(_main().ProjectSubmission).join(_main().ProjectApplication).join(_main().Project).where(_main().Project.industry_id == industry.id)
    if project_id is not None:
        query = query.where(_main().Project.id == project_id)
    submissions = db.scalars(query.order_by(_main().ProjectSubmission.submitted_at.desc())).all()
    output = [_submission_payload(db, submission) for submission in submissions]
    if status_filter:
        output = [item for item in output if (item["decision"] or item["status"]) == status_filter]
    return _main().ok(output)


@router.get("/api/industry/portal/job-vacancies")
def list_portal_vacancies(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    features = _industry_features()
    vacancies = db.scalars(select(features.JobVacancy).where(features.JobVacancy.industry_id == industry.id).order_by(features.JobVacancy.id.desc())).all()
    return _main().ok([features._vacancy_payload(db, vacancy) for vacancy in vacancies])


@router.get("/api/industry/demo-companies")
def list_demo_companies(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    companies = db.scalars(
        select(IndustryDemoDirectoryCompany).order_by(IndustryDemoDirectoryCompany.company_name)
    ).all()
    return _main().ok([{
        "company_key": company.company_key,
        "company_name": company.company_name,
        "category": company.category,
        "description": company.description,
        "website": company.website,
        "logo_text": company.logo_text,
        "account_status": company.demo_label,
        "is_demo": True,
    } for company in companies])


@router.post("/api/industry/portal/job-vacancies", status_code=201)
def create_portal_vacancy(payload: PortalVacancyInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    features = _industry_features()
    requirements = features._requirements(db, payload.required_skill_levels)
    vacancy = features.JobVacancy(
        industry_id=industry.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        location=payload.location.strip(),
        employment_type=payload.employment_type,
        eligibility=payload.eligibility.strip(),
        required_skill_levels=json.dumps(requirements),
        deadline=payload.deadline,
        status=payload.status,
    )
    db.add(vacancy)
    db.flush()
    _save_vacancy_details(db, vacancy.id, payload.preferred_skills, payload.experience_level)
    db.commit()
    db.refresh(vacancy)
    return _main().ok(features._vacancy_payload(db, vacancy))


@router.put("/api/industry/portal/job-vacancies/{vacancy_id}")
def update_portal_vacancy(vacancy_id: int, payload: PortalVacancyInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    features = _industry_features()
    vacancy = features._owned_vacancy(db, user, vacancy_id)
    requirements = features._requirements(db, payload.required_skill_levels)
    vacancy.title = payload.title.strip()
    vacancy.description = payload.description.strip()
    vacancy.location = payload.location.strip()
    vacancy.employment_type = payload.employment_type
    vacancy.eligibility = payload.eligibility.strip()
    vacancy.required_skill_levels = json.dumps(requirements)
    vacancy.deadline = payload.deadline
    vacancy.status = payload.status
    _save_vacancy_details(db, vacancy.id, payload.preferred_skills, payload.experience_level)
    db.commit()
    return _main().ok(features._vacancy_payload(db, vacancy))


@router.patch("/api/industry/portal/job-vacancies/{vacancy_id}/status")
def update_portal_vacancy_status(vacancy_id: int, vacancy_status: Literal["DRAFT", "OPEN", "CLOSED"], user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    features = _industry_features()
    vacancy = features._owned_vacancy(db, user, vacancy_id)
    vacancy.status = vacancy_status
    db.commit()
    return _main().ok(features._vacancy_payload(db, vacancy))


@router.post("/api/industry/project-submissions/{submission_id}/reviews", status_code=201)
def review_project_submission(submission_id: int, payload: SubmissionReviewInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    main = _main()
    industry = _industry_for(db, user)
    submission = db.scalar(
        select(main.ProjectSubmission)
        .join(main.ProjectApplication)
        .join(main.Project)
        .where(main.ProjectSubmission.id == submission_id, main.Project.industry_id == industry.id)
    )
    if submission is None:
        main.fail("Project submission not found", 404)
    previous = _latest_decision(db, submission.id)
    if previous and previous.decision in {"ACCEPTED", "REJECTED"}:
        main.fail("A final review decision has already been recorded", 409)
    if payload.decision == "NEEDS_REVISION" and not payload.revision_instructions.strip():
        main.fail("Revision instructions are required when requesting changes", 422)
    review = IndustrySubmissionReview(
        submission_id=submission.id,
        reviewer_user_id=user.id,
        decision=payload.decision,
        overall_feedback=payload.overall_feedback.strip(),
        technical_feedback=payload.technical_feedback.strip(),
        code_quality_feedback=payload.code_quality_feedback.strip(),
        problem_solving_feedback=payload.problem_solving_feedback.strip(),
        strengths=payload.strengths.strip(),
        improvement_areas=payload.improvement_areas.strip(),
        recommended_skills=json.dumps(payload.recommended_skills),
        rating=payload.rating,
        revision_instructions=payload.revision_instructions.strip(),
    )
    db.add(review)
    application = submission.application
    application.status = {
        "NEEDS_REVISION": "REVISION_REQUESTED",
        "ACCEPTED": "COMPLETED",
        "REJECTED": "REJECTED",
    }[payload.decision]
    _notify(
        db,
        application.student.user_id,
        "Project review available",
        f"Your submission for {application.project.title} was reviewed: {payload.decision.replace('_', ' ').lower()}.",
        "PROJECT_REVIEW",
    )
    db.commit()
    return main.ok({"id": review.id, "decision": review.decision, "reviewed_at": review.reviewed_at.isoformat()})


@router.get("/api/student/project-submissions")
def student_project_submissions(user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = _main().student_for(db, user)
    submissions = db.scalars(
        select(_main().ProjectSubmission)
        .join(_main().ProjectApplication)
        .where(_main().ProjectApplication.student_id == student.id)
        .order_by(_main().ProjectSubmission.submitted_at.desc())
    ).all()
    return _main().ok([_submission_payload(db, item, include_reviews=True) for item in submissions])


@router.post("/api/industry/job-applications/{application_id}/profile-access-request")
def request_job_profile_access(application_id: int, payload: ProfileAccessRequestInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    features = _industry_features()
    application = db.scalar(
        select(features.JobApplication)
        .join(features.JobVacancy)
        .where(features.JobApplication.id == application_id, features.JobVacancy.industry_id == industry.id)
    )
    if application is None:
        _main().fail("Job application not found", 404)
    consent = db.scalar(select(JobApplicationProfileConsent).where(
        JobApplicationProfileConsent.job_application_id == application.id
    ))
    if consent is not None and (
        consent.student_id != application.student_id or consent.industry_id != industry.id
    ):
        _main().fail("Profile access record does not match this application", 409)
    if consent is None:
        consent = JobApplicationProfileConsent(
            student_id=application.student_id,
            industry_id=industry.id,
            job_application_id=application.id,
            requested_profile_types="[]",
            granted_profile_types="[]",
            status="NOT_GRANTED",
        )
        db.add(consent)
        db.flush()
    consent.requested_profile_types = json.dumps(sorted(set(payload.profile_types)))
    consent.status = "REQUESTED"
    consent.updated_at = _now()
    student = application.student
    _notify(
        db,
        student.user_id,
        "Company requested profile access",
        f"{industry.company_name} requested selected professional profile links for {db.get(features.JobVacancy, application.vacancy_id).title}. Review and respond in Profile Sharing.",
        "PROFILE_ACCESS_REQUEST",
    )
    db.commit()
    return _main().ok(_profile_consent_payload(consent))


@router.get("/api/industry/job-applications/{application_id}/profiles")
def permitted_job_applicant_profiles(application_id: int, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    features = _industry_features()
    application = db.scalar(
        select(features.JobApplication)
        .join(features.JobVacancy)
        .where(features.JobApplication.id == application_id, features.JobVacancy.industry_id == industry.id)
    )
    if application is None:
        _main().fail("Job application not found", 404)
    consent = db.scalar(select(JobApplicationProfileConsent).where(
        JobApplicationProfileConsent.job_application_id == application.id
    ))
    if consent is not None and (
        consent.student_id != application.student_id or consent.industry_id != industry.id
    ):
        _main().fail("Profile access record does not match this application", 409)
    if consent is None or consent.revoked_at is not None:
        _main().fail("Student permission required", 403)
    granted = set(_consent_profile_types(consent, "granted_profile_types"))
    if not granted:
        _main().fail("Student permission required", 403)
    profile = db.scalar(select(_main().LearningProfile).where(_main().LearningProfile.student_id == application.student_id))
    if profile is None:
        return _main().ok({"profile_access_status": consent.status, "profiles": {}})
    fields = {"linkedin": "linkedin_url", "github": "github_url", "leetcode": "leetcode_url"}
    permitted = {
        name: getattr(profile, field)
        for name, field in fields.items()
        if name in granted and getattr(profile, field)
    }
    return _main().ok({"profile_access_status": consent.status, "profiles": permitted})


@router.get("/api/industry/notifications")
@router.get("/api/student/notifications")
def list_notifications(user: Annotated[object, Depends(_main().current_user)], db: Annotated[Session, Depends(get_db)]):
    notifications = db.scalars(
        select(IndustryPortalNotification)
        .where(IndustryPortalNotification.user_id == user.id)
        .order_by(IndustryPortalNotification.created_at.desc())
        .limit(100)
    ).all()
    return _main().ok([
        {"id": item.id, "title": item.title, "message": item.message, "kind": item.kind, "read": item.read, "created_at": item.created_at.isoformat()}
        for item in notifications
    ])


@router.get("/api/student/application-status-history")
def student_application_status_history(user: Annotated[object, Depends(_main().require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    main = _main()
    student = main.student_for(db, user)
    features = _industry_features()
    history = db.scalars(
        select(IndustryApplicationStatusHistory)
        .join(features.JobApplication, IndustryApplicationStatusHistory.job_application_id == features.JobApplication.id)
        .where(features.JobApplication.student_id == student.id)
        .order_by(IndustryApplicationStatusHistory.changed_at.desc())
    ).all()
    return main.ok([
        {
            "application_id": item.job_application_id,
            "status": item.status,
            "note": item.note,
            "changed_at": item.changed_at.isoformat(),
        }
        for item in history
    ])


@router.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: Annotated[object, Depends(_main().current_user)], db: Annotated[Session, Depends(get_db)]):
    notification = db.scalar(
        select(IndustryPortalNotification).where(
            IndustryPortalNotification.id == notification_id,
            IndustryPortalNotification.user_id == user.id,
        )
    )
    if notification is None:
        _main().fail("Notification not found", 404)
    notification.read = True
    db.commit()
    return _main().ok({"id": notification.id, "read": notification.read})


@router.get("/api/industry/portal/dashboard")
def portal_dashboard(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = _industry_for(db, user)
    main = _main()
    project_ids = select(main.Project.id).where(main.Project.industry_id == industry.id)
    vacancy_ids = select(_industry_features().JobVacancy.id).where(_industry_features().JobVacancy.industry_id == industry.id)
    projects = db.scalars(select(main.Project).where(main.Project.industry_id == industry.id)).all()
    vacancies = db.scalars(select(_industry_features().JobVacancy).where(_industry_features().JobVacancy.industry_id == industry.id)).all()
    submissions = db.scalars(select(main.ProjectSubmission).join(main.ProjectApplication).where(main.ProjectApplication.project_id.in_(project_ids))).all()
    applications = db.scalars(select(_industry_features().JobApplication).where(_industry_features().JobApplication.vacancy_id.in_(vacancy_ids))).all()
    job_status_counts = {
        status: sum(application.status == status for application in applications)
        for status in ("APPLIED", "REVIEWING", "SHORTLISTED", "INTERVIEW", "SELECTED")
    }
    project_applications = db.scalars(select(main.ProjectApplication).where(main.ProjectApplication.project_id.in_(project_ids))).all()
    latest_decisions = [_latest_decision(db, item.id) for item in submissions]
    pending = sum(
        decision is None or (item.submitted_at is not None and item.submitted_at > decision.reviewed_at)
        for item, decision in zip(submissions, latest_decisions)
    )
    features = _industry_features()
    project_reviews = db.scalars(
        select(features.ProjectApplicationReview).where(
            features.ProjectApplicationReview.project_application_id.in_([item.id for item in project_applications])
        )
    ).all()
    shortlisted = sum(item.status == "SHORTLISTED" for item in applications) + sum(
        item.status == "SHORTLISTED" for item in project_reviews
    )
    return main.ok({
        "active_projects": sum(item.status == "OPEN" for item in projects),
        "submissions_awaiting_review": pending,
        "published_opportunities": sum(item.status == "OPEN" for item in vacancies),
        "applications_received": len(applications) + len(project_applications),
        "shortlisted_candidates": shortlisted,
        "job_vacancies_total": len(vacancies),
        "job_vacancies_open": sum(item.status == "OPEN" for item in vacancies),
        "job_applications_total": len(applications),
        "job_applications_awaiting_review": job_status_counts["APPLIED"] + job_status_counts["REVIEWING"],
        "job_applications_shortlisted": job_status_counts["SHORTLISTED"],
        "job_applications_interview": job_status_counts["INTERVIEW"],
        "job_applications_selected": job_status_counts["SELECTED"],
        "eligible_candidates": None,
        "eligible_candidates_note": "Eligibility evaluation is available per application; no aggregate eligibility count is inferred.",
    })


@router.get("/api/industry/job-applications/analysis")
def analyze_job_applications(user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)], vacancy_id: int | None = None):
    main = _main()
    industry = _industry_for(db, user)
    features = _industry_features()
    query = select(features.JobApplication).join(features.JobVacancy).where(features.JobVacancy.industry_id == industry.id)
    if vacancy_id is not None:
        query = query.where(features.JobVacancy.id == vacancy_id)
    applications = db.scalars(query.order_by(features.JobApplication.applied_at.desc())).all()
    result = []
    for application in applications:
        vacancy = db.get(features.JobVacancy, application.vacancy_id)
        student = application.student
        requirements = json.loads(vacancy.required_skill_levels or "{}")
        match = _industry_features()._student_match(db, student, requirements)
        assessed = any(item["evidence"].__contains__("Completed assessment") for item in match["skill_details"])
        detailed_requirements = db.get(JobVacancyRequirements, vacancy.id)
        reasons = []
        if detailed_requirements:
            if detailed_requirements.mandatory_education and student.college.casefold() != detailed_requirements.mandatory_education.casefold():
                reasons.append("Required institution not verified")
            if detailed_requirements.mandatory_department and student.department.casefold() != detailed_requirements.mandatory_department.casefold():
                reasons.append("Required department not met")
            certifications = {item.name.casefold() for item in db.scalars(select(main.Certification).where(main.Certification.student_id == student.id)).all()}
            missing_certs = [name for name in json.loads(detailed_requirements.mandatory_certifications or "[]") if name.casefold() not in certifications]
            if missing_certs:
                reasons.extend(f"Required certification not found: {name}" for name in missing_certs)
        if reasons:
            eligibility = "NOT CURRENTLY ELIGIBLE"
        elif not assessed:
            eligibility = "ASSESSMENT PENDING"
        elif not requirements or match["match_percent"] == 100:
            eligibility = "ELIGIBLE"
        elif match["match_percent"] > 0:
            eligibility = "PARTIALLY ELIGIBLE"
        else:
            eligibility = "PARTIALLY ELIGIBLE"
        result.append({
            "application_id": application.id,
            "vacancy_id": vacancy.id,
            "opportunity_title": vacancy.title,
            "opportunity_type": vacancy.employment_type,
            "student_id": student.id,
            "student_name": student.user.name,
            "college": student.college,
            "department": student.department,
            "year": student.year,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
            "status": application.status,
            "candidate_match": match,
            "eligibility": eligibility,
            "eligibility_reasons": reasons or (["Assessment evidence is not available for all required skills."] if eligibility == "ASSESSMENT PENDING" else match["explanation"]),
            "course_data_available": False,
            "course_completion_status": "Course Data Unavailable",
            "course_completion_percent": None,
            "internal_note": application.note,
        })
    return main.ok(result)


@router.put("/api/industry/job-vacancies/{vacancy_id}/requirements")
def update_job_requirements(vacancy_id: int, payload: JobRequirementInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    vacancy = _industry_features()._owned_vacancy(db, user, vacancy_id)
    details = db.get(JobVacancyRequirements, vacancy.id)
    if details is None:
        details = JobVacancyRequirements(vacancy_id=vacancy.id)
        db.add(details)
    details.mandatory_education = payload.mandatory_education.strip()
    details.mandatory_department = payload.mandatory_department.strip()
    details.mandatory_certifications = json.dumps(payload.mandatory_certifications)
    details.experience_requirement = payload.experience_requirement.strip()
    details.internship_duration = payload.internship_duration.strip()
    details.openings = payload.openings
    details.application_instructions = payload.application_instructions.strip()
    db.commit()
    return _main().ok({"vacancy_id": vacancy.id, "openings": details.openings})


@router.get("/api/industry/job-vacancies/{vacancy_id}/requirements")
def get_job_requirements(vacancy_id: int, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    vacancy = _industry_features()._owned_vacancy(db, user, vacancy_id)
    details = db.get(JobVacancyRequirements, vacancy.id)
    return _main().ok({
        "mandatory_education": details.mandatory_education if details else "",
        "mandatory_department": details.mandatory_department if details else "",
        "mandatory_certifications": json.loads(details.mandatory_certifications or "[]") if details else [],
        "experience_requirement": details.experience_requirement if details else "",
        "internship_duration": details.internship_duration if details else "",
        "openings": details.openings if details else 1,
        "application_instructions": details.application_instructions if details else "",
    })


@router.post("/api/industry/job-applications/{application_id}/status")
def update_job_application_status(application_id: int, payload: _industry_features().JobApplicationStatusInput, user: Annotated[object, Depends(_main().require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    main = _main()
    industry = _industry_for(db, user)
    features = _industry_features()
    application = db.scalar(
        select(features.JobApplication)
        .join(features.JobVacancy)
        .where(features.JobApplication.id == application_id, features.JobVacancy.industry_id == industry.id)
    )
    if application is None:
        main.fail("Job application not found", 404)
    features._validate_job_status_transition(application.status, payload.status)
    previous_status = application.status
    application.status = payload.status
    application.note = payload.note.strip()
    application.updated_at = _now()
    db.add(IndustryApplicationStatusHistory(
        job_application_id=application.id,
        recruiter_user_id=user.id,
        previous_status=previous_status,
        status=payload.status,
        note=payload.note.strip(),
    ))
    vacancy = db.get(features.JobVacancy, application.vacancy_id)
    _notify(db, application.student.user_id, "Application status updated", f"Your application for {vacancy.title} is now {payload.status.lower().replace('_', ' ')}.", "JOB_APPLICATION")
    db.commit()
    return main.ok({"application_id": application.id, "status": application.status})


app_router = router
