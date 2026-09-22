"""Curated Educational Knowledge Base for Grounded RAG.
Used to index into Azure AI Search and as a local deterministic knowledge base.
"""

EDUCATIONAL_DOCUMENTS = [
    {
        "id": "doc_sql_indexing",
        "title": "SQL Indexing Strategies and B-Tree Performance",
        "topic": "Databases",
        "skill": "SQL",
        "source": "Placement Prep Knowledge Base - DB Internals",
        "url": "https://use-the-index-luke.com/",
        "content": (
            "A database index is a data structure (commonly a B-Tree or B+ Tree) that enhances data retrieval "
            "speed on a database table at the cost of additional storage and slower write performance (INSERT, UPDATE, DELETE). "
            "Clustered indexes determine the physical order of data in the table, meaning there can only be one clustered index per table. "
            "Non-clustered indexes contain pointers to the physical rows. Compound (composite) indexes must respect the leftmost prefix rule: "
            "queries filtering on leading columns can leverage the index, while queries omitting the leading column typically perform full table scans."
        )
    },
    {
        "id": "doc_sql_transactions",
        "title": "ACID Properties and Isolation Levels in Relational Databases",
        "topic": "Databases",
        "skill": "SQL",
        "source": "Placement Prep Knowledge Base - DB Internals",
        "url": "https://en.wikipedia.org/wiki/ACID",
        "content": (
            "Relational transactions are governed by ACID: Atomicity (all-or-nothing execution), Consistency (schema integrity rules enforced), "
            "Isolation (concurrent transactions execute independently), and Durability (committed data survives system crashes). "
            "Standard SQL isolation levels from weakest to strongest are: Read Uncommitted (dirty reads possible), Read Committed (prevents dirty reads, allows non-repeatable reads), "
            "Repeatable Read (prevents non-repeatable reads, may allow phantom reads), and Serializable (strict sequential execution, highest locking overhead)."
        )
    },
    {
        "id": "doc_fastapi_di",
        "title": "FastAPI Dependency Injection and Request Lifecycles",
        "topic": "Backend Frameworks",
        "skill": "FastAPI",
        "source": "Placement Prep Knowledge Base - Python Web Architecture",
        "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
        "content": (
            "FastAPI features a hierarchical Dependency Injection (DI) system powered by Python's `Depends` function. "
            "Dependencies allow developers to declare reusable logic for database session management, authentication, role verification, "
            "and configuration loading. FastAPI automatically resolves sub-dependencies in an acyclic graph, caches yields within the scope "
            "of a single HTTP request, and executes cleanup blocks (`finally` or generator exit) when the response is returned to the client."
        )
    },
    {
        "id": "doc_fastapi_async",
        "title": "Asynchronous Concurrency vs Multithreading in Python & FastAPI",
        "topic": "Backend Frameworks",
        "skill": "FastAPI",
        "source": "Placement Prep Knowledge Base - Python Web Architecture",
        "url": "https://fastapi.tiangolo.com/async/",
        "content": (
            "FastAPI uses Starlette and asyncio under the hood. Defining route handlers with `async def` allows Python's single-threaded "
            "event loop to switch execution contexts during I/O wait states (such as database queries or external API calls via httpx). "
            "If a CPU-bound or blocking synchronous operation is executed inside an `async def` handler without offloading, it blocks the entire event loop. "
            "Conversely, standard `def` endpoints in FastAPI are automatically offloaded to an external threadpool, preventing event loop starvation."
        )
    },
    {
        "id": "doc_system_design_caching",
        "title": "Distributed Caching Strategies: Cache-Aside, Write-Through, and Eviction",
        "topic": "System Design",
        "skill": "System Design",
        "source": "Placement Prep Knowledge Base - High Scalability",
        "url": "https://aws.amazon.com/caching/",
        "content": (
            "In high-traffic distributed systems, memory caches (such as Redis or Memcached) absorb read load and reduce database latency. "
            "The most common pattern is Cache-Aside (Lazy Loading): the application first queries the cache; upon a cache miss, it reads from the database, "
            "populates the cache with a Time-To-Live (TTL), and returns the result. In Write-Through caching, writes update both cache and database simultaneously. "
            "Eviction algorithms include LRU (Least Recently Used), LFU (Least Frequently Used), and TTL expiration to prevent stale data."
        )
    },
    {
        "id": "doc_python_memory",
        "title": "Python Memory Management, GIL, and Garbage Collection",
        "topic": "Programming",
        "skill": "Python",
        "source": "Placement Prep Knowledge Base - Core Python",
        "url": "https://docs.python.org/3/c-api/memory.html",
        "content": (
            "Python uses reference counting as its primary memory reclamation mechanism. When an object's reference count drops to zero, its memory is deallocated immediately. "
            "To resolve reference cycles (e.g., self-referencing lists or objects), CPython employs a generational cyclic garbage collector (Generations 0, 1, and 2). "
            "The Global Interpreter Lock (GIL) is a mutex that prevents multiple native threads from executing Python bytecodes concurrently, ensuring thread safety for CPython's memory management."
        )
    },
    {
        "id": "doc_git_workflows",
        "title": "Git Branching Strategies: Trunk-Based Development vs GitFlow",
        "topic": "DevOps & Tools",
        "skill": "Git",
        "source": "Placement Prep Knowledge Base - Engineering Practices",
        "url": "https://trunkbaseddevelopment.com/",
        "content": (
            "Trunk-Based Development involves engineers committing small, frequent changes directly to a shared main branch (or short-lived feature branches lasting < 1-2 days) "
            "paired with automated CI/CD pipelines and feature flags. This reduces merge hell and improves continuous delivery. In contrast, GitFlow utilizes long-lived release, "
            "develop, and hotfix branches, suitable for scheduled enterprise release cycles."
        )
    },
    {
        "id": "doc_rest_principles",
        "title": "REST API Architecture, Idempotency, and HTTP Status Codes",
        "topic": "CS Fundamentals",
        "skill": "REST APIs",
        "source": "Placement Prep Knowledge Base - API Standards",
        "url": "https://restfulapi.net/",
        "content": (
            "RESTful APIs rely on stateless client-server communication using standard HTTP verbs. GET, HEAD, OPTIONS, PUT, and DELETE are idempotent, "
            "meaning identical subsequent requests yield the same server state. POST is non-idempotent. Key status code ranges: 2xx (Success: 200 OK, 201 Created), "
            "3xx (Redirection), 4xx (Client Error: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 422 Unprocessable Entity), and 5xx (Server Error: 500, 502, 503)."
        )
    }
]
