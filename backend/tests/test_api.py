from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import bootstrap_tcs
from app.database import Base, get_db
from app.industry_features import JobVacancy
from app.industry_portal import IndustryCompanyDetails, IndustryDemoCompany
from app.main import (
    Assessment,
    AssessmentResult,
    CareerRole,
    Course,
    Industry,
    Institution,
    InstitutionCourseEnrollment,
    Mentor,
    Project,
    ProjectSubmission,
    RoleSkill,
    Skill,
    Student,
    User,
    app,
    hash_password,
)
from app.seed_demo_industry import DEMO_COMPANIES, seed_demo_industry
from app.seed_demo_company_directory import DEMO_DIRECTORY_COMPANIES, seed_demo_company_directory


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    student_user = User(name="Test Student", email="student@test.example.com", password_hash=hash_password("Student@test123"), role="student")
    industry_user = User(name="Test Company", email="industry@test.example.com", password_hash=hash_password("Industry@test123"), role="industry")
    mentor_user = User(name="Test Mentor", email="mentor@test.example.com", password_hash=hash_password("Mentor@test123"), role="mentor")
    institution_user = User(name="Test Institution", email="institution@test.example.com", password_hash=hash_password("Institution@test123"), role="institution")
    db.add_all([student_user, industry_user, mentor_user, institution_user])
    db.flush()
    student = Student(user_id=student_user.id, college="Test College", department="Computing", year=3, career_goal="Data Analyst")
    industry = Industry(user_id=industry_user.id, company_name="Test Company")
    mentor = Mentor(user_id=mentor_user.id, expertise="Analytics")
    sql = Skill(name="SQL", category="Data")
    python = Skill(name="Python", category="Programming")
    statistics = Skill(name="Statistics", category="Data")
    institution = Institution(user_id=institution_user.id, institution_name="Test College")
    db.add_all([student, industry, mentor, institution, sql, python, statistics])
    db.flush()
    role = CareerRole(name="Data Analyst", description="Analyze data.")
    db.add(role)
    db.flush()
    db.add_all([
        RoleSkill(role_id=role.id, skill_id=sql.id, required_level=4),
        RoleSkill(role_id=role.id, skill_id=python.id, required_level=3),
        RoleSkill(role_id=role.id, skill_id=statistics.id, required_level=3),
    ])
    alternate_role = CareerRole(name="Software Engineer", description="Build software.")
    db.add(alternate_role)
    db.flush()
    db.add(RoleSkill(role_id=alternate_role.id, skill_id=python.id, required_level=4))
    db.add(Project(industry_id=industry.id, title="Test Analysis", description="Analyze a dataset.", domain="Analytics", required_skills="SQL, Python", expected_outcome="A clear report.", status="OPEN"))
    db.commit()
    db.close()

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.test_session_factory = TestSession
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def associate_and_assign_test_mentor(client: TestClient):
    token = token_for(client, "institution@test.example.com", "Institution@test123")
    headers = {"Authorization": f"Bearer {token}"}
    students = client.get("/api/institution/analytics", headers=headers).json()["data"]["students"]
    associated = client.post(
        "/api/institution/mentors/associate",
        headers=headers,
        json={"email": "mentor@test.example.com"},
    )
    assert associated.status_code == 201
    assigned = client.put(
        f"/api/institution/students/{students[0]['id']}/mentorship",
        headers=headers,
        json={"mentor_id": associated.json()["data"]["mentor_id"], "status": "ASSIGNED", "reason": "", "notes": "", "follow_up_date": None},
    )
    assert assigned.status_code == 200


def test_auth_and_role_authorization(client: TestClient):
    validation_error = client.post("/api/auth/login", json={})
    assert validation_error.status_code == 422
    assert validation_error.json()["success"] is False
    assert validation_error.json()["message"]
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    response = client.get("/api/student/dashboard", headers={"Authorization": f"Bearer {student_token}"})
    assert response.status_code == 200
    forbidden = client.get("/api/industry/dashboard", headers={"Authorization": f"Bearer {student_token}"})
    assert forbidden.status_code == 403
    assert client.get("/api/institution/mentors", headers={"Authorization": f"Bearer {student_token}"}).status_code == 403
    public_mentor_registration = client.post(
        "/api/auth/register",
        json={"name": "Public Mentor", "email": "public-mentor@test.example.com", "password": "PublicMentor@test123", "role": "mentor"},
    )
    assert public_mentor_registration.status_code == 422


def test_institution_can_create_and_assign_managed_mentor(client: TestClient):
    institution_token = token_for(client, "institution@test.example.com", "Institution@test123")
    headers = {"Authorization": f"Bearer {institution_token}"}
    student = client.get("/api/institution/analytics", headers=headers).json()["data"]["students"][0]
    created = client.post("/api/institution/mentors", headers=headers, json={
        "name": "Managed Mentor", "email": "managed@test.example.com",
        "expertise": "Analytics, SQL", "experience": 8,
        "password": "SecureMentorPass123!", "availability": "AVAILABLE",
    })
    assert created.status_code == 201
    mentor = created.json()["data"]
    assert mentor["name"] == "Managed Mentor"
    assert "password" not in mentor
    duplicate = client.post("/api/institution/mentors", headers=headers, json={
        "name": "Duplicate Mentor", "email": "managed@test.example.com",
        "expertise": "Analytics", "experience": 2, "password": "AnotherSecurePass123!",
    })
    assert duplicate.status_code == 409
    assignment = client.put(
        f"/api/institution/students/{student['id']}/mentorship",
        headers=headers,
        json={"mentor_id": mentor["mentor_id"], "status": "ASSIGNED", "reason": "Student requested guidance.", "notes": "", "follow_up_date": None},
    )
    assert assignment.status_code == 200
    directory = client.get("/api/institution/mentors", headers=headers).json()["data"]
    assert directory["summary"]["active_mentors"] == 1
    assert directory["summary"]["assigned_students"] == 1
    assert directory["mentors"][0]["assigned_students"][0]["id"] == student["id"]
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    assigned_mentor = client.get("/api/student/mentor", headers={"Authorization": f"Bearer {student_token}"})
    assert assigned_mentor.status_code == 200
    assert assigned_mentor.json()["data"]["name"] == "Managed Mentor"
    deactivated = client.put(f"/api/institution/mentors/{mentor['mentor_id']}", headers=headers, json={
        "expertise": mentor["expertise"], "experience": mentor["experience"],
        "availability": mentor["availability"], "active": False,
    })
    assert deactivated.status_code == 200
    assert client.get("/api/student/mentor", headers={"Authorization": f"Bearer {student_token}"}).json()["data"] is None
    refreshed = client.get("/api/institution/mentors", headers=headers).json()["data"]
    assert refreshed["summary"]["active_mentors"] == 0
    assert refreshed["summary"]["assigned_students"] == 0


def test_mentor_membership_and_assignment_are_institution_scoped(client: TestClient):
    db = client.test_session_factory()
    second_user = User(
        name="Second Institution", email="second-institution@test.example.com",
        password_hash=hash_password("SecondInstitution@test123"), role="institution",
    )
    db.add(second_user)
    db.flush()
    db.add(Institution(user_id=second_user.id, institution_name="Other College"))
    db.commit()
    db.close()
    second_token = token_for(client, "second-institution@test.example.com", "SecondInstitution@test123")
    second_headers = {"Authorization": f"Bearer {second_token}"}
    associated = client.post(
        "/api/institution/mentors/associate",
        headers=second_headers,
        json={"email": "mentor@test.example.com"},
    )
    assert associated.status_code == 201
    mentor_id = associated.json()["data"]["mentor_id"]

    first_token = token_for(client, "institution@test.example.com", "Institution@test123")
    first_headers = {"Authorization": f"Bearer {first_token}"}
    assert client.get("/api/institution/mentors", headers=first_headers).json()["data"]["mentors"] == []
    student = client.get("/api/institution/analytics", headers=first_headers).json()["data"]["students"][0]
    denied = client.put(
        f"/api/institution/students/{student['id']}/mentorship",
        headers=first_headers,
        json={"mentor_id": mentor_id, "status": "ASSIGNED", "reason": "", "notes": "", "follow_up_date": None},
    )
    assert denied.status_code == 404


def test_mentor_cannot_review_unassigned_student_submission(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    mentor_token = token_for(client, "mentor@test.example.com", "Mentor@test123")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    mentor_headers = {"Authorization": f"Bearer {mentor_token}"}
    project = client.get("/api/projects", headers=student_headers).json()["data"][0]
    assert client.post(f"/api/projects/{project['id']}/apply", headers=student_headers).status_code == 201
    assert client.post(
        f"/api/projects/{project['id']}/submit",
        headers=student_headers,
        json={"description": "Submission awaiting assigned mentor review.", "github_url": "", "evidence": ""},
    ).status_code == 201
    db = client.test_session_factory()
    try:
        submission_id = db.query(ProjectSubmission).one().id
    finally:
        db.close()
    assert client.get("/api/mentor/submissions", headers=mentor_headers).json()["data"] == []
    denied = client.post(
        f"/api/projects/submissions/{submission_id}/evaluate",
        headers=mentor_headers,
        json={"technical_quality": 4, "problem_solving": 4, "code_quality": 4, "communication": 4, "innovation": 4, "feedback": "Review."},
    )
    assert denied.status_code == 403


def test_industry_jd_analyzer_role_authorization_and_diagnostics(client: TestClient, caplog):
    description = "Data analyst role requiring Python, SQL, and statistics."
    industry_token = token_for(client, "industry@test.example.com", "Industry@test123")
    industry_response = client.post(
        "/api/industry/skills/extract",
        headers={"Authorization": f"Bearer {industry_token}"},
        json={"description": description},
    )
    assert industry_response.status_code == 200
    assert {skill["name"] for skill in industry_response.json()["data"]["skills"]} >= {"Python", "SQL", "Statistics"}

    for role, password in (
        ("student", "Student@test123"),
        ("institution", "Institution@test123"),
    ):
        token = token_for(client, f"{role}@test.example.com", password)
        response = client.post(
            "/api/industry/skills/extract",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": description},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "You do not have permission to access this resource"
        request_id = response.headers["X-Request-ID"]
        assert request_id
        assert f"request_id={request_id}" in caplog.text
        assert f"path=/api/industry/skills/extract actual_role={role} expected_roles=industry" in caplog.text
        assert token not in caplog.text


def test_project_application_submission_evaluation_and_verification(client: TestClient):
    associate_and_assign_test_mentor(client)
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    mentor_token = token_for(client, "mentor@test.example.com", "Mentor@test123")
    headers = {"Authorization": f"Bearer {student_token}"}

    projects = client.get("/api/projects", headers=headers).json()["data"]
    project_id = projects[0]["id"]
    assert client.post(f"/api/projects/{project_id}/apply", headers=headers).status_code == 201
    duplicate = client.post(f"/api/projects/{project_id}/apply", headers=headers)
    assert duplicate.status_code == 409

    submitted = client.post(
        f"/api/projects/{project_id}/submit",
        headers=headers,
        json={"description": "Built the analysis and documented the results.", "github_url": "https://github.com/test/repo", "evidence": "Report"},
    )
    assert submitted.status_code == 201
    submission_id = client.get("/api/mentor/submissions", headers={"Authorization": f"Bearer {mentor_token}"}).json()["data"][0]["id"]
    evaluated = client.post(
        f"/api/projects/submissions/{submission_id}/evaluate",
        headers={"Authorization": f"Bearer {mentor_token}"},
        json={"technical_quality": 4, "problem_solving": 5, "code_quality": 4, "communication": 4, "innovation": 5, "feedback": "Good reasoning and clear evidence."},
    )
    assert evaluated.status_code == 200
    passport = client.get("/api/student/passport", headers=headers).json()["data"]
    assert {skill["name"] for skill in passport["skills"] if skill["verification_status"] == "VERIFIED"} == {"SQL", "Python"}
    protected_skill = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"current_skills": [{"skill_name": "SQL", "proficiency": 0}]},
    )
    assert protected_skill.status_code == 409


def test_assessment_updates_gap_and_roadmap(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    headers = {"Authorization": f"Bearer {student_token}"}
    questions = client.get("/api/assessment", headers=headers).json()["data"]["questions"]
    assert len(questions) == 10
    incomplete = client.post("/api/assessment/submit", headers=headers, json={"answers": [{"question_id": questions[0]["id"], "answer": questions[0]["options"][0]}]})
    assert incomplete.status_code == 400
    result = client.post("/api/assessment/submit", headers=headers, json={"answers": [{"question_id": q["id"], "answer": q["options"][0]} for q in questions]})
    assert result.status_code == 200
    gap = client.get("/api/skill-gap", headers=headers).json()["data"]
    assert {item["skill"] for item in gap["skills"]} == {"SQL", "Python", "Statistics"}
    roadmap = client.get("/api/roadmap", headers=headers).json()["data"]
    assert len(roadmap["tasks"]) == 4


def test_low_project_score_does_not_verify_skills(client: TestClient):
    associate_and_assign_test_mentor(client)
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    mentor_token = token_for(client, "mentor@test.example.com", "Mentor@test123")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    mentor_headers = {"Authorization": f"Bearer {mentor_token}"}
    project = client.get("/api/projects", headers=student_headers).json()["data"][0]
    client.post(f"/api/projects/{project['id']}/apply", headers=student_headers)
    client.post(
        f"/api/projects/{project['id']}/submit",
        headers=student_headers,
        json={"description": "Submitted initial project work for review.", "github_url": "", "evidence": ""},
    )
    submission_id = client.get("/api/mentor/submissions", headers=mentor_headers).json()["data"][0]["id"]
    result = client.post(
        f"/api/projects/submissions/{submission_id}/evaluate",
        headers=mentor_headers,
        json={"technical_quality": 2, "problem_solving": 2, "code_quality": 2, "communication": 2, "innovation": 2, "feedback": "Please add more validation and supporting evidence."},
    )
    assert result.status_code == 200
    assert result.json()["data"]["verified_skills"] == []


def test_learning_profile_gap_analysis_and_resource_transparency(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    headers = {"Authorization": f"Bearer {student_token}"}
    profile_response = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={
            "career_goal": "Data Analyst",
            "current_skills": [{"skill_name": "SQL", "proficiency": 3}],
            "programming_languages": ["Python", "SQL"],
            "completed_courses": ["Intro to SQL"],
            "github_url": "https://github.com/example",
            "linkedin_url": "https://www.linkedin.com/in/example",
            "study_minutes_per_day": 45,
            "learning_format": "Mixed",
        },
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()["data"]
    assert profile["career_goal"] == "Data Analyst"
    assert profile["current_skills"][0]["verification_status"] == "IN PROGRESS"
    assert profile["study_minutes_per_day"] == 45
    assert profile["github_url"] == "https://github.com/example"
    assert profile["linkedin_url"] == "https://www.linkedin.com/in/example"
    stored_profile = client.get("/api/student/learning-profile", headers=headers)
    assert stored_profile.status_code == 200
    assert stored_profile.json()["data"]["github_url"] == "https://github.com/example"
    assert stored_profile.json()["data"]["linkedin_url"] == "https://www.linkedin.com/in/example"

    analysis_response = client.get("/api/student/skill-gap-analysis", headers=headers)
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()["data"]
    assert analysis["engine"] == "rule-based"
    assert analysis["provisional"] is True
    sql = next(item for item in analysis["skills"] if item["skill"] == "SQL")
    assert (sql["current"], sql["required"], sql["gap"], sql["status"]) == (3, 4, 1, "Developing")
    assert analysis["readiness_calculation"]
    assert all(
        resource["url"].startswith("https://")
        and resource["link_type"] in {"Platform search", "Official reference", "Learning reference", "Search results"}
        for recommendation in analysis["recommendations"]
        for resource in recommendation["resources"]
    )

    invalid_url = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"github_url": "javascript:alert(1)"},
    )
    assert invalid_url.status_code == 422
    invalid_github_domain = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"github_url": "https://example.com/profile"},
    )
    assert invalid_github_domain.status_code == 422
    invalid_linkedin_domain = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"linkedin_url": "https://example.com/profile"},
    )
    assert invalid_linkedin_domain.status_code == 422
    invalid_leetcode_domain = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"leetcode_url": "https://example.com/profile"},
    )
    assert invalid_leetcode_domain.status_code == 422
    valid_leetcode = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"leetcode_url": "https://leetcode.com/u/example"},
    )
    assert valid_leetcode.status_code == 200
    assert valid_leetcode.json()["data"]["leetcode_url"] == "https://leetcode.com/u/example"
    valid_profile_subdomains = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={
            "github_url": "https://www.github.com/example",
            "linkedin_url": "https://uk.linkedin.com/in/example",
        },
    )
    assert valid_profile_subdomains.status_code == 200
    invalid_domain_suffix = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"github_url": "https://github.com.evil.example/profile"},
    )
    assert invalid_domain_suffix.status_code == 422
    unsafe_credentials_url = client.put(
        "/api/student/learning-profile",
        headers=headers,
        json={"linkedin_url": "https://user:password@linkedin.com/in/example"},
    )
    assert unsafe_credentials_url.status_code == 422


def test_learning_roadmap_status_persists_without_awarding_proficiency(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    headers = {"Authorization": f"Bearer {student_token}"}
    initial = client.get("/api/student/learning-roadmap", headers=headers)
    assert initial.status_code == 200
    roadmap = initial.json()["data"]
    assert roadmap["engine"] == "rule-based"
    assert roadmap["career_goal"] == "Data Analyst"
    assert roadmap["plan_version"] == 1
    assert roadmap["tasks"]
    task = roadmap["tasks"][0]

    updated = client.patch(
        f"/api/student/learning-roadmap/tasks/{task['id']}",
        headers=headers,
        json={"status": "Completed"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["completed_tasks"] == 1
    skills = client.get("/api/student/skills", headers=headers).json()["data"]
    if task["skill"]:
        completed_skill = next((item for item in skills if item["name"] == task["skill"]), None)
        assert completed_skill is None or completed_skill["proficiency"] == 0

    refreshed = client.post("/api/student/learning-roadmap/refresh", headers=headers)
    assert refreshed.status_code == 200
    refreshed_data = refreshed.json()["data"]
    assert refreshed_data["plan_version"] == 2
    preserved = next(item for item in refreshed_data["tasks"] if item["title"] == task["title"])
    assert preserved["status"] == "Completed"


def test_learning_endpoints_are_student_scoped(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    roadmap = client.get("/api/student/learning-roadmap", headers=student_headers).json()["data"]
    task_id = roadmap["tasks"][0]["id"]

    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Other Student",
            "email": "other@test.example.com",
            "password": "OtherStudent@123",
            "role": "student",
        },
    )
    assert registration.status_code == 201
    other_token = token_for(client, "other@test.example.com", "OtherStudent@123")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    other_profile = client.get("/api/student/learning-profile", headers=other_headers)
    assert other_profile.status_code == 200
    assert other_profile.json()["data"]["current_skills"] == []
    forbidden_task_update = client.patch(
        f"/api/student/learning-roadmap/tasks/{task_id}",
        headers=other_headers,
        json={"status": "Completed"},
    )
    assert forbidden_task_update.status_code == 404


def test_changing_career_preserves_existing_legacy_roadmap_records(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    headers = {"Authorization": f"Bearer {student_token}"}
    assert client.put("/api/student/career", headers=headers, json={"career_goal": "Data Analyst"}).status_code == 200
    original = client.get("/api/roadmap", headers=headers).json()["data"]
    original_task_ids = [task["id"] for task in original["tasks"]]
    assert original_task_ids
    completed = client.post(f"/api/roadmap/tasks/{original_task_ids[0]}/complete", headers=headers)
    assert completed.status_code == 200

    changed = client.put("/api/student/career", headers=headers, json={"career_goal": "Software Engineer"})
    assert changed.status_code == 200
    retained = client.get("/api/roadmap", headers=headers).json()["data"]
    assert [task["id"] for task in retained["tasks"]] == original_task_ids
    assert retained["tasks"][0]["completed"] is True
    assert retained["career_goal"] == "Data Analyst"

    new_plan = client.get("/api/student/learning-roadmap", headers=headers).json()["data"]
    assert new_plan["career_goal"] == "Software Engineer"


def test_industry_projects_matching_applications_and_shortlisting(client: TestClient):
    industry_token = token_for(client, "industry@test.example.com", "Industry@test123")
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    industry_headers = {"Authorization": f"Bearer {industry_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    profile = client.put(
        "/api/student/learning-profile",
        headers=student_headers,
        json={"current_skills": [
            {"skill_name": "SQL", "proficiency": 3},
            {"skill_name": "Python", "proficiency": 2},
        ]},
    )
    assert profile.status_code == 200
    posted = client.post(
        "/api/industry/projects",
        headers=industry_headers,
        json={
            "title": "Build a data report",
            "description": "Analyze a sample dataset and deliver a short report.",
            "domain": "Analytics",
            "difficulty": "Intermediate",
            "required_skills": ["SQL", "Python"],
            "required_skill_levels": {"SQL": 4, "Python": 2},
            "eligibility": "Open to undergraduate students",
        },
    )
    assert posted.status_code == 201
    project = posted.json()["data"]
    assert project["required_skill_levels"] == {"SQL": 4, "Python": 2}

    listings = client.get("/api/student/project-marketplace", headers=student_headers)
    matched = next(item for item in listings.json()["data"] if item["id"] == project["id"])
    assert matched["candidate_match"]["match_percent"] == 50
    assert matched["candidate_match"]["matched_skills"] == ["Python"]
    assert "advisory" in matched["candidate_match"]["decision_note"]
    applied = client.post(f"/api/student/project-marketplace/{project['id']}/applications", headers=student_headers)
    assert applied.status_code == 201
    application_id = applied.json()["data"]["application_id"]
    duplicate = client.post(f"/api/student/project-marketplace/{project['id']}/applications", headers=student_headers)
    assert duplicate.status_code == 409

    applicants = client.get(f"/api/industry/projects/{project['id']}/applications", headers=industry_headers)
    assert applicants.status_code == 200
    assert applicants.json()["data"][0]["candidate_match"]["skills_to_improve"] == ["SQL"]
    review = client.patch(
        f"/api/industry/project-applications/{application_id}/review",
        headers=industry_headers,
        json={"status": "SHORTLISTED", "note": "Please choose an interview time."},
    )
    assert review.status_code == 200
    tracked = client.get("/api/student/applications", headers=student_headers).json()["data"]
    project_application = next(item for item in tracked if item["kind"] == "project")
    assert project_application["status"] == "SHORTLISTED"
    assert project_application["company_note"] == "Please choose an interview time."

    forbidden = client.get(f"/api/industry/projects/{project['id']}/applications", headers=student_headers)
    assert forbidden.status_code == 403
    closed = client.patch(
        f"/api/industry/projects/{project['id']}/status",
        headers=industry_headers,
        json={"status": "CLOSED"},
    )
    assert closed.status_code == 200
    not_open = client.post(f"/api/student/project-marketplace/{project['id']}/applications", headers=student_headers)
    assert not_open.status_code == 404
    expired = client.post(
        "/api/industry/projects",
        headers=industry_headers,
        json={
            "title": "Past-deadline project",
            "description": "This challenge is no longer accepting applications.",
            "required_skills": [],
            "deadline": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert expired.status_code == 201
    expired_id = expired.json()["data"]["id"]
    expired_application = client.post(
        f"/api/student/project-marketplace/{expired_id}/applications",
        headers=student_headers,
    )
    assert expired_application.status_code == 409


def test_job_vacancy_application_shortlist_and_industry_ownership(client: TestClient):
    industry_token = token_for(client, "industry@test.example.com", "Industry@test123")
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    industry_headers = {"Authorization": f"Bearer {industry_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}
    posting = client.post(
        "/api/industry/job-vacancies",
        headers=industry_headers,
        json={
            "title": "Junior Data Analyst",
            "description": "Support reporting and analysis for our product team.",
            "location": "Remote",
            "employment_type": "Internship",
            "eligibility": "Current students",
            "required_skill_levels": {"SQL": 3},
            "deadline": "2027-01-31",
        },
    )
    assert posting.status_code == 201
    vacancy_id = posting.json()["data"]["id"]
    saved_requirements = client.put(
        f"/api/industry/job-vacancies/{vacancy_id}/requirements",
        headers=industry_headers,
        json={
            "mandatory_education": "Test College",
            "mandatory_department": "Computing",
            "mandatory_certifications": ["SQL Fundamentals"],
            "experience_requirement": "Entry level",
            "internship_duration": "12 weeks",
            "openings": 3,
            "application_instructions": "Include a project portfolio.",
        },
    )
    assert saved_requirements.status_code == 200
    assert client.get(
        f"/api/industry/job-vacancies/{vacancy_id}/requirements",
        headers=industry_headers,
    ).json()["data"]["openings"] == 3
    listing = client.get("/api/student/job-vacancies", headers=student_headers)
    assert next(item for item in listing.json()["data"] if item["id"] == vacancy_id)["candidate_match"]["match_percent"] == 0

    applied = client.post(f"/api/student/job-vacancies/{vacancy_id}/applications", headers=student_headers)
    assert applied.status_code == 201
    application_id = applied.json()["data"]["application_id"]
    analysis = client.get(
        f"/api/industry/job-applications/analysis?vacancy_id={vacancy_id}",
        headers=industry_headers,
    )
    assert analysis.status_code == 200
    candidate = analysis.json()["data"][0]
    assert candidate["eligibility"] == "NOT CURRENTLY ELIGIBLE"
    assert candidate["course_data_available"] is False
    assert candidate["course_completion_status"] == "Course Data Unavailable"
    assert candidate["course_completion_percent"] is None
    assert "Required certification not found" in " ".join(candidate["eligibility_reasons"])

    portal_update = client.post(
        f"/api/industry/job-applications/{application_id}/status",
        headers=industry_headers,
        json={"status": "SELECTED", "note": "Offer approved."},
    )
    assert portal_update.status_code == 200
    invalid_transition = client.patch(
        f"/api/industry/job-applications/{application_id}",
        headers=industry_headers,
        json={"status": "SHORTLISTED", "note": "Invalid regression."},
    )
    assert invalid_transition.status_code == 409
    duplicate = client.post(f"/api/student/job-vacancies/{vacancy_id}/applications", headers=student_headers)
    assert duplicate.status_code == 409
    applicants = client.get(f"/api/industry/job-vacancies/{vacancy_id}/applications", headers=industry_headers)
    assert applicants.status_code == 200
    assert len(applicants.json()["data"]) == 1

    update = client.patch(
        f"/api/industry/job-applications/{application_id}",
        headers=industry_headers,
        json={"status": "INTERVIEW", "note": "Interview invitation sent."},
    )
    assert update.status_code == 200
    student_apps = client.get("/api/student/applications", headers=student_headers).json()["data"]
    job_application = next(item for item in student_apps if item["kind"] == "job")
    assert job_application["status"] == "INTERVIEW"
    assert job_application["company_note"] == "Interview invitation sent."
    status_history = client.get("/api/student/application-status-history", headers=student_headers)
    assert status_history.status_code == 200
    assert {item["status"] for item in status_history.json()["data"]} >= {"SELECTED", "INTERVIEW"}

    other_industry = client.post(
        "/api/auth/register",
        json={"name": "Another Company", "email": "another@test.example.com", "password": "Another@test123", "role": "industry"},
    )
    assert other_industry.status_code == 201
    other_token = other_industry.json()["data"]["token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}
    hidden_vacancy = client.patch(
        f"/api/industry/job-vacancies/{vacancy_id}/status",
        headers=other_headers,
        json={"status": "CLOSED"},
    )
    assert hidden_vacancy.status_code == 404
    forbidden_status = client.patch(
        f"/api/industry/job-applications/{application_id}",
        headers=other_headers,
        json={"status": "SELECTED"},
    )
    assert forbidden_status.status_code == 404
    other_student = client.post(
        "/api/auth/register",
        json={"name": "Another Student", "email": "another-student@test.example.com", "password": "AnotherStudent@test123", "role": "student"},
    )
    assert other_student.status_code == 201
    other_student_headers = {"Authorization": f"Bearer {other_student.json()['data']['token']}"}
    private_apps = client.get("/api/student/applications", headers=other_student_headers)
    assert private_apps.status_code == 200
    assert private_apps.json()["data"] == []


def test_industry_portal_project_submission_review_and_consent(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    industry_token = token_for(client, "industry@test.example.com", "Industry@test123")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    industry_headers = {"Authorization": f"Bearer {industry_token}"}

    student_headers = {"Authorization": "Bearer " + student_token}
    industry_headers = {"Authorization": "Bearer " + industry_token}
    draft = client.post(
        "/api/industry/portal/projects",
        headers=industry_headers,
        json={
            "title": "TCS Data Quality Challenge",
            "description": "Build a data-quality workflow and document how it detects inconsistent records.",
            "category": "Data Engineering",
            "difficulty": "Intermediate",
            "required_skill_levels": {"SQL": 3, "Python": 2},
            "expected_outcome": "A tested workflow",
            "acceptance_criteria": "Include tests and a written report",
            "instructions": "Use the supplied project requirements.",
            "deliverables": ["Source code", "Test report"],
            "references": ["https://example.com/reference"],
            "deadline": (date.today() + timedelta(days=14)).isoformat(),
            "duration_weeks": 3,
            "participation": "Team",
            "team_size_min": 2,
            "team_size_max": 4,
            "eligibility": "Undergraduate students",
            "publication_status": "DRAFT",
        },
    )
    assert draft.status_code == 201, draft.text
    draft_data = draft.json()["data"]
    assert draft_data["publication_status"] == "DRAFT"
    assert draft_data["deliverables"] == ["Source code", "Test report"]
    project_id = draft_data["id"]
    marketplace = client.get("/api/student/project-marketplace", headers=student_headers).json()["data"]
    assert project_id not in {item["id"] for item in marketplace}

    published = client.patch(
        f"/api/industry/portal/projects/{project_id}/status?publication_status=PUBLISHED",
        headers=industry_headers,
    )
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "OPEN"
    project_detail = client.get(f"/api/projects/{project_id}", headers=student_headers)
    assert project_detail.status_code == 200
    assert project_detail.json()["data"]["instructions"] == "Use the supplied project requirements."
    application = client.post(
        f"/api/student/project-marketplace/{project_id}/applications",
        headers=student_headers,
    )
    assert application.status_code == 201

    profile = client.put(
        "/api/student/learning-profile",
        headers=student_headers,
        json={
            "github_url": "https://github.com/test-student",
            "linkedin_url": "https://www.linkedin.com/in/test-student",
        },
    )
    assert profile.status_code == 200
    sharing = client.put(
        "/api/student/profile-sharing",
        headers=student_headers,
        json={"share_social_links": True},
    )
    assert sharing.status_code == 200

    submitted = client.post(
        f"/api/projects/{project_id}/submission",
        headers=student_headers,
        json={
            "summary": "A tested data validation pipeline",
            "description": "Implemented the pipeline, tests, and a clear explanation of the validation results.",
            "github_url": "https://github.com/test-student/data-check",
            "demo_url": "https://example.com/demo",
            "report_url": "https://example.com/report",
            "evidence": "Test output and documentation",
            "skills_used": ["SQL", "Python"],
        },
    )
    assert submitted.status_code == 201, submitted.text
    submission_id = submitted.json()["data"]["submission_id"]
    industry_submissions = client.get("/api/industry/project-submissions", headers=industry_headers)
    assert industry_submissions.status_code == 200
    submission = industry_submissions.json()["data"][0]
    assert submission["id"] == submission_id
    assert "linkedin_url" not in submission
    assert "github_profile_url" not in submission
    private = client.put(
        "/api/student/profile-sharing",
        headers=student_headers,
        json={"share_social_links": False},
    )
    assert private.status_code == 200
    hidden_links = client.get("/api/industry/project-submissions", headers=industry_headers).json()["data"][0]
    assert "linkedin_url" not in hidden_links
    assert "github_profile_url" not in hidden_links
    client.put(
        "/api/student/profile-sharing",
        headers=student_headers,
        json={"share_social_links": True},
    )

    review_payload = {
        "decision": "NEEDS_REVISION",
        "overall_feedback": "Good foundation; add coverage for invalid values.",
        "technical_feedback": "The processing path is clear.",
        "code_quality_feedback": "Separate validation into a reusable function.",
        "problem_solving_feedback": "Add tests for edge cases.",
        "strengths": "Clear implementation.",
        "improvement_areas": "Expand validation tests.",
        "recommended_skills": ["Testing"],
        "rating": 4,
        "revision_instructions": "Add tests for missing and malformed records.",
    }
    review = client.post(
        f"/api/industry/project-submissions/{submission_id}/reviews",
        headers=industry_headers,
        json=review_payload,
    )
    assert review.status_code == 201
    student_history = client.get("/api/student/project-submissions", headers=student_headers)
    assert student_history.status_code == 200
    assert student_history.json()["data"][0]["reviews"][0]["revision_instructions"] == review_payload["revision_instructions"]
    assert student_history.json()["data"][0]["revision_count"] == 0

    revised = client.post(
        f"/api/projects/{project_id}/submission",
        headers=student_headers,
        json={
            "summary": "Updated pipeline with edge-case coverage",
            "description": "Added and documented tests for missing values, malformed values, and the normal input path.",
            "github_url": "https://github.com/test-student/data-check",
            "demo_url": "",
            "report_url": "",
            "evidence": "Updated test results",
            "skills_used": ["SQL", "Python", "Testing"],
        },
    )
    assert revised.status_code == 201, revised.text
    updated_history = client.get("/api/student/project-submissions", headers=student_headers).json()["data"][0]
    assert updated_history["revision_count"] == 1
    assert updated_history["summary"] == "Updated pipeline with edge-case coverage"

    notifications = client.get("/api/student/notifications", headers=student_headers)
    assert notifications.status_code == 200
    assert {item["kind"] for item in notifications.json()["data"]} >= {"PROJECT_REVIEW"}
    marked = client.patch(
        f"/api/notifications/{notifications.json()['data'][0]['id']}/read",
        headers=student_headers,
    )
    assert marked.status_code == 200

    assert client.get("/api/industry/project-submissions", headers=student_headers).status_code == 403
    assert client.get("/api/industry/company-profile", headers=student_headers).status_code == 403

    company_profile = client.get("/api/industry/company-profile", headers=industry_headers)
    assert company_profile.status_code == 200
    assert company_profile.json()["data"]["company_name"] == "Test Company"
    updated_profile = client.put(
        "/api/industry/company-profile",
        headers=industry_headers,
        json={
            "company_name": "Test Company",
            "industry_type": "Technology",
            "description": "Company description updated by its authenticated owner.",
            "website": "https://company.example.com",
            "company_email": "careers@company.example.com",
            "contact_person": "Recruiter",
            "contact_title": "Talent Partner",
            "phone": "+1-555-0100",
            "logo_url": "https://company.example.com/logo.png",
        },
    )
    assert updated_profile.status_code == 200
    assert updated_profile.json()["data"]["website"] == "https://company.example.com"
    invalid_profile_url = client.put(
        "/api/industry/company-profile",
        headers=industry_headers,
        json={"company_name": "Test Company", "website": "javascript:alert(1)"},
    )
    assert invalid_profile_url.status_code == 422

    draft_vacancy = client.post(
        "/api/industry/portal/job-vacancies",
        headers=industry_headers,
        json={
            "title": "TCS Data Engineering Internship",
            "description": "Work with the analytics team to build reliable data pipelines.",
            "location": "Hybrid",
            "employment_type": "Internship",
            "eligibility": "Current undergraduate students",
            "required_skill_levels": {"SQL": 2},
            "deadline": "",
            "status": "DRAFT",
        },
    )
    assert draft_vacancy.status_code == 201, draft_vacancy.text
    vacancy_id = draft_vacancy.json()["data"]["id"]
    visible_vacancies = client.get("/api/student/job-vacancies", headers=student_headers).json()["data"]
    assert vacancy_id not in {item["id"] for item in visible_vacancies}
    published_vacancy = client.patch(
        f"/api/industry/portal/job-vacancies/{vacancy_id}/status?vacancy_status=OPEN",
        headers=industry_headers,
    )
    assert published_vacancy.status_code == 200
    visible_vacancies = client.get("/api/student/job-vacancies", headers=student_headers).json()["data"]
    assert vacancy_id in {item["id"] for item in visible_vacancies}

    second_company = client.post(
        "/api/auth/register",
        json={"name": "Another Company", "email": "another-portal@test.example.com", "password": "AnotherPortal@test123", "role": "industry"},
    )
    assert second_company.status_code == 201
    second_headers = {"Authorization": "Bearer " + second_company.json()["data"]["token"]}
    assert client.get("/api/industry/project-submissions", headers=second_headers).json()["data"] == []
    assert client.get("/api/industry/company-profile", headers=second_headers).json()["data"]["company_name"] == "Another Company"
    isolated_update = client.patch(
        f"/api/industry/portal/projects/{project_id}/status?publication_status=CLOSED",
        headers=second_headers,
    )
    assert isolated_update.status_code == 404


def test_tcs_bootstrap_is_isolated_and_idempotent(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(bootstrap_tcs, "engine", engine)
    monkeypatch.setattr(bootstrap_tcs, "SessionLocal", sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))
    monkeypatch.setenv("TCS_INDUSTRY_EMAIL", "tcs-portal@test.example.com")
    monkeypatch.setenv("TCS_INDUSTRY_PASSWORD", "TcsPortal@test123")

    assert bootstrap_tcs.bootstrap_tcs() == "TCS Industry account configured. Credentials were not displayed."
    assert bootstrap_tcs.bootstrap_tcs() == "TCS account is already configured."
    with sessionmaker(bind=engine)() as db:
        tcs_user = db.query(User).filter_by(email="tcs-portal@test.example.com").one()
        assert tcs_user.role == "industry"
        assert tcs_user.industry.company_name == "TCS — Tata Consultancy Services"
        assert db.get(IndustryCompanyDetails, tcs_user.industry.id) is not None
    engine.dispose()


def test_job_profile_access_requires_application_scoped_student_consent(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    industry_token = token_for(client, "industry@test.example.com", "Industry@test123")
    student_headers = {"Authorization": "Bearer " + student_token}
    industry_headers = {"Authorization": "Bearer " + industry_token}
    profile = client.put(
        "/api/student/learning-profile",
        headers=student_headers,
        json={
            "linkedin_url": "https://www.linkedin.com/in/private-student",
            "github_url": "https://github.com/private-student",
            "leetcode_url": "https://leetcode.com/u/private-student",
        },
    )
    assert profile.status_code == 200

    vacancy_response = client.post(
        "/api/industry/job-vacancies",
        headers=industry_headers,
        json={
            "title": "Profile Consent Test Role",
            "description": "A test vacancy to verify role and application-scoped profile permissions.",
            "required_skill_levels": {"SQL": 1},
        },
    )
    assert vacancy_response.status_code == 201
    vacancy_id = vacancy_response.json()["data"]["id"]

    no_consent = client.post(
        f"/api/student/job-vacancies/{vacancy_id}/applications",
        headers=student_headers,
    )
    assert no_consent.status_code == 201
    first_application_id = no_consent.json()["data"]["application_id"]
    applicants = client.get(
        f"/api/industry/job-vacancies/{vacancy_id}/applications",
        headers=industry_headers,
    )
    assert applicants.status_code == 200
    first_applicant = applicants.json()["data"][0]
    assert first_applicant["profile_access_status"] == "NOT_GRANTED"
    assert not any(key in first_applicant for key in ("linkedin_url", "github_url", "leetcode_url"))
    assert client.get(
        f"/api/industry/job-applications/{first_application_id}/profiles",
        headers=industry_headers,
    ).status_code == 403

    denied_vacancy = client.post(
        "/api/industry/job-vacancies",
        headers=industry_headers,
        json={
            "title": "Explicit Decline Role",
            "description": "A vacancy where the applicant explicitly declines sharing their profiles.",
            "required_skill_levels": {},
        },
    )
    assert denied_vacancy.status_code == 201
    declined = client.post(
        f"/api/student/job-vacancies/{denied_vacancy.json()['data']['id']}/applications",
        headers=student_headers,
        json={"consent_decision": "DECLINED", "profile_types": []},
    )
    assert declined.status_code == 201
    declined_record = client.get("/api/student/job-profile-access", headers=student_headers)
    assert declined_record.status_code == 200
    assert next(item for item in declined_record.json()["data"] if item["job_application_id"] == declined.json()["data"]["application_id"])["profile_access_status"] == "DENIED"

    other_industry = client.post(
        "/api/auth/register",
        json={"name": "Other Employer", "email": "other-employer@test.example.com", "password": "OtherEmployer@test123", "role": "industry"},
    )
    assert other_industry.status_code == 201
    other_industry_headers = {"Authorization": "Bearer " + other_industry.json()["data"]["token"]}
    assert client.get(
        f"/api/industry/job-vacancies/{vacancy_id}/applications",
        headers=other_industry_headers,
    ).status_code == 404
    assert client.post(
        f"/api/industry/job-applications/{first_application_id}/profile-access-request",
        headers=other_industry_headers,
        json={"profile_types": ["linkedin"]},
    ).status_code == 404
    assert client.get(
        f"/api/industry/job-applications/{first_application_id}/profiles",
        headers=other_industry_headers,
    ).status_code == 404

    request_access = client.post(
        f"/api/industry/job-applications/{first_application_id}/profile-access-request",
        headers=industry_headers,
        json={"profile_types": ["linkedin", "leetcode"]},
    )
    assert request_access.status_code == 200
    assert request_access.json()["data"]["profile_access_status"] == "REQUESTED"
    assert client.get(
        f"/api/industry/job-applications/{first_application_id}/profiles",
        headers=industry_headers,
    ).status_code == 403
    access_records = client.get("/api/student/job-profile-access", headers=student_headers)
    requested = next(item for item in access_records.json()["data"] if item["job_application_id"] == first_application_id)
    assert requested["company"] == "Test Company"
    assert requested["requested_profile_types"] == ["leetcode", "linkedin"]

    other_student = client.post(
        "/api/auth/register",
        json={"name": "Other Student", "email": "other-student@test.example.com", "password": "OtherStudent@test123", "role": "student"},
    )
    assert other_student.status_code == 201
    other_student_headers = {"Authorization": "Bearer " + other_student.json()["data"]["token"]}
    assert client.post(
        f"/api/student/job-applications/{first_application_id}/profile-access-response",
        headers=other_student_headers,
        json={"decision": "GRANTED", "granted_profile_types": ["linkedin"]},
    ).status_code == 404
    assert client.get("/api/student/job-profile-access", headers=other_student_headers).json()["data"] == []

    granted = client.post(
        f"/api/student/job-applications/{first_application_id}/profile-access-response",
        headers=student_headers,
        json={"decision": "GRANTED", "granted_profile_types": ["linkedin"]},
    )
    assert granted.status_code == 200
    returned = client.get(
        f"/api/industry/job-applications/{first_application_id}/profiles",
        headers=industry_headers,
    )
    assert returned.status_code == 200
    assert returned.json()["data"]["profiles"] == {"linkedin": "https://www.linkedin.com/in/private-student"}

    revoked = client.post(
        f"/api/student/job-applications/{first_application_id}/profile-access-revoke",
        headers=student_headers,
        json={"profile_types": ["linkedin"]},
    )
    assert revoked.status_code == 200
    assert revoked.json()["data"]["profile_access_status"] == "REVOKED"
    assert client.get(
        f"/api/industry/job-applications/{first_application_id}/profiles",
        headers=industry_headers,
    ).status_code == 403


def test_job_application_can_grant_selected_profiles_at_submission(client: TestClient):
    student_token = token_for(client, "student@test.example.com", "Student@test123")
    industry_token = token_for(client, "industry@test.example.com", "Industry@test123")
    student_headers = {"Authorization": "Bearer " + student_token}
    industry_headers = {"Authorization": "Bearer " + industry_token}
    assert client.put(
        "/api/student/learning-profile",
        headers=student_headers,
        json={
            "github_url": "https://github.com/selected-student",
            "leetcode_url": "https://leetcode.com/u/selected-student",
        },
    ).status_code == 200
    vacancy = client.post(
        "/api/industry/job-vacancies",
        headers=industry_headers,
        json={
            "title": "Selected Profile Test",
            "description": "A test vacancy for explicit selected profile consent at application time.",
            "required_skill_levels": {},
        },
    )
    assert vacancy.status_code == 201
    applied = client.post(
        f"/api/student/job-vacancies/{vacancy.json()['data']['id']}/applications",
        headers=student_headers,
        json={"consent_decision": "GRANTED", "profile_types": ["github", "leetcode"]},
    )
    assert applied.status_code == 201
    applicant = client.get(
        f"/api/industry/job-vacancies/{vacancy.json()['data']['id']}/applications",
        headers=industry_headers,
    ).json()["data"][0]
    assert applicant["profile_access_status"] == "GRANTED"
    assert set(applicant["granted_profile_types"]) == {"github", "leetcode"}
    profile_access = client.get(
        f"/api/industry/job-applications/{applied.json()['data']['application_id']}/profiles",
        headers=industry_headers,
    )
    assert profile_access.status_code == 200
    assert profile_access.json()["data"]["profiles"] == {
        "github": "https://github.com/selected-student",
        "leetcode": "https://leetcode.com/u/selected-student",
    }
    partial_revoke = client.post(
        f"/api/student/job-applications/{applied.json()['data']['application_id']}/profile-access-revoke",
        headers=student_headers,
        json={"profile_types": ["leetcode"]},
    )
    assert partial_revoke.status_code == 200
    still_permitted = client.get(
        f"/api/industry/job-applications/{applied.json()['data']['application_id']}/profiles",
        headers=industry_headers,
    )
    assert still_permitted.status_code == 200
    assert still_permitted.json()["data"]["profiles"] == {"github": "https://github.com/selected-student"}
    revoke_all = client.post(
        f"/api/student/job-applications/{applied.json()['data']['application_id']}/profile-access-revoke",
        headers=student_headers,
        json={},
    )
    assert revoke_all.status_code == 200
    assert client.get(
        f"/api/industry/job-applications/{applied.json()['data']['application_id']}/profiles",
        headers=industry_headers,
    ).status_code == 403


def test_demo_industry_seed_is_repeatable_and_company_scoped(client: TestClient):
    db = client.test_session_factory()
    try:
        users_before_directory_seed = db.query(User).count()
        vacancies_before_directory_seed = db.query(JobVacancy).count()
        assert seed_demo_company_directory(db) == 6
        assert seed_demo_company_directory(db) == 0
        assert db.query(User).count() == users_before_directory_seed
        assert db.query(JobVacancy).count() == vacancies_before_directory_seed
        assert db.query(Industry).count() == 1
        assert len(DEMO_DIRECTORY_COMPANIES) == 6

        existing_names = set(db.query(Skill.name).all())
        required_names = {
            name
            for company in DEMO_COMPANIES
            for name in (*company["job"]["skills"].keys(), *company["job"]["preferred"])
        }
        db.add_all(Skill(name=name, category="Demo test") for name in required_names if (name,) not in existing_names)
        db.commit()
        credentials = {
            company["key"]: (f"{company['key']}-demo@test.example.com", "DemoRecruiter@test123")
            for company in DEMO_COMPANIES
        }
        assert seed_demo_industry(db, credentials) == {"companies": 6, "vacancies": 6}
        assert seed_demo_industry(db, credentials) == {"companies": 0, "vacancies": 0}
    finally:
        db.close()

    industry_headers = {"Authorization": "Bearer " + token_for(client, "industry@test.example.com", "Industry@test123")}
    directory = client.get("/api/industry/demo-companies", headers=industry_headers)
    assert directory.status_code == 200
    companies = directory.json()["data"]
    assert len(companies) == 6
    assert {company["account_status"] for company in companies} == {"DEMO COMPANY"}
    assert all(company["is_demo"] for company in companies)
    assert {company["company_name"] for company in companies} == {
        "Tata Consultancy Services (TCS)", "Amazon", "Infosys", "Microsoft", "Wipro", "Accenture",
    }
    assert all("not a registered employer" in company["description"] for company in companies)
    assert client.get("/api/industry/demo-companies").status_code == 401
    assert client.get(
        "/api/industry/demo-companies",
        headers={"Authorization": "Bearer " + token_for(client, "student@test.example.com", "Student@test123")},
    ).status_code == 403

    student_headers = {"Authorization": "Bearer " + token_for(client, "student@test.example.com", "Student@test123")}
    open_jobs = client.get("/api/student/job-vacancies", headers=student_headers)
    assert open_jobs.status_code == 200
    demo_jobs = open_jobs.json()["data"]
    assert len(demo_jobs) == 6
    assert all(job["is_demo"] and job["demo_label"] == "DEMO SAMPLE OPENING" for job in demo_jobs)
    assert all("not a verified or live vacancy" in job["description"].lower() for job in demo_jobs)

    tcs_headers = {"Authorization": "Bearer " + token_for(client, "tcs-demo@test.example.com", "DemoRecruiter@test123")}
    amazon_headers = {"Authorization": "Bearer " + token_for(client, "amazon-demo@test.example.com", "DemoRecruiter@test123")}
    tcs_vacancies = client.get("/api/industry/portal/job-vacancies", headers=tcs_headers).json()["data"]
    assert len(tcs_vacancies) == 1
    tcs_job = tcs_vacancies[0]
    assert tcs_job["is_demo"] is True
    assert tcs_job["preferred_skills"]
    application = client.post(
        f"/api/student/job-vacancies/{tcs_job['id']}/applications",
        headers=student_headers,
        json={"consent_decision": "DECLINED", "profile_types": []},
    )
    assert application.status_code == 201
    own_applicants = client.get(
        f"/api/industry/job-vacancies/{tcs_job['id']}/applications",
        headers=tcs_headers,
    )
    assert own_applicants.status_code == 200
    assert len(own_applicants.json()["data"]) == 1
    other_company_applicants = client.get(
        f"/api/industry/job-vacancies/{tcs_job['id']}/applications",
        headers=amazon_headers,
    )
    assert other_company_applicants.status_code == 404
    unauthorized_status = client.post(
        f"/api/industry/job-applications/{application.json()['data']['application_id']}/status",
        headers=amazon_headers,
        json={"status": "REVIEWING"},
    )
    assert unauthorized_status.status_code == 404
    directory_after_apply = client.get("/api/industry/demo-companies", headers=industry_headers).json()["data"]
    assert len(directory_after_apply) == 6
    assert client.patch(
        f"/api/industry/portal/job-vacancies/{tcs_job['id']}/status?vacancy_status=CLOSED",
        headers=tcs_headers,
    ).status_code == 200
    second_student = client.post(
        "/api/auth/register",
        json={"name": "Second Test Student", "email": "second-student@test.example.com", "password": "SecondStudent@test123", "role": "student"},
    )
    assert second_student.status_code == 201
    second_student_headers = {"Authorization": "Bearer " + second_student.json()["data"]["token"]}
    closed_application = client.post(
        f"/api/student/job-vacancies/{tcs_job['id']}/applications",
        headers=second_student_headers,
        json={"consent_decision": "DECLINED", "profile_types": []},
    )
    assert closed_application.status_code == 404


def test_demo_seeder_never_takes_over_existing_accounts(client: TestClient):
    credentials = {
        company["key"]: (f"{company['key']}-demo@test.example.com", "DemoRecruiter@test123")
        for company in DEMO_COMPANIES
    }
    credentials["tcs"] = ("industry@test.example.com", "DemoRecruiter@test123")
    db = client.test_session_factory()
    try:
        required_names = {
            name
            for company in DEMO_COMPANIES
            for name in (*company["job"]["skills"].keys(), *company["job"]["preferred"])
        }
        existing_names = set(db.query(Skill.name).all())
        db.add_all(Skill(name=name, category="Demo test") for name in required_names if (name,) not in existing_names)
        db.commit()
        existing = db.query(Industry).filter_by(company_name="Test Company").one()
        with pytest.raises(ValueError, match="already belongs to an account"):
            seed_demo_industry(db, credentials)
        db.refresh(existing)
        assert existing.company_name == "Test Company"
        assert db.query(IndustryDemoCompany).count() == 0
    finally:
        db.close()


def test_institution_dashboard_scopes_students_and_manages_course_and_mentorship(client: TestClient):
    token = token_for(client, "institution@test.example.com", "Institution@test123")
    headers = {"Authorization": f"Bearer {token}"}
    db = client.test_session_factory()
    try:
        student = db.query(Student).one()
        course = Course(title="Test course", skill_id=db.query(Skill).filter_by(name="Python").one().id)
        outside_user = User(name="Outside Student", email="outside@test.example.com", password_hash=hash_password("Outside@test123"), role="student")
        other_institution_user = User(name="Other Institution", email="other-institution@test.example.com", password_hash=hash_password("OtherInstitution@test123"), role="institution")
        db.add_all([course, outside_user, other_institution_user])
        db.flush()
        assessment = Assessment(student_id=student.id, title="Python diagnostic", completed_at=datetime.now())
        db.add(assessment)
        db.flush()
        db.add(AssessmentResult(
            assessment_id=assessment.id,
            skill_id=db.query(Skill).filter_by(name="Python").one().id,
            score=78,
            proficiency=3,
        ))
        outside_student = Student(user_id=outside_user.id, college="Other College", department="Computing", year=2)
        other_institution = Institution(user_id=other_institution_user.id, institution_name="Other College")
        db.add_all([outside_student, other_institution])
        db.commit()
        course_id = course.id
        outside_student_id = outside_student.id
        student_id = student.id
        mentor_id = db.query(Mentor).one().id
    finally:
        db.close()

    dashboard = client.get("/api/institution/dashboard", headers=headers)
    assert dashboard.status_code == 200
    data = dashboard.json()["data"]
    assert data["total_students"] == 1
    assert data["students"][0]["id"] == student_id
    assert data["students"][0]["course_completion_percent"] is None
    assert data["students"][0]["skill_gap_status"] == "ASSESSMENT_PENDING"
    assert data["students"][0]["assessed_skills"][0]["skill"] == "Python"

    assigned = client.post(
        f"/api/institution/students/{student_id}/courses",
        headers=headers,
        json={"course_id": course_id},
    )
    assert assigned.status_code == 201
    enrollment_id = assigned.json()["data"]["id"]
    student_headers = {"Authorization": f"Bearer {token_for(client, 'student@test.example.com', 'Student@test123')}"}
    student_courses = client.get("/api/student/institution-courses", headers=student_headers)
    assert student_courses.status_code == 200
    assert student_courses.json()["data"][0]["course_name"] == "Test course"
    assert client.patch(
        f"/api/institution/course-enrollments/{enrollment_id}",
        headers=student_headers,
        json={"status": "COMPLETED", "score": 92},
    ).status_code == 403
    duplicate = client.post(
        f"/api/institution/students/{student_id}/courses",
        headers=headers,
        json={"course_id": course_id},
    )
    assert duplicate.status_code == 409
    completed = client.patch(
        f"/api/institution/course-enrollments/{enrollment_id}",
        headers=headers,
        json={"status": "COMPLETED", "score": 92},
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["completed_at"]

    associated_mentor = client.post(
        "/api/institution/mentors/associate",
        headers=headers,
        json={"email": "mentor@test.example.com"},
    )
    assert associated_mentor.status_code == 201
    mentor_id = associated_mentor.json()["data"]["mentor_id"]
    mentorship = client.put(
        f"/api/institution/students/{student_id}/mentorship",
        headers=headers,
        json={
            "mentor_id": mentor_id,
            "status": "ASSIGNED",
            "reason": "Student requested guidance.",
            "notes": "Schedule a check-in.",
            "follow_up_date": "2026-11-01",
        },
    )
    assert mentorship.status_code == 200
    detail = client.get(f"/api/institution/students/{student_id}", headers=headers)
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["course_completion_percent"] == 100
    assert detail_data["course_records"][0]["score"] == 92
    assert detail_data["mentor_name"] == "Test Mentor"
    assert detail_data["mentorship_history"][0]["notes"] == "Schedule a check-in."
    assert client.get(f"/api/institution/students/{outside_student_id}", headers=headers).status_code == 404

    other_institution_headers = {"Authorization": f"Bearer {token_for(client, 'other-institution@test.example.com', 'OtherInstitution@test123')}"}
    assert client.get(f"/api/institution/students/{outside_student_id}", headers=other_institution_headers).status_code == 200
    assert client.get(f"/api/institution/students/{student_id}", headers=other_institution_headers).status_code == 404

    assert client.get("/api/institution/dashboard", headers=student_headers).status_code == 403
