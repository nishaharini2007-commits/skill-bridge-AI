from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import (
    CareerRole,
    Industry,
    Mentor,
    Project,
    RoleSkill,
    Skill,
    Student,
    User,
    app,
    hash_password,
)


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    student_user = User(name="Test Student", email="student@test.example.com", password_hash=hash_password("Student@test123"), role="student")
    industry_user = User(name="Test Company", email="industry@test.example.com", password_hash=hash_password("Industry@test123"), role="industry")
    mentor_user = User(name="Test Mentor", email="mentor@test.example.com", password_hash=hash_password("Mentor@test123"), role="mentor")
    db.add_all([student_user, industry_user, mentor_user])
    db.flush()
    student = Student(user_id=student_user.id, college="Test College", department="Computing", year=3, career_goal="Data Analyst")
    industry = Industry(user_id=industry_user.id, company_name="Test Company")
    mentor = Mentor(user_id=mentor_user.id, expertise="Analytics")
    sql = Skill(name="SQL", category="Data")
    python = Skill(name="Python", category="Programming")
    statistics = Skill(name="Statistics", category="Data")
    db.add_all([student, industry, mentor, sql, python, statistics])
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
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def token_for(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


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


def test_project_application_submission_evaluation_and_verification(client: TestClient):
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
            "study_minutes_per_day": 45,
            "learning_format": "Mixed",
        },
    )
    assert profile_response.status_code == 200
    profile = profile_response.json()["data"]
    assert profile["career_goal"] == "Data Analyst"
    assert profile["current_skills"][0]["verification_status"] == "IN PROGRESS"
    assert profile["study_minutes_per_day"] == 45

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
    listing = client.get("/api/student/job-vacancies", headers=student_headers)
    assert next(item for item in listing.json()["data"] if item["id"] == vacancy_id)["candidate_match"]["match_percent"] == 0

    applied = client.post(f"/api/student/job-vacancies/{vacancy_id}/applications", headers=student_headers)
    assert applied.status_code == 201
    application_id = applied.json()["data"]["application_id"]
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
