from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.main import (
    CareerRole,
    Certification,
    Course,
    Industry,
    Institution,
    Mentor,
    Opportunity,
    Project,
    RoleSkill,
    Roadmap,
    RoadmapTask,
    Skill,
    Student,
    StudentSkill,
    User,
    ensure_assessment_bank,
    hash_password,
)


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        skill_data = [
            ("Python", "Programming"), ("SQL", "Data"), ("Statistics", "Data"),
            ("Power BI", "Tools"), ("Data Visualization", "Data"), ("Excel", "Tools"),
            ("Problem Solving", "Core"), ("Machine Learning", "AI"), ("Cloud", "Infrastructure"),
            ("Cybersecurity", "Security"), ("JavaScript", "Programming"), ("React", "Programming"),
            ("Communication", "Core"), ("Teamwork", "Core"), ("Git", "Tools"),
            ("Data Cleaning", "Data"), ("DAX", "Data"), ("API Design", "Programming"),
        ]
        skills = {name: Skill(name=name, category=category, description=f"Practical {name} capability") for name, category in skill_data}
        db.add_all(skills.values())
        db.flush()

        role_specs = {
            "Data Analyst": {"SQL": 4, "Python": 4, "Statistics": 3, "Power BI": 4, "Data Visualization": 4, "Excel": 4, "Problem Solving": 3},
            "Full Stack Developer": {"JavaScript": 4, "React": 4, "SQL": 3, "Python": 2, "Git": 3, "API Design": 4, "Problem Solving": 4},
            "AI/ML Engineer": {"Python": 5, "Statistics": 4, "Machine Learning": 5, "SQL": 3, "Cloud": 3, "Problem Solving": 4},
            "Cybersecurity Analyst": {"Cybersecurity": 5, "Python": 3, "Cloud": 3, "SQL": 2, "Problem Solving": 4, "Communication": 3},
            "Cloud Engineer": {"Cloud": 5, "Python": 3, "SQL": 2, "Git": 3, "Cybersecurity": 3, "Problem Solving": 4},
        }
        roles = {}
        for name, requirements in role_specs.items():
            role = CareerRole(name=name, description=f"Build in-demand skills for a career as a {name}.")
            db.add(role)
            db.flush()
            roles[name] = role
            for skill_name, level in requirements.items():
                db.add(RoleSkill(role_id=role.id, skill_id=skills[skill_name].id, required_level=level))

        demo_users = [
            User(name="Arun Kumar", email="student@skillbridge.demo", password_hash=hash_password("Student@123"), role="student"),
            User(name="Priya Sharma", email="priya@skillbridge.demo", password_hash=hash_password("Student@123"), role="student"),
            User(name="Rahul Mehta", email="rahul@skillbridge.demo", password_hash=hash_password("Student@123"), role="student"),
            User(name="Aisha Khan", email="aisha@skillbridge.demo", password_hash=hash_password("Student@123"), role="student"),
            User(name="Kavya Nair", email="kavya@skillbridge.demo", password_hash=hash_password("Student@123"), role="student"),
            User(name="Northstar Analytics", email="industry@skillbridge.demo", password_hash=hash_password("Industry@123"), role="industry"),
            User(name="GreenGrid Labs", email="greengrid@skillbridge.demo", password_hash=hash_password("Industry@123"), role="industry"),
            User(name="BrightPath Digital", email="brightpath@skillbridge.demo", password_hash=hash_password("Industry@123"), role="industry"),
            User(name="Maya Iyer", email="mentor@skillbridge.demo", password_hash=hash_password("Mentor@123"), role="mentor"),
            User(name="Dev Patel", email="dev@skillbridge.demo", password_hash=hash_password("Mentor@123"), role="mentor"),
            User(name="Leena Thomas", email="leena@skillbridge.demo", password_hash=hash_password("Mentor@123"), role="mentor"),
            User(name="Riverdale Institute", email="institution@skillbridge.demo", password_hash=hash_password("Institution@123"), role="institution"),
            User(name="National Tech College", email="ntc@skillbridge.demo", password_hash=hash_password("Institution@123"), role="institution"),
        ]
        db.add_all(demo_users)
        db.flush()

        students = []
        student_data = [
            ("student@skillbridge.demo", "Riverdale Institute of Technology", "Computer Science", 3, "Data Analyst", "Curious about turning messy data into useful decisions.", "analytics, python, dashboards", {"Python": 3, "SQL": 2, "Statistics": 3, "Power BI": 1, "Data Visualization": 2, "Excel": 3}),
            ("priya@skillbridge.demo", "National Tech College", "Information Technology", 4, "Full Stack Developer", "Building accessible web products.", "react, design, APIs", {"JavaScript": 3, "React": 2, "SQL": 3, "Git": 3}),
            ("rahul@skillbridge.demo", "Riverdale Institute of Technology", "AI & Data Science", 3, "AI/ML Engineer", "Exploring applied machine learning.", "python, machine learning", {"Python": 4, "Statistics": 3, "Machine Learning": 2, "SQL": 2}),
            ("aisha@skillbridge.demo", "National Tech College", "Cybersecurity", 2, "Cybersecurity Analyst", "Interested in resilient systems and digital safety.", "security, cloud, python", {"Cybersecurity": 2, "Python": 2, "Cloud": 1, "Problem Solving": 3}),
            ("kavya@skillbridge.demo", "Riverdale Institute of Technology", "Computer Science", 4, "Cloud Engineer", "Learning to design reliable cloud systems.", "cloud, automation, git", {"Cloud": 3, "Python": 2, "Git": 3}),
        ]
        user_by_email = {user.email: user for user in demo_users}
        for email, college, department, year, goal, bio, interests, levels in student_data:
            student = Student(user_id=user_by_email[email].id, college=college, department=department, year=year, career_goal=goal, bio=bio, interests=interests)
            db.add(student)
            db.flush()
            students.append(student)
            for skill_name, level in levels.items():
                db.add(StudentSkill(student_id=student.id, skill_id=skills[skill_name].id, proficiency=level, verification_status="IN PROGRESS"))

        industry_specs = [
            ("industry@skillbridge.demo", "Northstar Analytics", "Data & AI", "Analytics products for growing businesses."),
            ("greengrid@skillbridge.demo", "GreenGrid Labs", "Climate Technology", "Data products supporting a cleaner energy transition."),
            ("brightpath@skillbridge.demo", "BrightPath Digital", "Software", "Digital services and workforce technology."),
        ]
        industries = {}
        for email, name, kind, description in industry_specs:
            industry = Industry(user_id=user_by_email[email].id, company_name=name, industry_type=kind, description=description)
            db.add(industry)
            db.flush()
            industries[name] = industry

        for email, expertise, company, years in [
            ("mentor@skillbridge.demo", "Data analytics, SQL, Power BI", "Northstar Analytics", 8),
            ("dev@skillbridge.demo", "Full-stack engineering, APIs", "BrightPath Digital", 7),
            ("leena@skillbridge.demo", "Machine learning, cloud", "GreenGrid Labs", 9),
        ]:
            db.add(Mentor(user_id=user_by_email[email].id, expertise=expertise, company=company, experience=years))

        db.add(Institution(user_id=user_by_email["institution@skillbridge.demo"].id, institution_name="Riverdale Institute of Technology", location="Bengaluru"))
        db.add(Institution(user_id=user_by_email["ntc@skillbridge.demo"].id, institution_name="National Tech College", location="Pune"))

        project_specs = [
            ("Customer Churn Analysis", "Analyze subscription behavior and build an explainable churn dashboard.", "Data Analytics", "Intermediate", "Python, SQL, Power BI, Statistics", "A validated churn model and decision-ready dashboard."),
            ("Retail Demand Forecasting", "Explore sales seasonality and forecast demand for a retail dataset.", "Data Analytics", "Intermediate", "Python, SQL, Statistics", "Forecast notebook and business summary."),
            ("Energy Usage Insights", "Turn smart-meter readings into an interactive sustainability dashboard.", "Climate Tech", "Beginner", "SQL, Power BI, Data Visualization", "A clear dashboard with actionable energy insights."),
            ("Student Success Explorer", "Identify patterns in anonymized learner engagement data.", "Education", "Beginner", "Excel, Statistics, Data Visualization", "A concise analysis and visualization pack."),
            ("Support Ticket Classifier", "Prototype a text classification workflow for customer support requests.", "AI", "Advanced", "Python, Machine Learning, SQL", "A reproducible model evaluation and demo."),
            ("Secure API Review", "Review a sample service design and document security improvements.", "Security", "Intermediate", "Cybersecurity, Python, API Design", "A threat-informed review and remediation plan."),
            ("Cloud Cost Monitor", "Design a lightweight cloud usage reporting pipeline.", "Cloud", "Intermediate", "Cloud, Python, SQL", "A working report and architecture note."),
            ("Accessible Learning Portal", "Prototype an accessible course discovery experience.", "Software", "Intermediate", "React, JavaScript, API Design", "An accessible, responsive web application."),
        ]
        for index, (title, description, domain, difficulty, required, outcome) in enumerate(project_specs):
            company = ("Northstar Analytics", "GreenGrid Labs", "BrightPath Digital")[index % 3]
            db.add(Project(industry_id=industries[company].id, title=title, description=description, domain=domain, difficulty=difficulty, required_skills=required, expected_outcome=outcome, evaluation_criteria="Technical quality, reasoning, communication and evidence.", deadline="2026-12-15", status="OPEN"))

        course_specs = [
            ("Python for Data Analysis", "Explore data structures, notebooks and practical analysis.", "Python", "Beginner", "3 weeks"),
            ("SQL Fundamentals", "Query, join and summarize relational datasets.", "SQL", "Beginner", "2 weeks"),
            ("Statistics for Decision Making", "Use distributions, sampling and inference in context.", "Statistics", "Intermediate", "3 weeks"),
            ("Power BI Essentials", "Build data models, measures and interactive reports.", "Power BI", "Beginner", "2 weeks"),
            ("Data Visualization Principles", "Choose and communicate effective visual encodings.", "Data Visualization", "Beginner", "2 weeks"),
            ("Excel for Analysts", "Use formulas, pivots and clean workflows for analysis.", "Excel", "Beginner", "2 weeks"),
            ("Problem Solving with Python", "Break open-ended problems into testable steps.", "Problem Solving", "Intermediate", "2 weeks"),
            ("Machine Learning Foundations", "Train and evaluate baseline predictive models.", "Machine Learning", "Intermediate", "4 weeks"),
            ("Cloud Fundamentals", "Understand core cloud services and deployment basics.", "Cloud", "Beginner", "3 weeks"),
            ("Cybersecurity Essentials", "Practice threat awareness and security principles.", "Cybersecurity", "Beginner", "3 weeks"),
            ("Modern JavaScript", "Build practical browser and server-side applications.", "JavaScript", "Beginner", "3 weeks"),
            ("React Application Development", "Compose interactive components and data-driven views.", "React", "Intermediate", "4 weeks"),
        ]
        for title, description, skill_name, difficulty, duration in course_specs:
            db.add(Course(title=title, description=description, skill_id=skills[skill_name].id, difficulty=difficulty, duration=duration))

        opportunity_specs = [
            ("Data Analyst Internship", "Internship", "Support customer analytics and reporting.", "Python, SQL, Statistics, Power BI", "Bengaluru"),
            ("Junior BI Apprentice", "Apprenticeship", "Build clear dashboards for operations teams.", "Power BI, Excel, SQL", "Remote"),
            ("Product Analytics Project Fellow", "Industry Project", "Investigate product engagement and retention.", "SQL, Python, Data Visualization", "Remote"),
            ("ML Engineering Intern", "Internship", "Experiment with applied prediction systems.", "Python, Machine Learning, Statistics", "Pune"),
            ("Security Operations Trainee", "Apprenticeship", "Help improve monitoring and incident workflows.", "Cybersecurity, Python, Cloud", "Hyderabad"),
            ("Cloud Support Associate", "Entry-level role", "Support deployment and reliability initiatives.", "Cloud, Python, Git", "Remote"),
            ("Frontend Developer Intern", "Internship", "Build accessible web experiences with a product team.", "React, JavaScript, API Design", "Mumbai"),
            ("Sustainability Data Fellow", "Industry Project", "Turn energy data into actionable insights.", "SQL, Power BI, Statistics", "Remote"),
        ]
        for index, (title, kind, description, required, location) in enumerate(opportunity_specs):
            company = ("Northstar Analytics", "GreenGrid Labs", "BrightPath Digital")[index % 3]
            db.add(Opportunity(industry_id=industries[company].id, title=title, type=kind, description=description, required_skills=required, location=location, eligibility="Students and recent graduates"))

        db.add(Certification(student_id=students[0].id, name="Python for Data Analysis", issuer="SkillBridge Learning", date="2026-04"))
        db.flush()
        arun = students[0]
        roadmap = Roadmap(student_id=arun.id, career_role_id=roles["Data Analyst"].id)
        db.add(roadmap)
        db.flush()
        for week, skill_name in enumerate(("SQL", "Power BI", "Data Visualization"), 1):
            db.add(RoadmapTask(roadmap_id=roadmap.id, week=week, title=f"{skill_name} learning sprint", type="LEARN", skill_id=skills[skill_name].id, description=f"Study core concepts and complete a hands-on {skill_name} challenge."))
        db.add(RoadmapTask(roadmap_id=roadmap.id, week=4, title="Customer Churn Analysis", type="PROJECT", description="Apply your data skills to an industry-reviewed project."))
        ensure_assessment_bank(db)
        db.commit()
        print("Database seeded. Demo accounts:")
        print("  student@skillbridge.demo / Student@123")
        print("  industry@skillbridge.demo / Industry@123")
        print("  mentor@skillbridge.demo / Mentor@123")
        print("  institution@skillbridge.demo / Institution@123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
