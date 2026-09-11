"""Pure MDX rendering with the established CV export behavior."""

from app.schemas.cv import CVExportRequest, CVProfile


def render_mdx(cv_profile: CVProfile, request: CVExportRequest) -> str:
    """Generate MDX content from CV profile."""
    mdx_lines = []

    # Header
    mdx_lines.append(
        f"# {cv_profile.personal_info.first_name} {cv_profile.personal_info.last_name}"
    )
    mdx_lines.append("")
    mdx_lines.append(f"**{cv_profile.personal_info.summary}**")
    mdx_lines.append("")

    # Contact Information
    mdx_lines.append("## Contact Information")
    mdx_lines.append(f"- **Email:** {cv_profile.personal_info.email}")
    mdx_lines.append(f"- **Location:** {cv_profile.personal_info.location}")
    mdx_lines.append(
        f"- **LinkedIn:** [{cv_profile.personal_info.linkedin_url}]({cv_profile.personal_info.linkedin_url})"
    )
    if cv_profile.personal_info.github_url:
        mdx_lines.append(
            f"- **GitHub:** [{cv_profile.personal_info.github_url}]({cv_profile.personal_info.github_url})"
        )
    if cv_profile.personal_info.website_url:
        mdx_lines.append(
            f"- **Website:** [{cv_profile.personal_info.website_url}]({cv_profile.personal_info.website_url})"
        )
    mdx_lines.append("")

    # Professional Summary
    mdx_lines.append("## Professional Summary")
    mdx_lines.append(cv_profile.personal_info.summary)
    mdx_lines.append("")

    # Work Experience
    if cv_profile.experience:
        mdx_lines.append("## Work Experience")
        mdx_lines.append("")

        for exp in cv_profile.experience:
            mdx_lines.append(f"### {exp.position}")
            mdx_lines.append(f"**{exp.company}** | {exp.location}")
            mdx_lines.append(
                f"*{exp.start_date.strftime('%B %Y')} - {exp.end_date.strftime('%B %Y') if exp.end_date else 'Present'}*"
            )
            mdx_lines.append("")
            mdx_lines.append(exp.description)
            mdx_lines.append("")

            if request.include_achievements and exp.achievements:
                mdx_lines.append("**Key Achievements:**")
                for achievement in exp.achievements:
                    mdx_lines.append(f"- {achievement}")
                mdx_lines.append("")

            if request.include_technologies and exp.technologies:
                mdx_lines.append("**Technologies:**")
                for tech in exp.technologies:
                    mdx_lines.append(f"- {tech}")
                mdx_lines.append("")

    # Education
    if cv_profile.education:
        mdx_lines.append("## Education")
        mdx_lines.append("")

        for edu in cv_profile.education:
            mdx_lines.append(f"### {edu.degree}")
            mdx_lines.append(f"**{edu.institution}** | {edu.field_of_study}")
            mdx_lines.append(
                f"*{edu.start_date.strftime('%B %Y')} - {edu.end_date.strftime('%B %Y') if edu.end_date else 'Present'}*"
            )
            if edu.gpa:
                mdx_lines.append(f"**GPA:** {edu.gpa}")
            if edu.honors:
                mdx_lines.append(f"**Honors:** {edu.honors}")
            if edu.description:
                mdx_lines.append(edu.description)
            mdx_lines.append("")

    # Skills
    if cv_profile.skills:
        mdx_lines.append("## Skills")
        mdx_lines.append("")

        # Programming Languages
        if cv_profile.skills.programming_languages:
            mdx_lines.append("### Programming Languages")
            for skill in cv_profile.skills.programming_languages:
                level_text = f" ({skill.level.value})" if request.include_scores else ""
                mdx_lines.append(f"- {skill.name}{level_text}")
            mdx_lines.append("")

        # Machine Learning
        if cv_profile.skills.machine_learning:
            mdx_lines.append("### Machine Learning & AI")
            for skill in cv_profile.skills.machine_learning:
                level_text = f" ({skill.level.value})" if request.include_scores else ""
                mdx_lines.append(f"- {skill.name}{level_text}")
            mdx_lines.append("")

        # Other skill categories
        other_categories = [
            ("frameworks_libraries", "Frameworks & Libraries"),
            ("databases", "Databases"),
            ("cloud_platforms", "Cloud Platforms"),
            ("devops_tools", "DevOps & Tools"),
            ("mathematical", "Mathematical Skills"),
            ("soft_skills", "Soft Skills"),
        ]

        for category, title in other_categories:
            skills = getattr(cv_profile.skills, category, [])
            if skills:
                mdx_lines.append(f"### {title}")
                for skill in skills:
                    level_text = (
                        f" ({skill.level.value})" if request.include_scores else ""
                    )
                    mdx_lines.append(f"- {skill.name}{level_text}")
                mdx_lines.append("")

    # Certifications
    if cv_profile.certifications:
        mdx_lines.append("## Certifications")
        mdx_lines.append("")

        for cert in cv_profile.certifications:
            mdx_lines.append(f"### {cert.name}")
            mdx_lines.append(f"**{cert.issuing_organization}**")
            mdx_lines.append(f"*Issued: {cert.issue_date.strftime('%B %Y')}*")
            if cert.expiry_date:
                mdx_lines.append(f"*Expires: {cert.expiry_date.strftime('%B %Y')}*")
            if cert.description:
                mdx_lines.append(cert.description)
            mdx_lines.append("")

    # Languages
    if cv_profile.languages:
        mdx_lines.append("## Languages")
        mdx_lines.append("")

        for lang in cv_profile.languages:
            mdx_lines.append(f"- **{lang.name}:** {lang.proficiency}")
            if lang.reading and lang.writing and lang.speaking:
                mdx_lines.append(
                    f"  - Reading: {lang.reading}, Writing: {lang.writing}, Speaking: {lang.speaking}"
                )
        mdx_lines.append("")

    # Footer
    mdx_lines.append("---")
    mdx_lines.append(
        f"*Last updated: {cv_profile.last_updated.strftime('%B %d, %Y at %H:%M UTC')}*"
    )
    mdx_lines.append(f"*Version: {cv_profile.version}*")

    return "\n".join(mdx_lines)
