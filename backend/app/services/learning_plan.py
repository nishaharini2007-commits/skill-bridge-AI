from math import ceil
from urllib.parse import quote_plus
from urllib.parse import urlparse


SKILL_GUIDANCE = {
    "python": {
        "why": "Python is widely used to explore data, automate work, and build role-specific tools.",
        "prerequisites": [],
        "official": ("Python tutorial", "Python documentation", "https://docs.python.org/3/tutorial/"),
    },
    "sql": {
        "why": "SQL helps you retrieve, join, and summarize information stored in relational databases.",
        "prerequisites": [],
        "official": ("SQL tutorial", "PostgreSQL documentation", "https://www.postgresql.org/docs/current/tutorial.html"),
    },
    "statistics": {
        "why": "Statistics helps you reason about samples, uncertainty, and whether observed patterns are meaningful.",
        "prerequisites": [],
        "official": ("Introductory statistics", "OpenStax", "https://openstax.org/details/books/introductory-statistics-2e"),
    },
    "numpy": {
        "why": "NumPy provides the array and numerical operations used throughout scientific Python.",
        "prerequisites": ["Python"],
        "official": ("NumPy for beginners", "NumPy documentation", "https://numpy.org/doc/stable/user/absolute_beginners.html"),
    },
    "pandas": {
        "why": "Pandas makes it practical to clean, transform, and analyze tabular data in Python.",
        "prerequisites": ["Python"],
        "official": ("Getting started tutorials", "Pandas documentation", "https://pandas.pydata.org/docs/getting_started/intro_tutorials/index.html"),
    },
    "machine learning": {
        "why": "Machine learning develops predictive models from data and requires careful evaluation.",
        "prerequisites": ["Python", "Statistics"],
        "official": ("Getting started", "scikit-learn documentation", "https://scikit-learn.org/stable/getting_started.html"),
    },
    "react": {
        "why": "React is used to build component-based interactive interfaces for web applications.",
        "prerequisites": ["JavaScript"],
        "official": ("Learn React", "React documentation", "https://react.dev/learn"),
    },
    "javascript": {
        "why": "JavaScript powers interactive web interfaces and a broad range of application runtimes.",
        "prerequisites": [],
        "official": ("JavaScript guide", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"),
    },
    "power bi": {
        "why": "Power BI helps you model data and communicate findings through interactive reports.",
        "prerequisites": ["SQL", "Statistics"],
        "official": ("Power BI learning paths", "Microsoft Learn", "https://learn.microsoft.com/en-us/training/powerplatform/power-bi/"),
    },
    "data visualization": {
        "why": "Data visualization makes patterns and conclusions easier to inspect and communicate.",
        "prerequisites": ["Statistics"],
        "official": ("Tutorials", "Matplotlib documentation", "https://matplotlib.org/stable/tutorials/index.html"),
    },
    "excel": {
        "why": "Excel remains a practical tool for organizing, validating, and summarizing business data.",
        "prerequisites": [],
        "official": ("Excel help and learning", "Microsoft Support", "https://support.microsoft.com/en-us/excel"),
    },
    "git": {
        "why": "Git records changes and makes project work easier to review, reproduce, and share.",
        "prerequisites": [],
        "official": ("GitHub Skills", "GitHub Skills", "https://learn.github.com/skills"),
    },
    "data structures and algorithms": {
        "why": "Data structures and algorithms help you choose clear, efficient approaches to programming problems.",
        "prerequisites": ["Programming fundamentals"],
        "official": ("Algorithms and data structures", "GeeksforGeeks", "https://www.geeksforgeeks.org/dsa/dsa-tutorial-learn-data-structures-and-algorithms/"),
    },
    "model evaluation": {
        "why": "Model evaluation checks whether predictions generalize and whether a metric fits the real problem.",
        "prerequisites": ["Statistics", "Machine Learning"],
        "official": ("Model evaluation", "scikit-learn documentation", "https://scikit-learn.org/stable/modules/model_evaluation.html"),
    },
}

LEVEL_LABELS = {
    0: "Not learned",
    1: "Beginner",
    2: "Beginner",
    3: "Intermediate",
    4: "Advanced",
    5: "Advanced",
}


def normalize_level(level: int) -> int:
    return max(0, min(5, int(level)))


def level_label(level: int) -> str:
    return LEVEL_LABELS[normalize_level(level)]


def gap_status(required: int, current: int) -> str:
    difference = max(0, normalize_level(required) - normalize_level(current))
    if difference == 0:
        return "Strong"
    if difference == 1:
        return "Developing"
    return "Needs Learning"


def readiness_score(skills: list[dict]) -> int | None:
    if not skills:
        return None
    ratios = [min(item["current"] / item["required"], 1) if item["required"] else 1 for item in skills]
    return round(sum(ratios) / len(ratios) * 100)


def skill_guidance(skill_name: str) -> dict:
    key = skill_name.strip().lower()
    return SKILL_GUIDANCE.get(key, {
        "why": f"{skill_name} is part of the selected role's configurable requirements.",
        "prerequisites": [],
        "official": (f"Search for {skill_name} documentation", "Documentation search", f"https://www.google.com/search?q={quote_plus(skill_name + ' official documentation')}"),
    })


def learning_resources(skill_name: str, current_level: int, language: str = "English", learning_format: str = "Mixed") -> list[dict]:
    guidance = skill_guidance(skill_name)
    query = quote_plus(f"{skill_name} {level_label(current_level)} tutorial {language}")
    difficulty = "Beginner" if current_level < 3 else "Intermediate"
    resources = [
        {
            "category": "Video tutorial",
            "title": f"{skill_name} {difficulty.lower()} tutorials",
            "platform": "YouTube",
            "topic": skill_name,
            "difficulty": difficulty,
            "url": f"https://www.youtube.com/results?search_query={query}",
            "link_type": "Platform search",
        },
        {
            "category": "Tutorial and practice",
            "title": f"{skill_name} tutorials and practice",
            "platform": "GeeksforGeeks",
            "topic": skill_name,
            "difficulty": difficulty,
            "url": f"https://www.geeksforgeeks.org/?s={quote_plus(skill_name)}",
            "link_type": "Platform search",
        },
        {
            "category": "Course search",
            "title": f"{skill_name} courses",
            "platform": "Coursera",
            "topic": skill_name,
            "difficulty": difficulty,
            "url": f"https://www.coursera.org/search?query={quote_plus(skill_name)}",
            "link_type": "Platform search",
        },
        {
            "category": "Official documentation" if guidance["official"][1] != "Documentation search" else "Documentation search",
            "title": guidance["official"][0],
            "platform": guidance["official"][1],
            "topic": skill_name,
            "difficulty": "Reference",
            "url": guidance["official"][2],
            "link_type": (
                "Search results" if guidance["official"][1] == "Documentation search"
                else "Learning reference" if guidance["official"][1] == "GeeksforGeeks"
                else "Official reference"
            ),
        },
        {
            "category": "Project-based learning",
            "title": f"{skill_name} project ideas",
            "platform": "GitHub",
            "topic": skill_name,
            "difficulty": difficulty,
            "url": f"https://github.com/search?q={quote_plus(skill_name + ' beginner project')}&type=repositories",
            "link_type": "Platform search",
        },
    ]
    if learning_format == "Interactive":
        resources.insert(1, {
            "category": "Interactive tutorial",
            "title": f"Interactive {skill_name} lessons",
            "platform": "freeCodeCamp",
            "topic": skill_name,
            "difficulty": difficulty,
            "url": f"https://www.freecodecamp.org/news/search/?query={quote_plus(skill_name)}",
            "link_type": "Platform search",
        })
    return [resource for resource in resources if valid_resource_url(resource["url"])]


def valid_resource_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def estimate_study_days(tasks: list[dict], minutes_per_day: int) -> int | None:
    if minutes_per_day <= 0:
        return None
    total_minutes = sum(max(0, int(task.get("estimated_minutes", 0))) for task in tasks)
    return ceil(total_minutes / minutes_per_day) if total_minutes else 0


def generate_task_specs(role_name: str, gaps: list[dict], language: str, learning_format: str) -> list[dict]:
    weak = [item for item in gaps if item["gap"] > 0]
    if not weak:
        focus = gaps[:1]
        explanation = "Your current profile meets the configured role requirements. Revisit this topic periodically and keep evidence of applied work."
    else:
        focus = weak
        explanation = "A completed task records learning activity only; update your proficiency separately when you have evidence of what you can do."

    tasks = []
    order = 1
    if focus:
        foundational = focus[-1]
        tasks.append(_task(
            order, 1, "Foundations", foundational, language, learning_format,
            "Build or refresh the prerequisite concepts that make later role skills easier to learn.",
            180, explanation, "Try a short concept check and explain one example in your own words.",
            "Create a one-page concept note or a small reproducible notebook.",
        ))
        order += 1

    core_items = sorted(focus, key=lambda item: (-item["priority_score"], item["skill"]))[:4]
    for item in core_items:
        tasks.append(_task(
            order, 2, "Core technical skills", item, language, learning_format,
            item["why_it_matters"], 240, explanation,
            f"Complete a small set of {item['skill']} exercises and record what was difficult.",
            f"Build a small {item['skill']} exercise using a public or self-created dataset.",
        ))
        order += 1

    advanced = next((item for item in core_items if item["required"] >= 4), None)
    if advanced:
        tasks.append(_task(
            order, 3, "Advanced and role-specific skills", advanced, language, learning_format,
            f"Extend your {advanced['skill']} knowledge toward the level configured for {role_name}.",
            300, explanation,
            f"Compare two approaches to a {advanced['skill']} task and note their trade-offs.",
            f"Extend your {advanced['skill']} exercise with a realistic edge case.",
        ))
        order += 1

    project_skill = core_items[0] if core_items else (gaps[0] if gaps else None)
    project_task = _task(
        order, 4, "Projects and practical application", project_skill, language, learning_format,
        f"Apply multiple role skills in a small project relevant to {role_name}.",
        360, "Project completion is evidence of practice, not automatic independent verification of proficiency.",
        "Write down the problem, your approach, and one limitation of the result.",
        f"Build a portfolio-ready {role_name} mini-project and document your decisions.",
    )
    project_task["skill"] = None
    project_task["prerequisites"] = [item["skill"] for item in core_items[:3]]
    tasks.append(project_task)
    order += 1

    interview_task = _task(
        order, 5, "Interview preparation and revision", project_skill, language, learning_format,
        "Practice explaining your approach, review fundamentals, and identify the next skill to strengthen.",
        120, "Interview preparation is practice and does not predict hiring or placement outcomes.",
        "Answer a role-related question aloud and review the explanation for clarity.",
        f"Prepare a short walkthrough of your {role_name} project, including trade-offs and lessons.",
    )
    interview_task["skill"] = None
    interview_task["prerequisites"] = ["Complete or review one practical project task"]
    tasks.append(interview_task)
    return tasks


def _task(order: int, phase: int, phase_name: str, item: dict | None, language: str, learning_format: str, why: str, minutes: int, explanation: str, practice: str, mini_project: str) -> dict:
    skill_name = item["skill"] if item else "Career preparation"
    current = item["current"] if item else 0
    guidance = skill_guidance(skill_name)
    prerequisites = list(guidance["prerequisites"])
    if item:
        known_prerequisites = {entry["skill"].lower() for entry in item.get("known_skills", [])}
        prerequisites = [prerequisite for prerequisite in prerequisites if prerequisite.lower() not in known_prerequisites]
    return {
        "order": order,
        "phase": phase,
        "phase_name": phase_name,
        "skill": skill_name if item else None,
        "title": f"{skill_name} learning activity" if item else mini_project,
        "why": why,
        "explanation": explanation,
        "prerequisites": prerequisites,
        "estimated_minutes": minutes,
        "resources": learning_resources(skill_name, current, language, learning_format) if item else [],
        "practice": practice,
        "mini_project": mini_project,
        "status": "Not Started",
    }
