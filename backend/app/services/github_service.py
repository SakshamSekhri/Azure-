import httpx
import base64
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone

from backend.app.config.settings import settings
from backend.app.models.profile import StudentProfile
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.evidence import Evidence
from backend.app.schemas.github import GitHubAnalysisResponse, GitHubRepoInfo
from backend.app.core.logging import logger


class GitHubService:
    @staticmethod
    def analyze_user_github(
        db: Session,
        user_id: int,
        username: str
    ) -> GitHubAnalysisResponse:
        username = username.strip().lstrip("@")
        if not username:
            raise HTTPException(status_code=400, detail="GitHub username is required.")

        # Update profile
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        if profile:
            profile.github_username = username
            db.commit()

        # Fetch repos bounded
        repos_data = GitHubService._fetch_public_repos(username)

        # Collect detected languages and skills
        detected_languages: Dict[str, int] = {}
        detected_frameworks: List[str] = []
        parsed_repos: List[GitHubRepoInfo] = []
        evidence_created_count = 0

        framework_keywords = {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "react": "React",
            "next": "Next.js",
            "express": "Node.js",
            "spring": "Spring Boot",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "postgres": "PostgreSQL",
            "sql": "SQL",
            "redis": "Redis",
            "mongo": "MongoDB"
        }

        for repo in repos_data[:settings.MAX_GITHUB_REPOS]:
            r_name = repo.get("name", "")
            r_desc = repo.get("description") or ""
            r_url = repo.get("html_url", f"https://github.com/{username}/{r_name}")
            lang = repo.get("language")
            topics = repo.get("topics", [])

            if lang:
                detected_languages[lang] = detected_languages.get(lang, 0) + 1

            # Check framework keywords in name, description, and topics
            combined_meta = f"{r_name} {r_desc} {' '.join(topics)}".lower()
            repo_frameworks = []
            for kw, fw_name in framework_keywords.items():
                if kw in combined_meta:
                    if fw_name not in detected_frameworks:
                        detected_frameworks.append(fw_name)
                    if fw_name not in repo_frameworks:
                        repo_frameworks.append(fw_name)

            # Bounded README fetch
            readme_snippet = GitHubService._fetch_readme_snippet(username, r_name)

            repo_info = GitHubRepoInfo(
                name=r_name,
                full_name=repo.get("full_name", f"{username}/{r_name}"),
                description=r_desc,
                html_url=r_url,
                language=lang,
                topics=topics,
                stargazers_count=repo.get("stargazers_count", 0),
                forks_count=repo.get("forks_count", 0),
                updated_at=repo.get("updated_at"),
                has_readme=bool(readme_snippet),
                readme_snippet=readme_snippet
            )
            parsed_repos.append(repo_info)

            # Create or update Evidence record
            # Supporting evidence only!
            existing_ev = db.query(Evidence).filter(
                Evidence.user_id == user_id,
                Evidence.type == "GitHub",
                Evidence.source == f"github.com/{username}/{r_name}"
            ).first()

            if not existing_ev:
                ev = Evidence(
                    user_id=user_id,
                    type="GitHub",
                    source=f"github.com/{username}/{r_name}",
                    title=f"Repository: {r_name}",
                    description=f"{r_desc} (Language: {lang or 'Multiple'})",
                    url=r_url,
                    evidence_strength=0.6,  # Strictly supporting evidence only
                    metadata_json={
                        "language": lang,
                        "topics": topics,
                        "stars": repo.get("stargazers_count", 0),
                        "frameworks": repo_frameworks
                    }
                )
                db.add(ev)
                evidence_created_count += 1

            # Map to Skill & StudentSkill
            skills_to_link = []
            if lang:
                skills_to_link.append((lang, "Programming"))
            for fw in repo_frameworks:
                skills_to_link.append((fw, "Framework"))

            for s_name, s_cat in skills_to_link:
                skill_obj = db.query(Skill).filter(Skill.name.ilike(s_name)).first()
                if not skill_obj:
                    skill_obj = Skill(name=s_name, category=s_cat)
                    db.add(skill_obj)
                    db.commit()
                    db.refresh(skill_obj)

                student_skill = db.query(StudentSkill).filter(
                    StudentSkill.user_id == user_id,
                    StudentSkill.skill_id == skill_obj.id
                ).first()

                if not student_skill:
                    student_skill = StudentSkill(
                        user_id=user_id,
                        skill_id=skill_obj.id,
                        confidence="Low",
                        evidence_count=1
                    )
                    db.add(student_skill)
                    db.flush()
                else:
                    count = db.query(Evidence).filter(
                        Evidence.user_id == user_id,
                        Evidence.type == "GitHub"
                    ).count()
                    student_skill.evidence_count = count

        db.commit()

        top_langs = sorted(detected_languages.keys(), key=lambda k: detected_languages[k], reverse=True)
        detected_all_skills = list(set(top_langs + detected_frameworks))

        summary = (
            f"Analyzed {len(parsed_repos)} public GitHub repositories for @{username}. "
            f"Detected languages: {', '.join(top_langs[:4]) if top_langs else 'N/A'}. "
            f"Identified frameworks/tools: {', '.join(detected_frameworks[:5]) if detected_frameworks else 'None'}. "
            f"Note: Recorded as supporting practical evidence."
        )

        return GitHubAnalysisResponse(
            username=username,
            total_repos_inspected=len(parsed_repos),
            primary_languages=top_langs,
            detected_frameworks=detected_frameworks,
            detected_skills=detected_all_skills,
            evidence_created_count=evidence_created_count,
            repos=parsed_repos,
            summary=summary
        )

    @staticmethod
    def _fetch_public_repos(username: str) -> List[Dict[str, Any]]:
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "PlacementPrepAgent/1.0"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        url = f"https://api.github.com/users/{username}/repos?type=public&sort=updated&per_page={settings.MAX_GITHUB_REPOS}"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    return res.json()
                elif res.status_code == 404:
                    raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found.")
                elif res.status_code == 403:
                    logger.warning("GitHub API rate limited.")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Error calling GitHub API: {e}")

        return []

    @staticmethod
    def _fetch_readme_snippet(username: str, repo_name: str) -> Optional[str]:
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "PlacementPrepAgent/1.0"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    content_b64 = data.get("content", "")
                    decoded = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                    return decoded[:settings.MAX_README_CHARS]
        except Exception:
            pass
        return None
