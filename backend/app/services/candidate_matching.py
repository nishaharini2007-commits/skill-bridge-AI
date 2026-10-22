def match_candidate(
    requirements: dict[str, int],
    student_skills: list[dict],
    assessed_skills: dict[str, int],
    verified_project_skills: set[str],
) -> dict:
    skill_levels = {item["name"].casefold(): item["proficiency"] for item in student_skills}
    evidence_by_skill = {
        item["name"].casefold(): item["verification_status"]
        for item in student_skills
    }
    matched = []
    needs_improvement = []
    details = []
    for name, required in requirements.items():
        key = name.casefold()
        current = max(skill_levels.get(key, 0), assessed_skills.get(key, 0))
        is_match = current >= required
        (matched if is_match else needs_improvement).append(name)
        evidence = []
        if key in assessed_skills:
            evidence.append("Completed assessment")
        if key in verified_project_skills or evidence_by_skill.get(key) == "VERIFIED":
            evidence.append("Verified project evidence")
        if current and not evidence:
            evidence.append("Profile skill level")
        details.append({
            "skill": name,
            "required_level": required,
            "current_level": current,
            "matched": is_match,
            "evidence": evidence,
        })
    percentage = round(len(matched) / len(requirements) * 100) if requirements else 0
    if not requirements:
        explanation = "No skill requirements were provided; review the candidate's profile directly."
    elif matched and needs_improvement:
        explanation = (
            f"{len(matched)} of {len(requirements)} listed skills meet the stated levels. "
            f"Consider strengthening: {', '.join(needs_improvement)}."
        )
    elif matched:
        explanation = f"All {len(requirements)} listed skills meet the stated levels."
    else:
        explanation = (
            f"None of the {len(requirements)} listed skills currently meet the stated levels. "
            "This is informational and does not prevent an application or company review."
        )
    return {
        "match_percent": percentage,
        "matched_skills": matched,
        "skills_to_improve": needs_improvement,
        "skill_details": details,
        "explanation": explanation,
        "decision_note": "Match information is advisory only. Companies make all shortlisting and hiring decisions.",
    }
