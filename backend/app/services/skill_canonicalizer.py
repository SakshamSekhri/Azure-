import re
from typing import Dict, List, Optional, NamedTuple


class CanonicalSkill(NamedTuple):
    canonical_id: str
    display_name: str
    category: str
    aliases: List[str]


# Authoritative catalog of known skills, aliases, and categories
_CANONICAL_CATALOG: List[CanonicalSkill] = [
    # Languages
    CanonicalSkill("python", "Python", "Programming", ["python", "python3", "py", "cpython"]),
    CanonicalSkill("javascript", "JavaScript", "Programming", ["javascript", "js", "ecmascript", "es6", "vanilla js"]),
    CanonicalSkill("typescript", "TypeScript", "Programming", ["typescript", "ts"]),
    CanonicalSkill("java", "Java", "Programming", ["java", "core java", "java 8", "java 11", "java 17", "java 21"]),
    CanonicalSkill("cpp", "C++", "Programming", ["c++", "cpp", "cplusplus", "c/c++"]),
    CanonicalSkill("csharp", "C#", "Programming", ["c#", "csharp", "c-sharp", ".net c#"]),
    CanonicalSkill("golang", "Go", "Programming", ["golang", "go"]),
    CanonicalSkill("rust", "Rust", "Programming", ["rust", "rustlang"]),
    CanonicalSkill("ruby", "Ruby", "Programming", ["ruby", "ruby on rails"]),
    CanonicalSkill("php", "PHP", "Programming", ["php", "php7", "php8"]),
    CanonicalSkill("sql", "SQL", "Database", ["sql", "structured query language", "ansi sql"]),

    # Frameworks / Libraries
    CanonicalSkill("fastapi", "FastAPI", "Framework", ["fastapi", "fast-api", "fast api"]),
    CanonicalSkill("flask", "Flask", "Framework", ["flask"]),
    CanonicalSkill("django", "Django", "Framework", ["django", "django rest framework", "drf"]),
    CanonicalSkill("react", "React", "Frontend", ["react", "react.js", "reactjs", "react-js"]),
    CanonicalSkill("angular", "Angular", "Frontend", ["angular", "angularjs", "angular.js", "angular 2+"]),
    CanonicalSkill("vue", "Vue.js", "Frontend", ["vue", "vue.js", "vuejs", "vue3"]),
    CanonicalSkill("nextjs", "Next.js", "Frontend", ["next.js", "nextjs", "next-js", "next"]),
    CanonicalSkill("nodejs", "Node.js", "Framework", ["node", "node.js", "nodejs", "node-js"]),
    CanonicalSkill("express", "Express.js", "Framework", ["express", "express.js", "expressjs"]),
    CanonicalSkill("springboot", "Spring Boot", "Framework", ["spring boot", "springboot", "spring-boot", "spring framework", "spring"]),
    CanonicalSkill("pytorch", "PyTorch", "AI/ML", ["pytorch", "torch"]),
    CanonicalSkill("tensorflow", "TensorFlow", "AI/ML", ["tensorflow", "tf"]),
    CanonicalSkill("scikit-learn", "Scikit-Learn", "AI/ML", ["scikit-learn", "sklearn", "scikit learn"]),

    # Databases
    CanonicalSkill("postgresql", "PostgreSQL", "Database", ["postgresql", "postgres", "postgre-sql", "psql", "pg"]),
    CanonicalSkill("mysql", "MySQL", "Database", ["mysql", "my-sql"]),
    CanonicalSkill("mongodb", "MongoDB", "Database", ["mongodb", "mongo", "mongo-db"]),
    CanonicalSkill("redis", "Redis", "Database", ["redis"]),
    CanonicalSkill("sqlite", "SQLite", "Database", ["sqlite", "sqlite3"]),
    CanonicalSkill("cassandra", "Cassandra", "Database", ["cassandra", "apache cassandra"]),
    CanonicalSkill("elasticsearch", "Elasticsearch", "Database", ["elasticsearch", "elastic search", "elastic"]),
    CanonicalSkill("dynamodb", "DynamoDB", "Database", ["dynamodb", "dynamo-db", "amazon dynamodb"]),

    # DevOps & Cloud
    CanonicalSkill("docker", "Docker", "DevOps", ["docker", "docker-compose", "containerization"]),
    CanonicalSkill("kubernetes", "Kubernetes", "DevOps", ["kubernetes", "k8s"]),
    CanonicalSkill("aws", "AWS", "Cloud", ["aws", "amazon web services", "amazon aws"]),
    CanonicalSkill("azure", "Azure", "Cloud", ["azure", "microsoft azure", "azure cloud"]),
    CanonicalSkill("gcp", "GCP", "Cloud", ["gcp", "google cloud", "google cloud platform"]),
    CanonicalSkill("git", "Git", "Tools", ["git", "github", "gitlab", "version control"]),
    CanonicalSkill("cicd", "CI/CD", "DevOps", ["ci/cd", "cicd", "ci cd", "continuous integration", "github actions", "jenkins"]),
    CanonicalSkill("linux", "Linux", "DevOps", ["linux", "unix", "bash", "shell scripting", "ubuntu"]),

    # CS Fundamentals & System Design
    CanonicalSkill("system-design", "System Design", "CS Fundamentals", ["system design", "distributed systems", "software architecture", "high level design", "low level design", "hld", "lld"]),
    CanonicalSkill("data-structures", "Data Structures", "CS Fundamentals", ["data structures", "dsa", "data structures & algorithms", "algorithms", "algo"]),
    CanonicalSkill("rest-api", "REST APIs", "CS Fundamentals", ["rest api", "rest apis", "restful", "restful apis", "api design"]),
    CanonicalSkill("microservices", "Microservices", "CS Fundamentals", ["microservices", "microservice architecture", "micro-services"]),
    CanonicalSkill("concurrency", "Concurrency", "CS Fundamentals", ["concurrency", "multithreading", "async", "asyncio", "parallelism"]),
    CanonicalSkill("machine-learning", "Machine Learning", "AI/ML", ["machine learning", "ml", "machine-learning", "deep learning", "deep-learning", "dl"]),
    CanonicalSkill("oop", "Object-Oriented Programming", "CS Fundamentals", ["oop", "object oriented programming", "object-oriented programming", "oops"]),
    CanonicalSkill("graphql", "GraphQL", "API", ["graphql", "graph-ql"]),
    CanonicalSkill("seo-sem", "SEO / SEM", "Marketing & Growth", ["seo", "sem", "seo / sem", "seo/sem", "search engine optimization", "search engine marketing"])
]

# Fast alias lookup index
_ALIAS_INDEX: Dict[str, CanonicalSkill] = {}
for item in _CANONICAL_CATALOG:
    _ALIAS_INDEX[item.canonical_id] = item
    _ALIAS_INDEX[item.display_name.lower()] = item
    _ALIAS_INDEX[re.sub(r"[\s\.\-_]", "", item.display_name.lower())] = item
    _ALIAS_INDEX[re.sub(r"[\s\.\-_]", "", item.canonical_id)] = item
    for alias in item.aliases:
        a_clean = alias.strip().lower()
        _ALIAS_INDEX[a_clean] = item
        _ALIAS_INDEX[re.sub(r"[\s\.\-_]", "", a_clean)] = item


def _clean_string(s: str) -> str:
    """Normalize raw string by removing non-alphanumeric punctuation (except +, #, -)."""
    normalized = s.strip().lower()
    # Normalize common patterns
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def canonicalize_skill(raw_name: str, category_hint: Optional[str] = None) -> CanonicalSkill:
    """Deterministically map any raw skill name to a canonical skill record.
    Never relies only on raw string equality.
    """
    if not raw_name or not raw_name.strip():
        return CanonicalSkill(
            canonical_id="unknown",
            display_name="Unknown",
            category=category_hint or "General",
            aliases=[]
        )

    cleaned = _clean_string(raw_name)

    # 1. Exact alias match
    if cleaned in _ALIAS_INDEX:
        return _ALIAS_INDEX[cleaned]

    # 2. Stripped space/dot/dash match (e.g. "react.js" -> "reactjs", "node js" -> "nodejs")
    stripped = re.sub(r"[\s\.\-_]", "", cleaned)
    if stripped in _ALIAS_INDEX:
        return _ALIAS_INDEX[stripped]

    # 3. Check without ".js" / " js" suffix if present
    if cleaned.endswith(".js") or cleaned.endswith(" js") or cleaned.endswith("js"):
        without_js = re.sub(r"[\.\s]?js$", "", cleaned).strip()
        if without_js in _ALIAS_INDEX:
            return _ALIAS_INDEX[without_js]
        stripped_without_js = re.sub(r"[\s\.\-_]", "", without_js)
        if stripped_without_js in _ALIAS_INDEX:
            return _ALIAS_INDEX[stripped_without_js]

    # 4. Fallback slugifier for unknown/new technologies
    slug = re.sub(r"[^a-z0-9+#\-]+", "-", cleaned).strip("-")
    if not slug:
        slug = "skill"

    # Derive clean display name: Capitalize words
    words = raw_name.strip().split()
    display_name = " ".join(w.capitalize() if not w.isupper() else w for w in words)

    return CanonicalSkill(
        canonical_id=slug,
        display_name=display_name,
        category=category_hint or "Technical",
        aliases=[cleaned]
    )
