import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from urllib.parse import urlparse
from uuid import uuid4

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, mapped_column, relationship
from starlette.requests import Request
from starlette.responses import JSONResponse

from .database import Base, engine, get_db
from .services.learning_plan import (
    estimate_study_days,
    gap_status,
    generate_task_specs,
    learning_resources,
    level_label,
    readiness_score,
    skill_guidance,
    valid_resource_url,
)

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "local-demo-secret-change-before-deployment")
ALGORITHM = "HS256"
TOKEN_MINUTES = 60 * 12


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(120), nullable=False)
    email = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash = mapped_column(String(255), nullable=False)
    role = mapped_column(String(30), nullable=False)
    created_at = mapped_column(DateTime, default=utc_now)
    student = relationship("Student", back_populates="user", uselist=False)
    industry = relationship("Industry", back_populates="user", uselist=False)
    mentor = relationship("Mentor", back_populates="user", uselist=False)
    institution = relationship("Institution", back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    college = mapped_column(String(180), default="")
    department = mapped_column(String(120), default="")
    year = mapped_column(Integer, default=3)
    career_goal = mapped_column(String(120), default="")
    bio = mapped_column(Text, default="")
    interests = mapped_column(Text, default="")
    user = relationship("User", back_populates="student")
    skills = relationship("StudentSkill", back_populates="student", cascade="all, delete-orphan")
    roadmap = relationship("Roadmap", back_populates="student", uselist=False, cascade="all, delete-orphan")
    applications = relationship("ProjectApplication", back_populates="student")
    assessments = relationship("Assessment", back_populates="student")
    opportunity_matches = relationship("OpportunityMatch", back_populates="student", cascade="all, delete-orphan")
    learning_profile = relationship("LearningProfile", back_populates="student", uselist=False, cascade="all, delete-orphan")
    learning_plans = relationship("LearningPlan", back_populates="student", cascade="all, delete-orphan")


class LearningProfile(Base):
    __tablename__ = "learning_profiles"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    programming_languages = mapped_column(Text, default="[]")
    completed_courses = mapped_column(Text, default="[]")
    completed_projects = mapped_column(Text, default="[]")
    github_url = mapped_column(String(500), default="")
    linkedin_url = mapped_column(String(500), default="")
    leetcode_url = mapped_column(String(500), default="")
    target_companies = mapped_column(Text, default="[]")
    study_minutes_per_day = mapped_column(Integer)
    learning_language = mapped_column(String(60), default="English")
    learning_format = mapped_column(String(30), default="Mixed")
    updated_at = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    student = relationship("Student", back_populates="learning_profile")


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    career_role_id = mapped_column(ForeignKey("career_roles.id"), nullable=False)
    active = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime, default=utc_now)
    tasks = relationship("LearningTask", back_populates="plan", cascade="all, delete-orphan", order_by="LearningTask.order")
    student = relationship("Student", back_populates="learning_plans")
    career_role = relationship("CareerRole")


class LearningTask(Base):
    __tablename__ = "learning_tasks"
    id = mapped_column(Integer, primary_key=True)
    plan_id = mapped_column(ForeignKey("learning_plans.id"), nullable=False)
    order = mapped_column(Integer, nullable=False)
    phase = mapped_column(Integer, nullable=False)
    phase_name = mapped_column(String(80), nullable=False)
    skill_id = mapped_column(ForeignKey("skills.id"))
    title = mapped_column(String(180), nullable=False)
    why = mapped_column(Text, default="")
    explanation = mapped_column(Text, default="")
    prerequisites = mapped_column(Text, default="[]")
    estimated_minutes = mapped_column(Integer, default=0)
    resources = mapped_column(Text, default="[]")
    practice = mapped_column(Text, default="")
    mini_project = mapped_column(Text, default="")
    status = mapped_column(String(20), default="Not Started")
    plan = relationship("LearningPlan", back_populates="tasks")
    skill = relationship("Skill")
    __table_args__ = (UniqueConstraint("plan_id", "order"),)


class Industry(Base):
    __tablename__ = "industries"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    company_name = mapped_column(String(180), nullable=False)
    industry_type = mapped_column(String(120), default="Technology")
    description = mapped_column(Text, default="")
    user = relationship("User", back_populates="industry")
    projects = relationship("Project", back_populates="industry")
    opportunities = relationship("Opportunity", back_populates="industry")


class Institution(Base):
    __tablename__ = "institutions"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    institution_name = mapped_column(String(180), nullable=False)
    location = mapped_column(String(180), default="")
    user = relationship("User", back_populates="institution")


class InstitutionCourseEnrollment(Base):
    __tablename__ = "institution_course_enrollments"
    id = mapped_column(Integer, primary_key=True)
    institution_id = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    course_id = mapped_column(ForeignKey("courses.id"), nullable=False)
    status = mapped_column(String(20), default="PENDING", nullable=False)
    assigned_at = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at = mapped_column(DateTime)
    score = mapped_column(Float)
    student = relationship("Student")
    course = relationship("Course")
    __table_args__ = (UniqueConstraint("institution_id", "student_id", "course_id"),)


class InstitutionMentorship(Base):
    __tablename__ = "institution_mentorships"
    id = mapped_column(Integer, primary_key=True)
    institution_id = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False, unique=True)
    mentor_id = mapped_column(ForeignKey("mentors.id"))
    status = mapped_column(String(20), default="NOT_ASSIGNED", nullable=False)
    reason = mapped_column(Text, default="", nullable=False)
    notes = mapped_column(Text, default="", nullable=False)
    follow_up_date = mapped_column(Date)
    created_at = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    mentor = relationship("Mentor")


class InstitutionMentorshipHistory(Base):
    __tablename__ = "institution_mentorship_history"
    id = mapped_column(Integer, primary_key=True)
    institution_id = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    mentor_id = mapped_column(ForeignKey("mentors.id"))
    status = mapped_column(String(20), nullable=False)
    reason = mapped_column(Text, default="", nullable=False)
    notes = mapped_column(Text, default="", nullable=False)
    follow_up_date = mapped_column(Date)
    created_at = mapped_column(DateTime, default=utc_now, nullable=False)
    mentor = relationship("Mentor")


class InstitutionMentorMembership(Base):
    __tablename__ = "institution_mentor_memberships"
    id = mapped_column(Integer, primary_key=True)
    institution_id = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    mentor_id = mapped_column(ForeignKey("mentors.id"), nullable=False, index=True)
    expertise = mapped_column(String(255), default="", nullable=False)
    experience = mapped_column(Integer, default=0, nullable=False)
    active = mapped_column(Boolean, default=True, nullable=False)
    availability = mapped_column(String(40), default="AVAILABLE", nullable=False)
    created_at = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    mentor = relationship("Mentor")
    __table_args__ = (UniqueConstraint("institution_id", "mentor_id"),)


class Mentor(Base):
    __tablename__ = "mentors"
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    expertise = mapped_column(String(255), default="")
    company = mapped_column(String(180), default="")
    experience = mapped_column(Integer, default=5)
    user = relationship("User", back_populates="mentor")


class Skill(Base):
    __tablename__ = "skills"
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(100), unique=True, nullable=False)
    category = mapped_column(String(80), default="Technical")
    description = mapped_column(Text, default="")
    student_skills = relationship("StudentSkill", back_populates="skill")


class CareerRole(Base):
    __tablename__ = "career_roles"
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(120), unique=True, nullable=False)
    description = mapped_column(Text, default="")
    role_skills = relationship("RoleSkill", back_populates="role", cascade="all, delete-orphan")


class RoleSkill(Base):
    __tablename__ = "role_skills"
    id = mapped_column(Integer, primary_key=True)
    role_id = mapped_column(ForeignKey("career_roles.id"), nullable=False)
    skill_id = mapped_column(ForeignKey("skills.id"), nullable=False)
    required_level = mapped_column(Integer, default=3)
    role = relationship("CareerRole", back_populates="role_skills")
    skill = relationship("Skill")
    __table_args__ = (UniqueConstraint("role_id", "skill_id"),)


class StudentSkill(Base):
    __tablename__ = "student_skills"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False)
    skill_id = mapped_column(ForeignKey("skills.id"), nullable=False)
    proficiency = mapped_column(Integer, default=1)
    verification_status = mapped_column(String(30), default="IN PROGRESS")
    evidence = mapped_column(Text, default="")
    student = relationship("Student", back_populates="skills")
    skill = relationship("Skill", back_populates="student_skills")
    __table_args__ = (UniqueConstraint("student_id", "skill_id"),)


class Assessment(Base):
    __tablename__ = "assessments"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"))
    title = mapped_column(String(160), nullable=False)
    score = mapped_column(Float, default=0)
    completed_at = mapped_column(DateTime)
    student = relationship("Student", back_populates="assessments")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    results = relationship("AssessmentResult", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    id = mapped_column(Integer, primary_key=True)
    assessment_id = mapped_column(ForeignKey("assessments.id"), nullable=False)
    question = mapped_column(Text, nullable=False)
    options = mapped_column(Text, nullable=False)
    correct_answer = mapped_column(String(255), nullable=False)
    skill_id = mapped_column(ForeignKey("skills.id"), nullable=False)
    difficulty = mapped_column(String(30), default="Intermediate")
    assessment = relationship("Assessment", back_populates="questions")
    skill = relationship("Skill")


class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    id = mapped_column(Integer, primary_key=True)
    assessment_id = mapped_column(ForeignKey("assessments.id"), nullable=False)
    skill_id = mapped_column(ForeignKey("skills.id"), nullable=False)
    score = mapped_column(Float, default=0)
    proficiency = mapped_column(Integer, default=1)
    assessment = relationship("Assessment", back_populates="results")
    skill = relationship("Skill")


class Roadmap(Base):
    __tablename__ = "roadmaps"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    career_role_id = mapped_column(ForeignKey("career_roles.id"), nullable=False)
    created_at = mapped_column(DateTime, default=utc_now)
    student = relationship("Student", back_populates="roadmap")
    tasks = relationship("RoadmapTask", back_populates="roadmap", cascade="all, delete-orphan", order_by="RoadmapTask.week")
    career_role = relationship("CareerRole")


class RoadmapTask(Base):
    __tablename__ = "roadmap_tasks"
    id = mapped_column(Integer, primary_key=True)
    roadmap_id = mapped_column(ForeignKey("roadmaps.id"), nullable=False)
    week = mapped_column(Integer, nullable=False)
    title = mapped_column(String(180), nullable=False)
    type = mapped_column(String(40), default="LEARN")
    skill_id = mapped_column(ForeignKey("skills.id"))
    description = mapped_column(Text, default="")
    completed = mapped_column(Boolean, default=False)
    roadmap = relationship("Roadmap", back_populates="tasks")
    skill = relationship("Skill")


class Course(Base):
    __tablename__ = "courses"
    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String(180), nullable=False)
    description = mapped_column(Text, default="")
    skill_id = mapped_column(ForeignKey("skills.id"), nullable=False)
    difficulty = mapped_column(String(40), default="Beginner")
    duration = mapped_column(String(40), default="2 weeks")
    url = mapped_column(String(500), default="")
    skill = relationship("Skill")


class Project(Base):
    __tablename__ = "projects"
    id = mapped_column(Integer, primary_key=True)
    industry_id = mapped_column(ForeignKey("industries.id"), nullable=False)
    title = mapped_column(String(180), nullable=False)
    description = mapped_column(Text, default="")
    domain = mapped_column(String(100), default="")
    difficulty = mapped_column(String(40), default="Intermediate")
    required_skills = mapped_column(Text, default="")
    expected_outcome = mapped_column(Text, default="")
    evaluation_criteria = mapped_column(Text, default="")
    deadline = mapped_column(String(50), default="")
    status = mapped_column(String(30), default="OPEN")
    industry = relationship("Industry", back_populates="projects")
    applications = relationship("ProjectApplication", back_populates="project", cascade="all, delete-orphan")


class ProjectApplication(Base):
    __tablename__ = "project_applications"
    id = mapped_column(Integer, primary_key=True)
    project_id = mapped_column(ForeignKey("projects.id"), nullable=False)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False)
    status = mapped_column(String(30), default="APPLIED")
    applied_at = mapped_column(DateTime, default=utc_now)
    project = relationship("Project", back_populates="applications")
    student = relationship("Student", back_populates="applications")
    submission = relationship("ProjectSubmission", back_populates="application", uselist=False, cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint("project_id", "student_id"),)


class ProjectSubmission(Base):
    __tablename__ = "project_submissions"
    id = mapped_column(Integer, primary_key=True)
    application_id = mapped_column(ForeignKey("project_applications.id"), unique=True, nullable=False)
    description = mapped_column(Text, default="")
    github_url = mapped_column(String(500), default="")
    evidence = mapped_column(Text, default="")
    submitted_at = mapped_column(DateTime, default=utc_now)
    application = relationship("ProjectApplication", back_populates="submission")
    evaluation = relationship("ProjectEvaluation", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class ProjectEvaluation(Base):
    __tablename__ = "project_evaluations"
    id = mapped_column(Integer, primary_key=True)
    submission_id = mapped_column(ForeignKey("project_submissions.id"), unique=True, nullable=False)
    mentor_id = mapped_column(ForeignKey("mentors.id"), nullable=False)
    technical_quality = mapped_column(Integer, default=3)
    problem_solving = mapped_column(Integer, default=3)
    code_quality = mapped_column(Integer, default=3)
    communication = mapped_column(Integer, default=3)
    innovation = mapped_column(Integer, default=3)
    overall_score = mapped_column(Float, default=0)
    feedback = mapped_column(Text, default="")
    evaluated_at = mapped_column(DateTime, default=utc_now)
    submission = relationship("ProjectSubmission", back_populates="evaluation")
    mentor = relationship("Mentor")


class Opportunity(Base):
    __tablename__ = "opportunities"
    id = mapped_column(Integer, primary_key=True)
    industry_id = mapped_column(ForeignKey("industries.id"), nullable=False)
    title = mapped_column(String(180), nullable=False)
    type = mapped_column(String(60), default="Internship")
    description = mapped_column(Text, default="")
    required_skills = mapped_column(Text, default="")
    location = mapped_column(String(120), default="Remote")
    eligibility = mapped_column(String(255), default="Students")
    industry = relationship("Industry", back_populates="opportunities")
    matches = relationship("OpportunityMatch", back_populates="opportunity", cascade="all, delete-orphan")


class OpportunityMatch(Base):
    __tablename__ = "opportunity_matches"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False)
    opportunity_id = mapped_column(ForeignKey("opportunities.id"), nullable=False)
    match_score = mapped_column(Float, default=0)
    matched_skills = mapped_column(Text, default="")
    missing_skills = mapped_column(Text, default="")
    updated_at = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    student = relationship("Student", back_populates="opportunity_matches")
    opportunity = relationship("Opportunity", back_populates="matches")
    __table_args__ = (UniqueConstraint("student_id", "opportunity_id"),)


class Certification(Base):
    __tablename__ = "certifications"
    id = mapped_column(Integer, primary_key=True)
    student_id = mapped_column(ForeignKey("students.id"), nullable=False)
    name = mapped_column(String(180), nullable=False)
    issuer = mapped_column(String(160), default="")
    date = mapped_column(String(40), default="")
    credential_url = mapped_column(String(500), default="")


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterInput(Credentials):
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(student|industry|institution)$")


class ProfileInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    college: str = ""
    department: str = ""
    year: int = Field(ge=1, le=8)
    bio: str = ""
    interests: str = ""


class SkillProfileInput(BaseModel):
    skill_name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=0, le=5)


class LearningProfileInput(BaseModel):
    current_skills: list[SkillProfileInput] | None = Field(default=None, max_length=100)
    programming_languages: list[str] | None = None
    completed_courses: list[str] | None = None
    completed_projects: list[str] | None = None
    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)
    leetcode_url: str | None = Field(default=None, max_length=500)
    career_goal: str | None = Field(default=None, max_length=120)
    target_companies: list[str] | None = None
    study_minutes_per_day: int | None = Field(default=None, ge=5, le=720)
    learning_language: str | None = Field(default=None, min_length=2, max_length=60)
    learning_format: Literal["Video", "Reading", "Interactive", "Mixed"] | None = None

    @field_validator("github_url", "linkedin_url", "leetcode_url")
    @classmethod
    def validate_profile_url(cls, value: str | None):
        if value is None or not value.strip():
            return ""
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Profile URLs must be valid http or https URLs")
        return normalized

    @field_validator("github_url")
    @classmethod
    def validate_github_profile_url(cls, value: str | None):
        host = urlparse(value).hostname if value else None
        if host and not (host == "github.com" or host.endswith(".github.com")):
            raise ValueError("GitHub profile URLs must use github.com or its subdomains")
        return value

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_profile_url(cls, value: str | None):
        host = urlparse(value).hostname if value else None
        if host and not (host == "linkedin.com" or host.endswith(".linkedin.com")):
            raise ValueError("LinkedIn profile URLs must use linkedin.com or its subdomains")
        return value

    @field_validator("leetcode_url")
    @classmethod
    def validate_leetcode_profile_url(cls, value: str | None):
        host = urlparse(value).hostname if value else None
        if host and not (host == "leetcode.com" or host.endswith(".leetcode.com")):
            raise ValueError("LeetCode profile URLs must use leetcode.com or its subdomains")
        return value

    @field_validator("programming_languages", "completed_courses", "completed_projects", "target_companies")
    @classmethod
    def validate_string_lists(cls, value: list[str] | None):
        if value is None:
            return None
        if len(value) > 50 or any(not item.strip() or len(item.strip()) > 180 for item in value):
            raise ValueError("List entries must be non-empty and no longer than 180 characters")
        return list(dict.fromkeys(item.strip() for item in value))


class LearningTaskStatusInput(BaseModel):
    status: Literal["Not Started", "In Progress", "Completed"]


class InstitutionCourseEnrollmentInput(BaseModel):
    course_id: int = Field(ge=1)


class InstitutionCourseStatusInput(BaseModel):
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED"]
    score: float | None = Field(default=None, ge=0, le=100)


class InstitutionMentorshipInput(BaseModel):
    mentor_id: int | None = Field(default=None, ge=1)
    status: Literal["NOT_ASSIGNED", "ASSIGNED", "IN_PROGRESS", "COMPLETED"]
    reason: str = Field(default="", max_length=1000)
    notes: str = Field(default="", max_length=5000)
    follow_up_date: date | None = None


class InstitutionMentorInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    expertise: str = Field(min_length=2, max_length=255)
    experience: int = Field(ge=0, le=60)
    password: str = Field(min_length=12, max_length=128)
    availability: Literal["AVAILABLE", "LIMITED", "UNAVAILABLE"] = "AVAILABLE"


class InstitutionMentorAssociationInput(BaseModel):
    email: EmailStr


class InstitutionMentorUpdateInput(BaseModel):
    expertise: str = Field(min_length=2, max_length=255)
    experience: int = Field(ge=0, le=60)
    availability: Literal["AVAILABLE", "LIMITED", "UNAVAILABLE"]
    active: bool


class CareerInput(BaseModel):
    career_goal: str


class AssessmentAnswer(BaseModel):
    question_id: int = Field(ge=1)
    answer: str = Field(min_length=1)


class AnswersInput(BaseModel):
    answers: list[AssessmentAnswer] = Field(min_length=1)


class ProjectInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str
    domain: str = "Technology"
    difficulty: str = "Intermediate"
    required_skills: list[str] = []
    expected_outcome: str = ""
    evaluation_criteria: str = ""
    deadline: str = ""


class SubmissionInput(BaseModel):
    description: str = Field(min_length=10)
    github_url: str = ""
    evidence: str = ""


class EvaluationInput(BaseModel):
    technical_quality: int = Field(ge=1, le=5)
    problem_solving: int = Field(ge=1, le=5)
    code_quality: int = Field(ge=1, le=5)
    communication: int = Field(ge=1, le=5)
    innovation: int = Field(ge=1, le=5)
    feedback: str = Field(min_length=3, max_length=2000)


class ExtractInput(BaseModel):
    description: str = Field(min_length=10, max_length=12000)


class RequirementInput(BaseModel):
    role_name: str
    skill_name: str
    required_level: int = Field(ge=1, le=5)


security = HTTPBearer(auto_error=False)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SkillBridge AI API", version="1.0.0", description="Industry-academia skill intelligence platform", lifespan=lifespan)
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in origins], allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Request-ID"])


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exc: HTTPException):
    detail = exc.detail
    message = detail.get("message", "Request failed") if isinstance(detail, dict) else str(detail)
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": message}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    messages = [error["msg"] for error in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"success": False, "message": "; ".join(messages) or "Invalid request"})


def ok(data):
    return {"success": True, "data": data}


def fail(message: str, code: int = 400):
    raise HTTPException(status_code=code, detail={"success": False, "message": message})


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310_000).hex()
        return hmac.compare_digest(actual, digest_hex)
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "role": user.role, "iat": now, "exp": now + timedelta(minutes=TOKEN_MINUTES)}, SECRET_KEY, algorithm=ALGORITHM)


def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)], db: Annotated[Session, Depends(get_db)]) -> User:
    if credentials is None:
        fail("Authentication required", status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", ""))
    except (jwt.InvalidTokenError, ValueError, TypeError):
        fail("Invalid or expired token", status.HTTP_401_UNAUTHORIZED)
    user = db.get(User, user_id)
    if user is None:
        fail("User not found", status.HTTP_401_UNAUTHORIZED)
    return user


def require_role(*roles):
    def check(request: Request, user: Annotated[User, Depends(current_user)]):
        if user.role not in roles:
            logger.warning(
                "Authorization denied: request_id=%s method=%s path=%s actual_role=%s expected_roles=%s",
                request.state.request_id,
                request.method,
                request.url.path,
                user.role,
                ",".join(roles),
            )
            fail("You do not have permission to access this resource", status.HTTP_403_FORBIDDEN)
        return user
    return check


def student_for(db: Session, user: User) -> Student:
    student = db.scalar(select(Student).where(Student.user_id == user.id))
    if student is None:
        fail("Student profile not found", 404)
    return student


def learning_profile_for(db: Session, student: Student) -> LearningProfile | None:
    return db.scalar(select(LearningProfile).where(LearningProfile.student_id == student.id))


def json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def learning_profile_payload(student: Student, profile: LearningProfile | None):
    return {
        "career_goal": student.career_goal,
        "current_skills": [
            {
                "skill_name": item.skill.name,
                "proficiency": item.proficiency,
                "level": level_label(item.proficiency),
                "verification_status": item.verification_status,
                "evidence": item.evidence,
            }
            for item in sorted(student.skills, key=lambda entry: entry.skill.name.lower())
        ],
        "programming_languages": json_list(profile.programming_languages) if profile else [],
        "completed_courses": json_list(profile.completed_courses) if profile else [],
        "completed_projects": json_list(profile.completed_projects) if profile else [],
        "github_url": profile.github_url if profile else "",
        "linkedin_url": profile.linkedin_url if profile else "",
        "leetcode_url": profile.leetcode_url if profile else "",
        "target_companies": json_list(profile.target_companies) if profile else [],
        "study_minutes_per_day": profile.study_minutes_per_day if profile else None,
        "learning_language": profile.learning_language if profile else "English",
        "learning_format": profile.learning_format if profile else "Mixed",
    }


def learning_analysis_data(db: Session, student: Student, profile: LearningProfile | None):
    role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal)) if student.career_goal else None
    if role is None:
        return {
            "career_goal": student.career_goal,
            "engine": "rule-based",
            "provisional": True,
            "provisional_reasons": ["Choose a configured career role to compare skills against its requirements."],
            "readiness": None,
            "readiness_calculation": "Equal-weight average of min(current proficiency / required proficiency, 1) for each configured role skill.",
            "skills": [],
            "next_recommended_action": "Select a career goal.",
        }

    known = {item.skill.name.lower(): item.proficiency for item in student.skills}
    gaps = []
    for requirement in role.role_skills:
        skill = requirement.skill
        current = max(0, known.get(skill.name.lower(), 0))
        required = requirement.required_level
        difference = max(0, required - current)
        guidance = skill_guidance(skill.name)
        prerequisites = []
        for name in guidance["prerequisites"]:
            current_prerequisite = next((item for item in student.skills if item.skill.name.lower() == name.lower()), None)
            prerequisites.append({
                "skill": name,
                "current": current_prerequisite.proficiency if current_prerequisite else 0,
                "level": level_label(current_prerequisite.proficiency) if current_prerequisite else "Not learned",
            })
        gaps.append({
            "skill_id": skill.id,
            "skill": skill.name,
            "category": skill.category,
            "required": required,
            "required_level": level_label(required),
            "current": current,
            "current_level": level_label(current),
            "gap": difference,
            "status": gap_status(required, current),
            "priority": "High" if difference >= 3 else "Medium" if difference == 2 else "Low" if difference == 1 else "Maintain",
            "priority_score": difference * 10 + required,
            "why_it_matters": guidance["why"],
            "prerequisites": prerequisites,
            "known_skills": [{"skill": item.skill.name, "proficiency": item.proficiency} for item in student.skills],
        })
    gaps.sort(key=lambda item: (-item["priority_score"], item["skill"].lower()))
    has_assessment = db.scalar(
        select(Assessment.id).where(
            Assessment.student_id == student.id,
            Assessment.completed_at.is_not(None),
        ).limit(1)
    ) is not None
    provisional_reasons = []
    if not student.skills:
        provisional_reasons.append("No current skills are in your profile yet; unlisted skills are treated as not learned.")
    elif any(requirement.skill.name.lower() not in known for requirement in role.role_skills):
        provisional_reasons.append("Some role-required skills have no profile entry and are treated as not learned.")
    if not has_assessment:
        provisional_reasons.append("No completed diagnostic assessment is recorded; listed proficiency is self-reported or seeded.")
    return {
        "career_goal": role.name,
        "engine": "rule-based",
        "provisional": bool(provisional_reasons),
        "provisional_reasons": provisional_reasons,
        "readiness": readiness_score(gaps),
        "readiness_calculation": "Equal-weight average of min(current proficiency / required proficiency, 1) across configured role skills. This is a planning indicator, not a hiring or placement prediction.",
        "skills": gaps,
        "highest_priority": next((item["skill"] for item in gaps if item["gap"] > 0), None),
        "recommendations": [
            {
                "skill": item["skill"],
                "explanation": f"These resources introduce {item['skill']} at a {level_label(item['current']).lower()} level and provide a practical way to practice it.",
                "gap_closing_activity": f"Complete one practice exercise and record evidence of your approach to {item['skill']}.",
                "resources": learning_resources(
                    item["skill"],
                    item["current"],
                    profile.learning_language if profile else "English",
                    profile.learning_format if profile else "Mixed",
                ),
            }
            for item in gaps if item["gap"] > 0
        ],
        "next_recommended_action": (
            f"Start with {next((item['skill'] for item in gaps if item['gap'] > 0), role.name)}."
            if any(item["gap"] > 0 for item in gaps)
            else "Review one role skill and build project evidence to keep your profile current."
        ),
    }


def learning_task_payload(task: LearningTask):
    resources = json_list(task.resources)
    return {
        "id": task.id,
        "order": task.order,
        "phase": task.phase,
        "phase_name": task.phase_name,
        "skill": task.skill.name if task.skill else None,
        "title": task.title,
        "why": task.why,
        "explanation": task.explanation,
        "prerequisites": json_list(task.prerequisites),
        "estimated_minutes": task.estimated_minutes,
        "resources": resources,
        "practice": task.practice,
        "mini_project": task.mini_project,
        "status": task.status,
        "next_recommended_task": None,
    }


def ensure_learning_plan(db: Session, student: Student, profile: LearningProfile | None, refresh: bool = False):
    role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal)) if student.career_goal else None
    if role is None:
        return None
    active = db.scalar(
        select(LearningPlan).where(LearningPlan.student_id == student.id, LearningPlan.active.is_(True)).order_by(LearningPlan.id.desc())
    )
    if active and active.career_role_id == role.id and not refresh:
        return active

    previous_status = {}
    if active:
        previous_status = {
            (task.phase, task.skill.name.lower() if task.skill else "", task.title): task.status
            for task in active.tasks
        }
        active.active = False

    analysis = learning_analysis_data(db, student, profile)
    task_specs = generate_task_specs(
        role.name,
        analysis["skills"],
        profile.learning_language if profile else "English",
        profile.learning_format if profile else "Mixed",
    )
    plan = LearningPlan(student_id=student.id, career_role_id=role.id, active=True)
    db.add(plan)
    db.flush()
    for spec in task_specs:
        skill = skill_by_name(db, spec["skill"]) if spec["skill"] else None
        status_value = previous_status.get((spec["phase"], (spec["skill"] or "").lower(), spec["title"]), "Not Started")
        resources = [resource for resource in spec["resources"] if valid_resource_url(resource["url"])]
        plan.tasks.append(LearningTask(
            order=spec["order"],
            phase=spec["phase"],
            phase_name=spec["phase_name"],
            skill_id=skill.id if skill else None,
            title=spec["title"],
            why=spec["why"],
            explanation=spec["explanation"],
            prerequisites=json.dumps(spec["prerequisites"]),
            estimated_minutes=spec["estimated_minutes"],
            resources=json.dumps(resources),
            practice=spec["practice"],
            mini_project=spec["mini_project"],
            status=status_value,
        ))
    db.flush()
    return plan


def skill_by_name(db: Session, name: str) -> Skill | None:
    return db.scalar(select(Skill).where(Skill.name.ilike(name.strip())))


def skill_level(student: Student, skill_id: int) -> int:
    return next((item.proficiency for item in student.skills if item.skill_id == skill_id), 0)


def student_skill_payload(item: StudentSkill):
    return {"id": item.id, "skill_id": item.skill_id, "name": item.skill.name, "category": item.skill.category, "proficiency": item.proficiency, "verification_status": item.verification_status, "evidence": item.evidence}


@app.get("/api/health")
def health():
    return ok({"status": "healthy"})


@app.post("/api/auth/login")
def login(payload: Credentials, db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        fail("Email or password is incorrect", 401)
    return ok({"token": create_token(user), "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}})


@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterInput, db: Annotated[Session, Depends(get_db)]):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        fail("An account with this email already exists", 409)
    user = User(name=payload.name, email=email, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()
    if payload.role == "student":
        db.add(Student(user_id=user.id))
    elif payload.role == "industry":
        db.add(Industry(user_id=user.id, company_name=payload.name))
    else:
        db.add(Institution(user_id=user.id, institution_name=payload.name))
    db.commit()
    return ok({"token": create_token(user), "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}})


@app.get("/api/auth/me")
def me(user: Annotated[User, Depends(current_user)]):
    return ok({"id": user.id, "name": user.name, "email": user.email, "role": user.role})


@app.get("/api/student/profile")
def get_profile(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    return ok({"id": user.id, "name": user.name, "email": user.email, "college": student.college, "department": student.department, "year": student.year, "career_goal": student.career_goal, "bio": student.bio, "interests": student.interests})


@app.put("/api/student/profile")
def update_profile(payload: ProfileInput, user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    user.name = payload.name
    student.college, student.department, student.year = payload.college, payload.department, payload.year
    student.bio, student.interests = payload.bio, payload.interests
    db.commit()
    return get_profile(user, db)


def ensure_roadmap(db: Session, student: Student, role: CareerRole):
    roadmap = db.scalar(select(Roadmap).where(Roadmap.student_id == student.id))
    if roadmap:
        return roadmap
    roadmap = Roadmap(student_id=student.id, career_role_id=role.id)
    db.add(roadmap)
    db.flush()
    role_skills = sorted(role.role_skills, key=lambda rs: rs.required_level - skill_level(student, rs.skill_id), reverse=True)
    for week, role_skill in enumerate(role_skills[:3], 1):
        db.add(RoadmapTask(roadmap_id=roadmap.id, week=week, title=f"{role_skill.skill.name} learning sprint", type="LEARN", skill_id=role_skill.skill_id, description=f"Build practical {role_skill.skill.name} capability with a guided course and hands-on practice."))
    project = db.scalar(select(Project).where(Project.status == "OPEN"))
    db.add(RoadmapTask(roadmap_id=roadmap.id, week=4, title=project.title if project else "Complete an industry project", type="PROJECT", description="Apply your new skills to an industry-reviewed project."))
    db.flush()
    return roadmap


@app.get("/api/student/career-roles")
def career_roles(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(require_role("student"))]):
    return ok([{"id": role.id, "name": role.name, "description": role.description, "skills": [{"name": item.skill.name, "required_level": item.required_level} for item in role.role_skills]} for role in db.scalars(select(CareerRole).order_by(CareerRole.name))])


@app.put("/api/student/career")
def set_career(payload: CareerInput, user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    role = db.scalar(select(CareerRole).where(CareerRole.name.ilike(payload.career_goal.strip())))
    if role is None:
        fail("Select a career role from the available list", 404)
    student.career_goal = role.name
    roadmap = ensure_roadmap(db, student, role)
    db.commit()
    return ok({"career_goal": role.name, "roadmap_id": roadmap.id})


@app.get("/api/student/learning-profile")
def get_learning_profile(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    return ok(learning_profile_payload(student, learning_profile_for(db, student)))


@app.put("/api/student/learning-profile")
def update_learning_profile(
    payload: LearningProfileInput,
    user: Annotated[User, Depends(require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    student = student_for(db, user)
    profile = learning_profile_for(db, student)
    if profile is None:
        profile = LearningProfile(student_id=student.id)
        db.add(profile)
        db.flush()

    if payload.career_goal is not None:
        role = db.scalar(select(CareerRole).where(CareerRole.name.ilike(payload.career_goal.strip())))
        if payload.career_goal.strip() and role is None:
            fail("Select a career role from the available list", 404)
        student.career_goal = role.name if role else ""

    for field_name in (
        "programming_languages",
        "completed_courses",
        "completed_projects",
        "target_companies",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(profile, field_name, json.dumps(value))
    for field_name in (
        "github_url",
        "linkedin_url",
        "leetcode_url",
        "study_minutes_per_day",
        "learning_language",
        "learning_format",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(profile, field_name, value)

    if payload.current_skills is not None:
        submitted_names = set()
        existing = {item.skill_id: item for item in student.skills}
        for submitted in payload.current_skills:
            skill_name = submitted.skill_name.strip()
            normalized_name = skill_name.casefold()
            if normalized_name in submitted_names:
                fail("Each skill can only appear once in the profile", 422)
            submitted_names.add(normalized_name)
            skill = skill_by_name(db, skill_name)
            if skill is None:
                skill = Skill(name=skill_name, category="Student reported")
                db.add(skill)
                db.flush()
            student_skill = existing.get(skill.id)
            if student_skill is None:
                student_skill = StudentSkill(
                    student_id=student.id,
                    skill_id=skill.id,
                    proficiency=submitted.proficiency,
                    verification_status="IN PROGRESS",
                    evidence="Self-reported in learning profile",
                )
                db.add(student_skill)
                existing[skill.id] = student_skill
            else:
                if student_skill.verification_status == "VERIFIED" and student_skill.proficiency != submitted.proficiency:
                    fail(f"Verified proficiency for {skill.name} cannot be edited as self-reported data", 409)
                student_skill.proficiency = submitted.proficiency
                if student_skill.verification_status != "VERIFIED":
                    student_skill.verification_status = "IN PROGRESS"
                    student_skill.evidence = "Self-reported in learning profile"
    db.commit()
    db.refresh(student)
    return ok(learning_profile_payload(student, learning_profile_for(db, student)))


@app.get("/api/student/skill-gap-analysis")
def student_skill_gap_analysis(
    user: Annotated[User, Depends(require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    student = student_for(db, user)
    return ok(learning_analysis_data(db, student, learning_profile_for(db, student)))


def learning_roadmap_payload(db: Session, student: Student, profile: LearningProfile | None, plan: LearningPlan | None):
    analysis = learning_analysis_data(db, student, profile)
    plan_version = db.scalar(
        select(func.count(LearningPlan.id)).where(LearningPlan.student_id == student.id)
    ) or 0
    if plan is None:
        return {
            "career_goal": analysis["career_goal"],
            "plan_version": plan_version,
            "engine": "rule-based",
            "provisional": analysis["provisional"],
            "provisional_reasons": analysis["provisional_reasons"],
            "readiness": analysis["readiness"],
            "estimated_days": None,
            "study_minutes_per_day": profile.study_minutes_per_day if profile else None,
            "tasks": [],
            "progress": 0,
            "next_recommended_task": None,
        }
    tasks = [learning_task_payload(task) for task in plan.tasks]
    next_task = next((task for task in tasks if task["status"] != "Completed"), None)
    if next_task:
        next_task["next_recommended_task"] = True
    for task in tasks:
        task["next_recommended_task"] = task["id"] == next_task["id"] if next_task else False
    completed = sum(task["status"] == "Completed" for task in tasks)
    return {
        "career_goal": plan.career_role.name,
        "plan_version": plan_version,
        "engine": "rule-based",
        "provisional": analysis["provisional"],
        "provisional_reasons": analysis["provisional_reasons"],
        "readiness": analysis["readiness"],
        "estimated_days": estimate_study_days(
            [{"estimated_minutes": task["estimated_minutes"]} for task in tasks],
            profile.study_minutes_per_day if profile and profile.study_minutes_per_day else 0,
        ),
        "study_minutes_per_day": profile.study_minutes_per_day if profile else None,
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "progress": round(completed / len(tasks) * 100) if tasks else 0,
        "next_recommended_task": next_task["id"] if next_task else None,
        "tasks": tasks,
    }


@app.get("/api/student/learning-roadmap")
def get_learning_roadmap(
    user: Annotated[User, Depends(require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    student = student_for(db, user)
    profile = learning_profile_for(db, student)
    plan = ensure_learning_plan(db, student, profile)
    if plan is not None:
        db.commit()
    return ok(learning_roadmap_payload(db, student, profile, plan))


@app.post("/api/student/learning-roadmap/refresh")
def refresh_learning_roadmap(
    user: Annotated[User, Depends(require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    student = student_for(db, user)
    profile = learning_profile_for(db, student)
    plan = ensure_learning_plan(db, student, profile, refresh=True)
    if plan is None:
        return ok(learning_roadmap_payload(db, student, profile, None))
    db.commit()
    return ok(learning_roadmap_payload(db, student, profile, plan))


@app.patch("/api/student/learning-roadmap/tasks/{task_id}")
def update_learning_task_status(
    task_id: int,
    payload: LearningTaskStatusInput,
    user: Annotated[User, Depends(require_role("student"))],
    db: Annotated[Session, Depends(get_db)],
):
    student = student_for(db, user)
    task = db.scalar(
        select(LearningTask)
        .join(LearningPlan)
        .where(
            LearningTask.id == task_id,
            LearningPlan.student_id == student.id,
            LearningPlan.active.is_(True),
        )
    )
    if task is None:
        fail("Learning task not found", 404)
    task.status = payload.status
    db.commit()
    profile = learning_profile_for(db, student)
    plan = db.get(LearningPlan, task.plan_id)
    return ok(learning_roadmap_payload(db, student, profile, plan))


def gap_items(db: Session, student: Student):
    role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal))
    if role is None:
        return []
    output = []
    for requirement in role.role_skills:
        current = skill_level(student, requirement.skill_id)
        gap = max(requirement.required_level - current, 0)
        label = "Strong" if gap == 0 else "Low" if gap == 1 else "Medium" if gap == 2 else "High"
        output.append({"skill_id": requirement.skill_id, "skill": requirement.skill.name, "category": requirement.skill.category, "required": requirement.required_level, "current": current, "gap": gap, "priority": label, "priority_score": gap * 10 + requirement.required_level})
    return sorted(output, key=lambda item: (-item["priority_score"], item["skill"]))


@app.get("/api/skill-gap")
def get_skill_gap(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    gaps = gap_items(db, student)
    projects = db.scalars(select(Project).where(Project.status == "OPEN")).all()
    recommendations = []
    for item in [gap for gap in gaps if gap["gap"] > 0][:5]:
        course = db.scalar(select(Course).where(Course.skill_id == item["skill_id"]).order_by(Course.id))
        project = next((project for project in projects if item["skill"].lower() in project.required_skills.lower()), None)
        recommendations.append({"skill": item["skill"], "course": course.title if course else f"{item['skill']} Fundamentals", "practice": f"{item['skill']} applied challenge", "project": project.title if project else "Industry skill challenge", "assessment": f"{item['skill']} Skill Check"})
    return ok({"career_goal": student.career_goal, "skills": gaps, "highest_priority": gaps[0]["skill"] if gaps and gaps[0]["gap"] else None, "recommendations": recommendations})


QUESTIONS = [
    {"id": 1, "skill": "Python", "question": "Which Python structure stores key-value pairs?", "options": ["List", "Dictionary", "Tuple", "Set"], "answer": "Dictionary"},
    {"id": 2, "skill": "Python", "question": "What does len([2, 4, 6]) return?", "options": ["2", "3", "6", "12"], "answer": "3"},
    {"id": 3, "skill": "SQL", "question": "Which clause filters grouped rows?", "options": ["WHERE", "HAVING", "ORDER BY", "LIMIT"], "answer": "HAVING"},
    {"id": 4, "skill": "SQL", "question": "Which join returns every row from the left table?", "options": ["INNER JOIN", "LEFT JOIN", "CROSS JOIN", "SELF JOIN"], "answer": "LEFT JOIN"},
    {"id": 5, "skill": "Statistics", "question": "Which measure is least affected by extreme values?", "options": ["Mean", "Median", "Range", "Variance"], "answer": "Median"},
    {"id": 6, "skill": "Statistics", "question": "A correlation near zero suggests:", "options": ["Strong positive relation", "No linear relation", "Causation", "Identical distributions"], "answer": "No linear relation"},
    {"id": 7, "skill": "Power BI", "question": "What language is commonly used for Power BI measures?", "options": ["DAX", "CSS", "Bash", "YAML"], "answer": "DAX"},
    {"id": 8, "skill": "Data Visualization", "question": "Which chart best shows a trend over time?", "options": ["Line chart", "Pie chart", "Treemap", "Gauge"], "answer": "Line chart"},
    {"id": 9, "skill": "Excel", "question": "Which function counts cells matching a condition?", "options": ["SUM", "COUNTIF", "CONCAT", "ROUND"], "answer": "COUNTIF"},
    {"id": 10, "skill": "Problem Solving", "question": "What is the best first step for an unfamiliar problem?", "options": ["Guess an answer", "Break it into smaller parts", "Skip testing", "Add more tools"], "answer": "Break it into smaller parts"},
]


def ensure_assessment_bank(db: Session):
    assessment = db.scalar(select(Assessment).where(Assessment.student_id.is_(None), Assessment.title == "Industry Readiness Diagnostic"))
    if assessment is None:
        assessment = Assessment(title="Industry Readiness Diagnostic")
        db.add(assessment)
        db.flush()
    if not assessment.questions:
        for item in QUESTIONS:
            skill = skill_by_name(db, item["skill"])
            if skill is None:
                skill = Skill(name=item["skill"], category="Technical")
                db.add(skill)
                db.flush()
            assessment.questions.append(AssessmentQuestion(question=item["question"], options=json.dumps(item["options"]), correct_answer=item["answer"], skill_id=skill.id, difficulty="Intermediate"))
        db.flush()
    return assessment


@app.get("/api/assessment")
def get_assessment(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    assessment = ensure_assessment_bank(db)
    questions = [{"id": question.id, "skill": question.skill.name, "question": question.question, "options": json.loads(question.options)} for question in assessment.questions]
    db.commit()
    return ok({"title": assessment.title, "questions": questions})


@app.post("/api/assessment/submit")
def submit_assessment(payload: AnswersInput, user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    bank = ensure_assessment_bank(db)
    questions = list(bank.questions)
    answer_map = {item.question_id: item.answer for item in payload.answers}
    if len(answer_map) != len(questions) or set(answer_map) != {question.id for question in questions}:
        fail("Submit an answer for every assessment question exactly once")
    assessment = Assessment(student_id=student.id, title=bank.title)
    db.add(assessment)
    db.flush()
    grouped = {}
    for question in questions:
        correct = answer_map.get(question.id) == question.correct_answer
        grouped.setdefault(question.skill.name, []).append(correct)
    correct_count = sum(answer_map.get(question.id) == question.correct_answer for question in questions)
    for name, results in grouped.items():
        skill = skill_by_name(db, name)
        if skill is None:
            continue
        score = sum(results) / len(results)
        proficiency = max(1, min(5, round(score * 4) + 1))
        record = db.scalar(select(StudentSkill).where(StudentSkill.student_id == student.id, StudentSkill.skill_id == skill.id))
        if record is None:
            record = StudentSkill(student_id=student.id, skill_id=skill.id, proficiency=proficiency)
            db.add(record)
        else:
            record.proficiency = proficiency
        db.add(AssessmentResult(assessment_id=assessment.id, skill_id=skill.id, score=score * 100, proficiency=proficiency))
    assessment.score = correct_count / len(questions) * 100
    assessment.completed_at = utc_now()
    if student.career_goal:
        role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal))
        if role:
            ensure_roadmap(db, student, role)
    db.commit()
    return ok({"assessment_id": assessment.id, "score": assessment.score, "correct": correct_count, "total": len(questions), "results": [{"skill": name, "proficiency": max(1, min(5, round(sum(vals) / len(vals) * 4) + 1))} for name, vals in grouped.items()]})


def readiness(db: Session, student: Student) -> int:
    gaps = gap_items(db, student)
    if not gaps:
        levels = [item.proficiency for item in student.skills]
        return round(sum(levels) / (5 * len(levels)) * 100) if levels else 0
    return round(sum(item["current"] for item in gaps) / (5 * len(gaps)) * 100)


def roadmap_payload(db: Session, student: Student):
    role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal))
    if role is None:
        return {"career_goal": "", "tasks": [], "progress": 0}
    roadmap = ensure_roadmap(db, student, role)
    tasks = [{"id": task.id, "week": task.week, "title": task.title, "type": task.type, "skill": task.skill.name if task.skill else "", "description": task.description, "completed": task.completed} for task in roadmap.tasks]
    return {"career_goal": roadmap.career_role.name, "tasks": tasks, "progress": round(sum(task["completed"] for task in tasks) / len(tasks) * 100) if tasks else 0}


@app.get("/api/roadmap")
def get_roadmap(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    return ok(roadmap_payload(db, student))


@app.post("/api/roadmap/tasks/{task_id}/complete")
def complete_task(task_id: int, user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    task = db.get(RoadmapTask, task_id)
    if task is None or task.roadmap.student_id != student.id:
        fail("Roadmap task not found", 404)
    task.completed = not task.completed
    db.commit()
    return ok(roadmap_payload(db, student))


@app.get("/api/student/skills")
def student_skills(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    return ok([student_skill_payload(item) for item in student.skills])


def project_payload(project: Project, student: Student | None = None):
    applications = project.applications
    application = next((item for item in applications if student and item.student_id == student.id), None)
    return {"id": project.id, "title": project.title, "description": project.description, "domain": project.domain, "difficulty": project.difficulty, "required_skills": [item.strip() for item in project.required_skills.split(",") if item.strip()], "expected_outcome": project.expected_outcome, "evaluation_criteria": project.evaluation_criteria, "deadline": project.deadline, "status": project.status, "company": project.industry.company_name, "applications": len(applications), "application_status": application.status if application else None, "submission_status": "SUBMITTED" if application and application.submission else None}


@app.get("/api/projects")
def list_projects(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]):
    student = db.scalar(select(Student).where(Student.user_id == user.id)) if user.role == "student" else None
    projects = db.scalars(select(Project).where(Project.status == "OPEN").order_by(Project.id)).all()
    return ok([project_payload(project, student) for project in projects])


@app.get("/api/projects/{project_id}")
def project_detail(project_id: int, user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]):
    project = db.get(Project, project_id)
    if project is None:
        fail("Project not found", 404)
    student = db.scalar(select(Student).where(Student.user_id == user.id)) if user.role == "student" else None
    from .industry_features import _project_payload

    return ok(_project_payload(db, project, student))


@app.post("/api/projects", status_code=201)
def create_project(payload: ProjectInput, user: Annotated[User, Depends(require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = db.scalar(select(Industry).where(Industry.user_id == user.id))
    if industry is None:
        fail("Industry profile not found", 404)
    project = Project(industry_id=industry.id, title=payload.title, description=payload.description, domain=payload.domain, difficulty=payload.difficulty, required_skills=", ".join(dict.fromkeys(payload.required_skills)), expected_outcome=payload.expected_outcome, evaluation_criteria=payload.evaluation_criteria, deadline=payload.deadline)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ok(project_payload(project))


@app.post("/api/projects/{project_id}/apply", status_code=201)
def apply_project(project_id: int, user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    project = db.get(Project, project_id)
    if project is None or project.status != "OPEN":
        fail("Project is not available", 404)
    if db.scalar(select(ProjectApplication).where(ProjectApplication.project_id == project_id, ProjectApplication.student_id == student.id)):
        fail("You have already applied to this project", 409)
    application = ProjectApplication(project_id=project_id, student_id=student.id)
    db.add(application)
    db.commit()
    return ok({"application_id": application.id, "status": application.status})


@app.post("/api/projects/{project_id}/submit", status_code=201)
def submit_project(project_id: int, payload: SubmissionInput, user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    application = db.scalar(select(ProjectApplication).where(ProjectApplication.project_id == project_id, ProjectApplication.student_id == student.id))
    if application is None:
        fail("Apply to this project before submitting", 409)
    if application.submission:
        fail("A submission already exists for this project", 409)
    if payload.github_url and not re.match(r"^https?://", payload.github_url):
        fail("GitHub URL must start with http:// or https://")
    submission = ProjectSubmission(application_id=application.id, description=payload.description, github_url=payload.github_url, evidence=payload.evidence)
    application.status = "SUBMITTED"
    db.add(submission)
    db.commit()
    return ok({"submission_id": submission.id, "status": "SUBMITTED"})


@app.get("/api/mentor/submissions")
def mentor_submissions(user: Annotated[User, Depends(require_role("mentor"))], db: Annotated[Session, Depends(get_db)]):
    mentor = db.scalar(select(Mentor).where(Mentor.user_id == user.id))
    student_ids = mentor_accessible_student_ids(db, mentor) if mentor else set()
    submissions = db.scalars(
        select(ProjectSubmission)
        .join(ProjectApplication)
        .where(ProjectApplication.student_id.in_(student_ids))
        .order_by(ProjectSubmission.submitted_at.desc())
    ).all() if student_ids else []
    return ok([{"id": item.id, "project_id": item.application.project_id, "project": item.application.project.title, "student": item.application.student.user.name, "student_id": item.application.student_id, "description": item.description, "github_url": item.github_url, "evidence": item.evidence, "submitted_at": item.submitted_at.isoformat(), "evaluated": item.evaluation is not None, "feedback": item.evaluation.feedback if item.evaluation else ""} for item in submissions])


@app.get("/api/student/mentor")
def student_assigned_mentor(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    mentorship = db.scalar(select(InstitutionMentorship).where(
        InstitutionMentorship.student_id == student.id,
        InstitutionMentorship.status.in_(("ASSIGNED", "IN_PROGRESS")),
    ))
    if mentorship is None or mentorship.mentor is None:
        return ok(None)
    membership = institution_mentor_membership_for(
        db, db.get(Institution, mentorship.institution_id), mentorship.mentor_id
    )
    if membership is None:
        return ok(None)
    return ok({
        "name": mentorship.mentor.user.name,
        "expertise": mentorship.mentor.expertise,
        "status": mentorship.status,
    })


@app.post("/api/projects/submissions/{submission_id}/evaluate")
def evaluate_submission(submission_id: int, payload: EvaluationInput, user: Annotated[User, Depends(require_role("mentor"))], db: Annotated[Session, Depends(get_db)]):
    mentor = db.scalar(select(Mentor).where(Mentor.user_id == user.id))
    submission = db.get(ProjectSubmission, submission_id)
    if mentor is None or submission is None:
        fail("Submission or mentor profile not found", 404)
    if submission.application.student_id not in mentor_accessible_student_ids(db, mentor):
        fail("This student is not assigned to you through an active institution", status.HTTP_403_FORBIDDEN)
    if submission.evaluation:
        fail("This submission has already been evaluated", 409)
    scores = [payload.technical_quality, payload.problem_solving, payload.code_quality, payload.communication, payload.innovation]
    evaluation = ProjectEvaluation(submission_id=submission.id, mentor_id=mentor.id, technical_quality=scores[0], problem_solving=scores[1], code_quality=scores[2], communication=scores[3], innovation=scores[4], overall_score=sum(scores) / len(scores) * 20, feedback=payload.feedback)
    db.add(evaluation)
    application = submission.application
    application.status = "EVALUATED"
    project = application.project
    student = application.student
    verified_skills = []
    if evaluation.overall_score >= 70:
        for name in project.required_skills.split(","):
            skill = skill_by_name(db, name)
            if skill is None:
                continue
            record = db.scalar(select(StudentSkill).where(StudentSkill.student_id == student.id, StudentSkill.skill_id == skill.id))
            if record is None:
                record = StudentSkill(student_id=student.id, skill_id=skill.id, proficiency=1)
                db.add(record)
            record.proficiency = max(record.proficiency, min(5, round(evaluation.overall_score / 20)))
            record.verification_status = "VERIFIED"
            record.evidence = f"Mentor-verified project: {project.title}"
            verified_skills.append(skill.name)
    db.commit()
    return ok({"overall_score": evaluation.overall_score, "verified_skills": verified_skills})


@app.get("/api/student/passport")
def skill_passport(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    evaluations = db.scalars(select(ProjectEvaluation).join(ProjectSubmission).join(ProjectApplication).where(ProjectApplication.student_id == student.id)).all()
    projects = db.scalars(select(ProjectApplication).where(ProjectApplication.student_id == student.id)).all()
    assessments = db.scalars(select(Assessment).where(Assessment.student_id == student.id).order_by(Assessment.completed_at.desc())).all()
    certifications = db.scalars(select(Certification).where(Certification.student_id == student.id)).all()
    return ok({"student": {"name": user.name, "email": user.email, "college": student.college, "department": student.department, "career_goal": student.career_goal}, "readiness": readiness(db, student), "skills": [student_skill_payload(item) for item in student.skills], "projects": [{"title": item.project.title, "status": item.status, "score": item.submission.evaluation.overall_score if item.submission and item.submission.evaluation else None} for item in projects], "assessments": [{"title": item.title, "score": item.score, "completed_at": item.completed_at.isoformat() if item.completed_at else None} for item in assessments], "certifications": [{"name": item.name, "issuer": item.issuer} for item in certifications], "evaluations": len(evaluations)})


@app.get("/api/student/dashboard")
def student_dashboard(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    gaps = gap_items(db, student)
    tasks = roadmap_payload(db, student)["tasks"]
    matches = opportunity_matches_data(db, student)
    applications = db.scalars(select(ProjectApplication).where(ProjectApplication.student_id == student.id)).all()
    completed_assessments = db.query(Assessment).filter(Assessment.student_id == student.id, Assessment.completed_at.is_not(None)).count()
    return ok({"name": user.name, "career_goal": student.career_goal, "readiness": readiness(db, student), "verified_skills": sum(item.verification_status == "VERIFIED" for item in student.skills), "skill_count": len(student.skills), "open_tasks": sum(not task["completed"] for task in tasks), "roadmap_progress": round(sum(task["completed"] for task in tasks) / len(tasks) * 100) if tasks else 0, "project_applications": len(applications), "opportunity_matches": len(matches), "assessment_count": completed_assessments, "top_gaps": gaps[:4]})


@app.get("/api/student/institution-courses")
def student_institution_courses(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    records = db.scalars(
        select(InstitutionCourseEnrollment)
        .where(InstitutionCourseEnrollment.student_id == student.id)
        .order_by(InstitutionCourseEnrollment.assigned_at.desc())
    ).all()
    return ok([{
        "course_name": item.course.title,
        "skill": item.course.skill.name,
        "status": item.status,
        "assigned_at": item.assigned_at.isoformat(),
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "score": item.score,
    } for item in records])


@app.get("/api/student/progress")
def student_progress(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    tasks = roadmap_payload(db, student)["tasks"]
    applications = db.scalars(select(ProjectApplication).where(ProjectApplication.student_id == student.id)).all()
    assessments = db.query(Assessment).filter(Assessment.student_id == student.id, Assessment.completed_at.is_not(None)).count()
    return ok({"readiness": readiness(db, student), "assessment_completion": 100 if assessments else 0, "roadmap_completion": round(sum(task["completed"] for task in tasks) / len(tasks) * 100) if tasks else 0, "project_completion": round(sum(item.status in ("SUBMITTED", "EVALUATED") for item in applications) / len(applications) * 100) if applications else 0, "verified_skills": sum(item.verification_status == "VERIFIED" for item in student.skills), "skills": [{"skill": item.skill.name, "proficiency": item.proficiency} for item in student.skills]})


def opportunity_matches_data(db: Session, student: Student):
    matches = []
    for opportunity in db.scalars(select(Opportunity)).all():
        required = [name.strip() for name in opportunity.required_skills.split(",") if name.strip()]
        found, missing, score_total = [], [], 0
        for name in required:
            skill = skill_by_name(db, name)
            level = skill_level(student, skill.id) if skill else 0
            if level >= 2:
                found.append(name)
            else:
                missing.append(name)
            score_total += min(level / 4, 1) * 100 if skill else 0
        score = round(score_total / len(required)) if required else 0
        goal_bonus = 8 if student.career_goal and student.career_goal.lower() in (opportunity.title + " " + opportunity.description).lower() else 0
        matches.append({"id": opportunity.id, "title": opportunity.title, "type": opportunity.type, "description": opportunity.description, "company": opportunity.industry.company_name, "location": opportunity.location, "eligibility": opportunity.eligibility, "required_skills": required, "matched_skills": found, "missing_skills": missing, "match_score": min(100, score + goal_bonus)})
    return sorted(matches, key=lambda item: item["match_score"], reverse=True)


@app.get("/api/opportunities/matches")
def opportunity_matches(user: Annotated[User, Depends(require_role("student"))], db: Annotated[Session, Depends(get_db)]):
    student = student_for(db, user)
    matches = opportunity_matches_data(db, student)
    for match in matches:
        stored = db.scalar(select(OpportunityMatch).where(OpportunityMatch.student_id == student.id, OpportunityMatch.opportunity_id == match["id"]))
        if stored is None:
            stored = OpportunityMatch(student_id=student.id, opportunity_id=match["id"])
            db.add(stored)
        stored.match_score = match["match_score"]
        stored.matched_skills = ", ".join(match["matched_skills"])
        stored.missing_skills = ", ".join(match["missing_skills"])
    db.commit()
    return ok(matches)


@app.post("/api/industry/skills/extract")
def extract_skills(payload: ExtractInput, user: Annotated[User, Depends(require_role("industry"))]):
    dictionary = {
        "Python": (["python", "python programming"], "Technical Skills"),
        "SQL": (["sql", "structured query language"], "Technical Skills"),
        "Power BI": (["power bi", "powerbi"], "Tools"),
        "Excel": (["excel", "microsoft excel", "advanced excel"], "Tools"),
        "Statistics": (["statistics", "statistical analysis", "statistical"], "Technical Skills"),
        "Data Visualization": (["data visualization", "data visualisation", "visualization"], "Technical Skills"),
        "Machine Learning": (["machine learning", "ml"], "Technical Skills"),
        "Cloud": (["cloud", "aws", "azure", "gcp"], "Tools"),
        "Cybersecurity": (["cybersecurity", "security analyst"], "Technical Skills"),
        "Communication": (["communication", "presentation"], "Soft Skills"),
        "Problem Solving": (["problem solving", "problem-solving"], "Soft Skills"),
        "Teamwork": (["teamwork", "collaboration"], "Soft Skills"),
        "JavaScript": (["javascript", "typescript"], "Technical Skills"),
        "React": (["react", "react.js"], "Technical Skills"),
    }
    text = payload.description.lower()
    found = [{"name": name, "category": category} for name, (aliases, category) in dictionary.items() if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text) for alias in aliases)]
    return ok({"skills": found, "groups": {category: [item["name"] for item in found if item["category"] == category] for category in ("Technical Skills", "Tools", "Soft Skills")}, "engine": "local-dictionary-nlp"})


@app.post("/api/industry/requirements")
def create_requirement(payload: RequirementInput, user: Annotated[User, Depends(require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    role = db.scalar(select(CareerRole).where(CareerRole.name.ilike(payload.role_name.strip())))
    skill = skill_by_name(db, payload.skill_name)
    if role is None or skill is None:
        fail("Career role or skill not found", 404)
    requirement = db.scalar(select(RoleSkill).where(RoleSkill.role_id == role.id, RoleSkill.skill_id == skill.id))
    if requirement:
        requirement.required_level = payload.required_level
    else:
        db.add(RoleSkill(role_id=role.id, skill_id=skill.id, required_level=payload.required_level))
    db.commit()
    return ok({"role": role.name, "skill": skill.name, "required_level": payload.required_level})


@app.get("/api/industry/dashboard")
def industry_dashboard(user: Annotated[User, Depends(require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    industry = db.scalar(select(Industry).where(Industry.user_id == user.id))
    projects = db.scalars(select(Project).where(Project.industry_id == industry.id)).all()
    demand = {}
    for project in projects:
        for name in project.required_skills.split(","):
            if name.strip():
                demand[name.strip()] = demand.get(name.strip(), 0) + 1
    return ok({"company": industry.company_name, "project_count": len(projects), "application_count": sum(len(p.applications) for p in projects), "open_projects": sum(p.status == "OPEN" for p in projects), "top_skills": [{"skill": k, "demand": v} for k, v in sorted(demand.items(), key=lambda pair: pair[1], reverse=True)[:6]], "projects": [project_payload(p) for p in projects]})


@app.get("/api/industry/talent")
def industry_talent(user: Annotated[User, Depends(require_role("industry"))], db: Annotated[Session, Depends(get_db)]):
    students = db.scalars(select(Student)).all()
    return ok([{"name": student.user.name, "college": student.college, "career_goal": student.career_goal, "readiness": readiness(db, student), "skills": [item.skill.name for item in student.skills]} for student in students])


def institution_for(db: Session, user: User) -> Institution:
    institution = db.scalar(select(Institution).where(Institution.user_id == user.id))
    if institution is None:
        fail("Institution profile not found", status.HTTP_404_NOT_FOUND)
    return institution


def institution_students(db: Session, institution: Institution) -> list[Student]:
    return db.scalars(
        select(Student)
        .where(func.lower(func.trim(Student.college)) == institution.institution_name.strip().lower())
        .order_by(Student.department, Student.year, Student.id)
    ).all()


def institution_mentor_memberships(db: Session, institution: Institution, active_only: bool = False) -> list[InstitutionMentorMembership]:
    query = select(InstitutionMentorMembership).where(
        InstitutionMentorMembership.institution_id == institution.id
    )
    if active_only:
        query = query.where(InstitutionMentorMembership.active.is_(True))
    return db.scalars(query.join(Mentor).join(User).order_by(User.name)).all()


def institution_mentor_payload(db: Session, institution: Institution, membership: InstitutionMentorMembership) -> dict:
    assignments = db.scalars(select(InstitutionMentorship).where(
        InstitutionMentorship.institution_id == institution.id,
        InstitutionMentorship.mentor_id == membership.mentor_id,
        InstitutionMentorship.status != "COMPLETED",
    )).all()
    eligible_students = {student.id: student for student in institution_students(db, institution)}
    assigned_students = []
    for assignment in assignments:
        student = eligible_students.get(assignment.student_id)
        if student is not None:
            assigned_students.append({
                "id": student.id,
                "name": student.user.name,
                "career_goal": student.career_goal,
                "department": student.department,
                "year": student.year,
                "status": assignment.status,
            })
    mentor = membership.mentor
    return {
        "id": membership.id,
        "mentor_id": mentor.id,
        "name": mentor.user.name,
        "email": mentor.user.email,
        "expertise": membership.expertise or mentor.expertise,
        "skills": [skill.strip() for skill in (membership.expertise or mentor.expertise).split(",") if skill.strip()],
        "experience": membership.experience if membership.expertise else mentor.experience,
        "company": mentor.company,
        "availability": membership.availability,
        "active": membership.active,
        "assigned_student_count": len(assigned_students),
        "assigned_students": assigned_students,
    }


def institution_mentor_membership_for(db: Session, institution: Institution, mentor_id: int, active_only: bool = True):
    query = select(InstitutionMentorMembership).where(
        InstitutionMentorMembership.institution_id == institution.id,
        InstitutionMentorMembership.mentor_id == mentor_id,
    )
    if active_only:
        query = query.where(InstitutionMentorMembership.active.is_(True))
    return db.scalar(query)


def mentor_accessible_student_ids(db: Session, mentor: Mentor) -> set[int]:
    memberships = db.scalars(
        select(InstitutionMentorMembership).where(
            InstitutionMentorMembership.mentor_id == mentor.id,
            InstitutionMentorMembership.active.is_(True),
        )
    ).all()
    student_ids: set[int] = set()
    for membership in memberships:
        institution = db.get(Institution, membership.institution_id)
        if institution is None:
            continue
        for assignment in db.scalars(select(InstitutionMentorship.student_id).where(
            InstitutionMentorship.institution_id == institution.id,
            InstitutionMentorship.mentor_id == mentor.id,
            InstitutionMentorship.status.in_(("ASSIGNED", "IN_PROGRESS")),
        )).all():
            student = db.get(Student, assignment)
            if student is not None and student.college.strip().lower() == institution.institution_name.strip().lower():
                student_ids.add(student.id)
    return student_ids


def institution_student_summary(db: Session, institution: Institution, student: Student) -> dict:
    from .industry_features import JobApplication

    enrollments = db.scalars(
        select(InstitutionCourseEnrollment).where(
            InstitutionCourseEnrollment.institution_id == institution.id,
            InstitutionCourseEnrollment.student_id == student.id,
        )
    ).all()
    completed = sum(item.status == "COMPLETED" for item in enrollments)
    in_progress = sum(item.status == "IN_PROGRESS" for item in enrollments)
    pending = sum(item.status == "PENDING" for item in enrollments)
    role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal)) if student.career_goal else None
    results = db.scalars(
        select(AssessmentResult)
        .join(Assessment)
        .where(Assessment.student_id == student.id, Assessment.completed_at.is_not(None))
        .order_by(Assessment.completed_at.desc(), Assessment.id.desc())
    ).all()
    assessed = {}
    for result in results:
        assessed.setdefault(result.skill_id, {
            "skill_id": result.skill_id,
            "skill": result.skill.name,
            "proficiency": result.proficiency,
            "score": result.score,
            "assessed_at": result.assessment.completed_at.isoformat(),
        })
    gaps = []
    if role is not None:
        for requirement in role.role_skills:
            current = assessed.get(requirement.skill_id)
            gaps.append({
                "skill": requirement.skill.name,
                "required": requirement.required_level,
                "current": current["proficiency"] if current else None,
                "status": "INSUFFICIENT_EVIDENCE" if current is None else (
                    "MEETS_REQUIREMENT" if current["proficiency"] >= requirement.required_level else "NEEDS_IMPROVEMENT"
                ),
                "recommended_courses": [
                    {"id": course.id, "title": course.title}
                    for course in db.scalars(
                        select(Course).where(Course.skill_id == requirement.skill_id).order_by(Course.id).limit(3)
                    ).all()
                ],
            })
    completed_assessments = db.scalar(
        select(func.count(Assessment.id)).where(
            Assessment.student_id == student.id, Assessment.completed_at.is_not(None)
        )
    ) or 0
    last_assessment = db.scalar(
        select(Assessment.completed_at)
        .where(Assessment.student_id == student.id, Assessment.completed_at.is_not(None))
        .order_by(Assessment.completed_at.desc(), Assessment.id.desc())
        .limit(1)
    )
    assessed_gaps = [item for item in gaps if item["status"] == "NEEDS_IMPROVEMENT"]
    missing_evidence = [item for item in gaps if item["status"] == "INSUFFICIENT_EVIDENCE"]
    if not completed_assessments or (role is not None and missing_evidence):
        gap_status = "ASSESSMENT_PENDING"
    elif any(item["required"] - item["current"] >= 2 for item in assessed_gaps):
        gap_status = "SIGNIFICANT_GAPS"
    elif assessed_gaps:
        gap_status = "MINOR_GAPS"
    elif role is not None:
        gap_status = "SKILLS_ALIGNED"
    else:
        gap_status = "ASSESSMENT_PENDING"
    mentorship = db.scalar(
        select(InstitutionMentorship).where(
            InstitutionMentorship.institution_id == institution.id,
            InstitutionMentorship.student_id == student.id,
        )
    )
    needs_mentorship = (mentorship is None or mentorship.status != "COMPLETED") and (gap_status == "SIGNIFICANT_GAPS" or any(
        item.status != "COMPLETED" for item in enrollments
    ))
    if gap_status == "SIGNIFICANT_GAPS":
        mentorship_reason = "Significant assessed skill gaps (proficiency gap of at least 2 levels on a 1–5 scale)."
    elif any(item.status != "COMPLETED" for item in enrollments):
        mentorship_reason = "Assigned course work is incomplete."
    else:
        mentorship_reason = ""
    profile = db.scalar(select(LearningProfile).where(LearningProfile.student_id == student.id))
    return {
        "id": student.id,
        "name": student.user.name,
        "email": student.user.email,
        "department": student.department,
        "year": student.year,
        "career_goal": student.career_goal,
        "assigned_courses": len(enrollments),
        "assigned_course_ids": [item.course_id for item in enrollments],
        "completed_courses": completed,
        "courses_in_progress": in_progress,
        "pending_courses": pending,
        "course_completion_percent": round(completed * 100 / len(enrollments), 1) if enrollments else None,
        "course_data_available": bool(enrollments),
        "assessed_skills": list(assessed.values()),
        "skill_gaps": gaps,
        "skill_gap_status": gap_status,
        "last_assessment_at": last_assessment.isoformat() if last_assessment else None,
        "linkedin_url": profile.linkedin_url if profile else "",
        "github_url": profile.github_url if profile else "",
        "mentorship_status": mentorship.status if mentorship else "NOT_ASSIGNED",
        "mentor_id": mentorship.mentor_id if mentorship else None,
        "mentor_name": mentorship.mentor.user.name if mentorship and mentorship.mentor else None,
        "mentorship_reason": (mentorship.reason or mentorship_reason) if mentorship else mentorship_reason,
        "needs_mentorship": needs_mentorship,
        "mentorship_notes": mentorship.notes if mentorship else "",
        "follow_up_date": mentorship.follow_up_date.isoformat() if mentorship and mentorship.follow_up_date else None,
    }


def institution_dashboard_payload(db: Session, institution: Institution) -> dict:
    students = institution_students(db, institution)
    summaries = [institution_student_summary(db, institution, student) for student in students]
    total = len(summaries)
    gap_counts = {}
    industry_demand = {}
    readiness_scores = [readiness(db, student) for student in students]
    for student, summary in zip(students, summaries):
        role = db.scalar(select(CareerRole).where(CareerRole.name == student.career_goal)) if student.career_goal else None
        if role is not None:
            for requirement in role.role_skills:
                industry_demand[requirement.skill.name] = industry_demand.get(requirement.skill.name, 0) + requirement.required_level
        for gap in summary["skill_gaps"]:
            if gap["status"] == "NEEDS_IMPROVEMENT":
                gap_counts[gap["skill"]] = gap_counts.get(gap["skill"], 0) + 1
    enrollments = db.scalars(
        select(InstitutionCourseEnrollment).where(InstitutionCourseEnrollment.institution_id == institution.id)
    ).all()
    student_ids = [student.id for student in students]
    project_participation = db.scalar(
        select(func.count(ProjectApplication.id)).where(ProjectApplication.student_id.in_(student_ids))
    ) if student_ids else 0
    assessment_completion = sum(bool(db.scalar(
        select(Assessment.id).where(
            Assessment.student_id == student.id, Assessment.completed_at.is_not(None)
        ).limit(1)
    )) for student in students)
    department_totals = {}
    for summary in summaries:
        department = summary["department"] or "Not specified"
        aggregate = department_totals.setdefault(department, {"department": department, "students": 0, "assigned": 0, "completed": 0})
        aggregate["students"] += 1
        aggregate["assigned"] += summary["assigned_courses"]
        aggregate["completed"] += summary["completed_courses"]
    assessment_history = {}
    if student_ids:
        for assessment in db.scalars(select(Assessment).where(
            Assessment.student_id.in_(student_ids), Assessment.completed_at.is_not(None)
        ).order_by(Assessment.completed_at)).all():
            month = assessment.completed_at.strftime("%Y-%m")
            aggregate = assessment_history.setdefault(month, {"month": month, "assessments": 0, "score_total": 0.0})
            aggregate["assessments"] += 1
            aggregate["score_total"] += assessment.score or 0
    return {
        "institution_name": institution.institution_name,
        "total_students": total,
        "students_completed_all_courses": sum(item["assigned_courses"] > 0 and item["completed_courses"] == item["assigned_courses"] for item in summaries),
        "students_learning": sum(item["courses_in_progress"] > 0 for item in summaries),
        "students_with_pending_courses": sum(item["pending_courses"] > 0 for item in summaries),
        "students_with_skill_gaps": sum(item["skill_gap_status"] in {"SIGNIFICANT_GAPS", "MINOR_GAPS"} for item in summaries),
        "students_requiring_mentorship": sum(item["needs_mentorship"] for item in summaries),
        "course_catalog": [
            {"id": course.id, "title": course.title, "skill": course.skill.name}
            for course in db.scalars(select(Course).order_by(Course.title)).all()
        ],
        "mentors": [
            {"id": membership.mentor.id, "name": membership.mentor.user.name, "expertise": membership.mentor.expertise}
            for membership in institution_mentor_memberships(db, institution, active_only=True)
        ],
        "course_status_counts": {
            "completed": sum(item.status == "COMPLETED" for item in enrollments),
            "in_progress": sum(item.status == "IN_PROGRESS" for item in enrollments),
            "pending": sum(item.status == "PENDING" for item in enrollments),
        },
        "department_progress": [{
            **aggregate,
            "completion_percent": round(aggregate["completed"] * 100 / aggregate["assigned"], 1) if aggregate["assigned"] else None,
        } for aggregate in sorted(department_totals.values(), key=lambda item: item["department"].lower())],
        "assessment_progress_over_time": [{
            "month": aggregate["month"],
            "assessments": aggregate["assessments"],
            "average_score": round(aggregate["score_total"] / aggregate["assessments"], 1),
        } for aggregate in assessment_history.values()],
        "common_skill_gaps": [
            {"skill": skill, "students": count}
            for skill, count in sorted(gap_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
        ],
        "average_readiness": round(sum(readiness_scores) / total) if total else 0,
        "assessment_completion": round(assessment_completion * 100 / total) if total else 0,
        "top_skill_gaps": [
            {"skill": skill, "students": count}
            for skill, count in sorted(gap_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
        ],
        "industry_demand": [
            {"skill": skill, "demand": count}
            for skill, count in sorted(industry_demand.items(), key=lambda item: (-item[1], item[0]))[:8]
        ],
        "project_participation": project_participation or 0,
        "verified_skills": sum(item.verification_status == "VERIFIED" for student in students for item in student.skills),
        "readiness_distribution": [
            {"student": student.user.name, "readiness": readiness(db, student)}
            for student in students
        ],
        "students": summaries,
    }


@app.get("/api/institution/analytics")
@app.get("/api/institution/dashboard")
def institution_analytics(user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    return ok(institution_dashboard_payload(db, institution))


@app.get("/api/institution/students/{student_id}")
def institution_student_detail(student_id: int, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    student = db.get(Student, student_id)
    if student is None or student not in institution_students(db, institution):
        fail("Student not found in this institution", status.HTTP_404_NOT_FOUND)
    from .industry_features import JobApplication, JobVacancy

    summary = institution_student_summary(db, institution, student)
    enrollments = db.scalars(
        select(InstitutionCourseEnrollment)
        .where(
            InstitutionCourseEnrollment.institution_id == institution.id,
            InstitutionCourseEnrollment.student_id == student.id,
        )
        .order_by(InstitutionCourseEnrollment.assigned_at.desc())
    ).all()
    roadmap = db.scalar(select(Roadmap).where(Roadmap.student_id == student.id))
    learning_plans = db.scalars(
        select(LearningPlan).where(LearningPlan.student_id == student.id).order_by(LearningPlan.created_at.desc())
    ).all()
    projects = db.scalars(select(ProjectApplication).where(ProjectApplication.student_id == student.id)).all()
    submissions = db.scalars(
        select(ProjectSubmission).join(ProjectApplication).where(ProjectApplication.student_id == student.id)
    ).all()
    job_applications = db.execute(
        select(JobApplication, JobVacancy)
        .join(JobVacancy, JobVacancy.id == JobApplication.vacancy_id)
        .where(JobApplication.student_id == student.id)
        .order_by(JobApplication.applied_at.desc())
    ).all()
    mentorship_history = db.scalars(
        select(InstitutionMentorshipHistory)
        .where(
            InstitutionMentorshipHistory.institution_id == institution.id,
            InstitutionMentorshipHistory.student_id == student.id,
        )
        .order_by(InstitutionMentorshipHistory.created_at.desc(), InstitutionMentorshipHistory.id.desc())
    ).all()
    return ok({
        **summary,
        "mentors": [
            {"id": membership.mentor.id, "name": membership.mentor.user.name, "expertise": membership.mentor.expertise}
            for membership in institution_mentor_memberships(db, institution, active_only=True)
        ],
        "course_records": [{
            "id": item.id,
            "course_id": item.course_id,
            "course_name": item.course.title,
            "status": item.status,
            "assigned_at": item.assigned_at.isoformat(),
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "score": item.score,
        } for item in enrollments],
        "roadmap": [{
            "title": task.title,
            "status": "COMPLETED" if task.completed else "PENDING",
            "skill": task.skill.name if task.skill else None,
        } for task in (roadmap.tasks if roadmap else [])] + [{
            "title": task.title,
            "status": task.status.upper().replace(" ", "_"),
            "skill": task.skill.name if task.skill else None,
        } for plan in learning_plans for task in plan.tasks],
        "industry_projects": [{
            "title": item.project.title,
            "status": item.status,
            "created_at": item.applied_at.isoformat() if item.applied_at else None,
        } for item in projects],
        "project_submissions": [{
            "project": item.application.project.title,
            "status": "EVALUATED" if item.evaluation else "SUBMITTED",
            "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
            "feedback": item.evaluation.feedback if item.evaluation else "",
            "score": item.evaluation.overall_score if item.evaluation else None,
        } for item in submissions],
        "job_applications": [{
            "job": vacancy.title,
            "company": db.get(Industry, vacancy.industry_id).company_name if db.get(Industry, vacancy.industry_id) else "Company unavailable",
            "status": application.status,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        } for application, vacancy in job_applications],
        "mentorship_history": [{
            "status": item.status,
            "mentor": item.mentor.user.name if item.mentor else None,
            "reason": item.reason,
            "notes": item.notes,
            "follow_up_date": item.follow_up_date.isoformat() if item.follow_up_date else None,
            "created_at": item.created_at.isoformat(),
        } for item in mentorship_history],
    })


@app.post("/api/institution/students/{student_id}/courses", status_code=status.HTTP_201_CREATED)
def institution_assign_course(student_id: int, payload: InstitutionCourseEnrollmentInput, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    student = db.get(Student, student_id)
    if student is None or student not in institution_students(db, institution):
        fail("Student not found in this institution", status.HTTP_404_NOT_FOUND)
    if db.get(Course, payload.course_id) is None:
        fail("Course not found", status.HTTP_404_NOT_FOUND)
    enrollment = db.scalar(select(InstitutionCourseEnrollment).where(
        InstitutionCourseEnrollment.institution_id == institution.id,
        InstitutionCourseEnrollment.student_id == student.id,
        InstitutionCourseEnrollment.course_id == payload.course_id,
    ))
    if enrollment is not None:
        fail("Course is already assigned to this student", status.HTTP_409_CONFLICT)
    enrollment = InstitutionCourseEnrollment(
        institution_id=institution.id, student_id=student.id, course_id=payload.course_id
    )
    db.add(enrollment)
    db.commit()
    return ok({"id": enrollment.id, "course_id": enrollment.course_id, "status": enrollment.status})


@app.patch("/api/institution/course-enrollments/{enrollment_id}")
def institution_update_course_status(enrollment_id: int, payload: InstitutionCourseStatusInput, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    enrollment = db.scalar(select(InstitutionCourseEnrollment).where(
        InstitutionCourseEnrollment.id == enrollment_id,
        InstitutionCourseEnrollment.institution_id == institution.id,
    ))
    if enrollment is None or enrollment.student not in institution_students(db, institution):
        fail("Course enrollment not found in this institution", status.HTTP_404_NOT_FOUND)
    enrollment.status = payload.status
    enrollment.score = payload.score
    enrollment.completed_at = utc_now() if payload.status == "COMPLETED" else None
    db.commit()
    return ok({"id": enrollment.id, "status": enrollment.status, "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None})


@app.get("/api/institution/mentors")
def institution_mentors(user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    memberships = institution_mentor_memberships(db, institution)
    students = institution_students(db, institution)
    mentorships = db.scalars(select(InstitutionMentorship).where(
        InstitutionMentorship.institution_id == institution.id,
    )).all()
    mentorship_by_student = {item.student_id: item for item in mentorships}
    active_mentor_ids = {
        membership.mentor_id
        for membership in institution_mentor_memberships(db, institution, active_only=True)
    }
    assigned = {
        item.student_id: item for item in mentorships
        if item.status in {"ASSIGNED", "IN_PROGRESS"} and item.mentor_id in active_mentor_ids
    }
    return ok({
        "mentors": [institution_mentor_payload(db, institution, item) for item in memberships],
        "students": [{
            "id": student.id,
            "name": student.user.name,
            "career_goal": student.career_goal,
            "department": student.department,
            "skill_gaps": [
                gap["skill"] for gap in institution_student_summary(db, institution, student)["skill_gaps"]
                if gap["status"] == "NEEDS_IMPROVEMENT"
            ],
            "assigned_mentor_id": assigned[student.id].mentor_id if student.id in assigned else None,
            "mentorship_status": (
                mentorship_by_student[student.id].status
                if student.id in assigned or (
                    student.id in mentorship_by_student
                    and mentorship_by_student[student.id].status not in {"ASSIGNED", "IN_PROGRESS"}
                )
                else "NOT_ASSIGNED"
            ),
            "mentorship_reason": mentorship_by_student[student.id].reason if student.id in mentorship_by_student else "",
            "mentorship_notes": mentorship_by_student[student.id].notes if student.id in mentorship_by_student else "",
            "follow_up_date": mentorship_by_student[student.id].follow_up_date.isoformat() if student.id in mentorship_by_student and mentorship_by_student[student.id].follow_up_date else None,
        } for student in students],
        "summary": {
            "total_mentors": len(memberships),
            "active_mentors": sum(item.active for item in memberships),
            "assigned_students": len(assigned),
            "students_without_mentor": sum(student.id not in assigned for student in students),
        },
    })


@app.post("/api/institution/mentors", status_code=status.HTTP_201_CREATED)
def institution_create_mentor(payload: InstitutionMentorInput, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    email = str(payload.email).strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)) is not None:
        fail("An account with this email already exists. Associate an existing mentor account instead.", status.HTTP_409_CONFLICT)
    try:
        mentor_user = User(
            name=payload.name.strip(), email=email,
            password_hash=hash_password(payload.password), role="mentor",
        )
        db.add(mentor_user)
        db.flush()
        mentor = Mentor(user_id=mentor_user.id, expertise=payload.expertise.strip(), experience=payload.experience)
        db.add(mentor)
        db.flush()
        membership = InstitutionMentorMembership(
            institution_id=institution.id, mentor_id=mentor.id,
            expertise=mentor.expertise, experience=mentor.experience,
            availability=payload.availability,
        )
        db.add(membership)
        db.commit()
    except IntegrityError:
        db.rollback()
        fail("Unable to create mentor account; an account with this email may already exist.", status.HTTP_409_CONFLICT)
    return ok(institution_mentor_payload(db, institution, membership))


@app.post("/api/institution/mentors/associate", status_code=status.HTTP_201_CREATED)
def institution_associate_mentor(payload: InstitutionMentorAssociationInput, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    mentor_user = db.scalar(select(User).where(func.lower(User.email) == str(payload.email).strip().lower()))
    mentor = db.scalar(select(Mentor).where(Mentor.user_id == mentor_user.id)) if mentor_user else None
    if mentor is None:
        fail("No existing mentor account was found for this email", status.HTTP_404_NOT_FOUND)
    if institution_mentor_membership_for(db, institution, mentor.id, active_only=False) is not None:
        fail("This mentor is already associated with your institution", status.HTTP_409_CONFLICT)
    membership = InstitutionMentorMembership(
        institution_id=institution.id, mentor_id=mentor.id,
        expertise=mentor.expertise, experience=mentor.experience,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        fail("This mentor is already associated with your institution", status.HTTP_409_CONFLICT)
    return ok(institution_mentor_payload(db, institution, membership))


@app.put("/api/institution/mentors/{mentor_id}")
def institution_update_mentor(mentor_id: int, payload: InstitutionMentorUpdateInput, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    membership = institution_mentor_membership_for(db, institution, mentor_id, active_only=False)
    if membership is None:
        fail("Mentor not found in this institution", status.HTTP_404_NOT_FOUND)
    membership.expertise = payload.expertise.strip()
    membership.experience = payload.experience
    membership.availability = payload.availability
    membership.active = payload.active
    if not payload.active:
        assignments = db.scalars(select(InstitutionMentorship).where(
            InstitutionMentorship.institution_id == institution.id,
            InstitutionMentorship.mentor_id == mentor_id,
            InstitutionMentorship.status.in_(("ASSIGNED", "IN_PROGRESS")),
        )).all()
        for assignment in assignments:
            assignment.mentor_id = None
            assignment.status = "NOT_ASSIGNED"
            assignment.reason = assignment.reason or "Mentor deactivated; reassignment required."
            db.add(InstitutionMentorshipHistory(
                institution_id=institution.id, student_id=assignment.student_id,
                mentor_id=None, status=assignment.status, reason=assignment.reason,
                notes=assignment.notes, follow_up_date=assignment.follow_up_date,
            ))
    db.commit()
    return ok(institution_mentor_payload(db, institution, membership))


@app.put("/api/institution/students/{student_id}/mentorship")
def institution_update_mentorship(student_id: int, payload: InstitutionMentorshipInput, user: Annotated[User, Depends(require_role("institution"))], db: Annotated[Session, Depends(get_db)]):
    institution = institution_for(db, user)
    student = db.get(Student, student_id)
    if student is None or student not in institution_students(db, institution):
        fail("Student not found in this institution", status.HTTP_404_NOT_FOUND)
    if payload.mentor_id is not None and institution_mentor_membership_for(db, institution, payload.mentor_id) is None:
        fail("Mentor is not actively associated with this institution", status.HTTP_404_NOT_FOUND)
    if payload.mentor_id is None and payload.status != "NOT_ASSIGNED":
        fail("A mentor must be selected for an assigned mentorship status", status.HTTP_422_UNPROCESSABLE_ENTITY)
    mentorship = db.scalar(select(InstitutionMentorship).where(
        InstitutionMentorship.institution_id == institution.id,
        InstitutionMentorship.student_id == student.id,
    ))
    if mentorship is None:
        mentorship = InstitutionMentorship(institution_id=institution.id, student_id=student.id)
        db.add(mentorship)
    mentorship.mentor_id = payload.mentor_id
    mentorship.status = payload.status
    mentorship.reason = payload.reason
    mentorship.notes = payload.notes
    mentorship.follow_up_date = payload.follow_up_date
    db.add(InstitutionMentorshipHistory(
        institution_id=institution.id,
        student_id=student.id,
        mentor_id=mentorship.mentor_id,
        status=mentorship.status,
        reason=mentorship.reason,
        notes=mentorship.notes,
        follow_up_date=mentorship.follow_up_date,
    ))
    db.commit()
    return ok({
        "student_id": student.id,
        "status": mentorship.status,
        "mentor_name": mentorship.mentor.user.name if mentorship.mentor else None,
        "follow_up_date": mentorship.follow_up_date.isoformat() if mentorship.follow_up_date else None,
    })


@app.get("/api/mentor/dashboard")
def mentor_dashboard(user: Annotated[User, Depends(require_role("mentor"))], db: Annotated[Session, Depends(get_db)]):
    mentor = db.scalar(select(Mentor).where(Mentor.user_id == user.id))
    student_ids = mentor_accessible_student_ids(db, mentor) if mentor else set()
    submissions = db.scalars(
        select(ProjectSubmission)
        .join(ProjectApplication)
        .where(ProjectApplication.student_id.in_(student_ids))
    ).all() if student_ids else []
    return ok({"pending_evaluations": sum(item.evaluation is None for item in submissions), "evaluated": sum(item.evaluation is not None for item in submissions), "submissions": [{"id": item.id, "project": item.application.project.title, "student": item.application.student.user.name, "evaluated": item.evaluation is not None} for item in submissions]})


from .industry_features import router as industry_features_router

app.include_router(industry_features_router)
from .industry_portal import router as industry_portal_router

app.include_router(industry_portal_router)
