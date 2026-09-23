"""Curated Educational Knowledge Base for Grounded RAG.
Used to index into Azure AI Search and as a local deterministic knowledge base.
Provides authoritative, interview-focused documentation across core engineering domains.
"""

EDUCATIONAL_DOCUMENTS = [
    # -------------------------------------------------------------
    # 1. DATABASES & DATA SYSTEMS
    # -------------------------------------------------------------
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
        "id": "doc_nosql_vs_relational",
        "title": "Relational Databases vs NoSQL: MongoDB, DynamoDB, and Redis",
        "topic": "Databases",
        "skill": "Databases",
        "source": "Placement Prep Knowledge Base - Data Stores",
        "url": "https://aws.amazon.com/nosql/",
        "content": (
            "Relational databases (PostgreSQL, MySQL) excel at complex multi-table joins, ACID transactions, and structured schemas. "
            "NoSQL databases relax rigid relational guarantees for horizontal scaling and high write throughput. "
            "Document stores (MongoDB) store flexible JSON/BSON hierarchies, ideal for catalog data and rapid prototyping. "
            "Key-value stores (Redis, DynamoDB) deliver sub-millisecond lookups via primary keys, ideal for session stores and leaderboards. "
            "Columnar stores (Cassandra) optimize write-heavy analytical workloads across distributed clusters."
        )
    },

    # -------------------------------------------------------------
    # 2. BACKEND FRAMEWORKS & LANGUAGES
    # -------------------------------------------------------------
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
        "id": "doc_springboot_architecture",
        "title": "Spring Boot Dependency Injection, Inversion of Control, and Bean Lifecycle",
        "topic": "Backend Frameworks",
        "skill": "Spring Boot",
        "source": "Placement Prep Knowledge Base - Java Enterprise",
        "url": "https://spring.io/projects/spring-boot",
        "content": (
            "Spring Boot provides Inversion of Control (IoC) via the ApplicationContext container. "
            "Components marked with `@Component`, `@Service`, or `@Repository` are registered as Spring Beans. "
            "By default, Spring Beans are singletons. The bean lifecycle includes: instantiation, dependency injection (`@Autowired`), "
            "`@PostConstruct` initialization, availability in the container, and `@PreDestroy` cleanup upon application shutdown. "
            "Spring Boot auto-configuration analyzes classpath dependencies and automatically initializes required beans."
        )
    },
    {
        "id": "doc_nodejs_event_loop",
        "title": "Node.js Single-Threaded Event Loop and Non-Blocking I/O Architecture",
        "topic": "Backend Frameworks",
        "skill": "Node.js",
        "source": "Placement Prep Knowledge Base - JavaScript Runtime",
        "url": "https://nodejs.org/en/docs/guides/event-loop-timers-and-nexttick/",
        "content": (
            "Node.js runs on a single main execution thread powered by the V8 JavaScript engine and libuv. "
            "Libuv provides an abstraction layer over operating system asynchronous primitives (epoll on Linux, kqueue on macOS, IOCP on Windows) "
            "and maintains a background threadpool for blocking operations (filesystem I/O, crypto, DNS). "
            "The event loop executes in discrete phases: Timers (setTimeout/setInterval), Pending I/O callbacks, Idle/Prepare, Poll (incoming connections and data), "
            "Check (setImmediate), and Close callbacks. `process.nextTick` executes microtasks immediately after the current operation."
        )
    },

    # -------------------------------------------------------------
    # 3. FRONTEND ENGINEERING
    # -------------------------------------------------------------
    {
        "id": "doc_react_hooks_lifecycle",
        "title": "React Component Lifecycle, Virtual DOM, and Hooks Architecture",
        "topic": "Frontend",
        "skill": "React",
        "source": "Placement Prep Knowledge Base - Modern Web UI",
        "url": "https://react.dev/reference/react",
        "content": (
            "React maintains a lightweight in-memory Virtual DOM representation of the UI. "
            "When component state (`useState`, `useReducer`) changes, React reconciles changes between the previous and new Virtual DOM "
            "using the Diffing algorithm and batches minimum mutations to the real browser DOM. "
            "`useEffect` handles side-effects (data fetching, subscriptions); its dependency array dictates re-execution: empty array runs only on mount/unmount, "
            "specific dependencies run on change, omitted array runs on every render. `useCallback` memoizes function references and `useMemo` caches expensive calculations."
        )
    },
    {
        "id": "doc_javascript_async_loop",
        "title": "JavaScript Event Loop: Microtasks, Macrotasks, and Promise Resolution",
        "topic": "Frontend",
        "skill": "JavaScript",
        "source": "Placement Prep Knowledge Base - JavaScript Core",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop",
        "content": (
            "JavaScript is a single-threaded language featuring run-to-completion semantics for synchronous code in the call stack. "
            "Asynchronous callbacks are partitioned into two priority queues: "
            "1. Microtask Queue: includes `Promise.then`, `catch`, `finally`, `queueMicrotask`, and `MutationObserver`. "
            "2. Macrotask (Task) Queue: includes `setTimeout`, `setInterval`, I/O, and UI rendering events. "
            "After every synchronous call stack frame finishes, the engine completely empties the entire Microtask Queue before executing the next Macrotask."
        )
    },

    # -------------------------------------------------------------
    # 4. SYSTEM DESIGN & DISTRIBUTED SYSTEMS
    # -------------------------------------------------------------
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
        "id": "doc_cap_theorem",
        "title": "CAP Theorem, Eventual Consistency, and PACELC in Distributed Architecture",
        "topic": "System Design",
        "skill": "System Design",
        "source": "Placement Prep Knowledge Base - Distributed Architecture",
        "url": "https://en.wikipedia.org/wiki/CAP_theorem",
        "content": (
            "The CAP Theorem states that in the event of a network partition (P), a distributed system must choose between "
            "Consistency (C - every read receives the most recent write or an error) and Availability (A - every non-failing node returns a response). "
            "Systems like Spanner and ZooKeeper choose CP, while DynamoDB and Cassandra typically favor AP with eventual consistency. "
            "The PACELC theorem expands this: if there is a Partition (P), choose between Availability (A) and Consistency (C); Else (E), "
            "choose between Latency (L) and Consistency (C)."
        )
    },
    {
        "id": "doc_message_queues_kafka",
        "title": "Event-Driven Architecture: Apache Kafka Partitions vs RabbitMQ",
        "topic": "System Design",
        "skill": "System Design",
        "source": "Placement Prep Knowledge Base - Distributed Messaging",
        "url": "https://kafka.apache.org/documentation/",
        "content": (
            "Message brokers decouple services and smooth out load spikes. "
            "RabbitMQ is an AMQP message broker where messages are routed through exchanges to queues and acknowledged/deleted upon consumption. "
            "Apache Kafka is a distributed, append-only commit log. Topics are partitioned across cluster brokers, enabling massive parallelism. "
            "Consumers track their own offset in consumer groups. Kafka guarantees strict message ordering within a single partition (via partition key hashing), "
            "retains messages according to retention policies, and supports high-throughput event sourcing."
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
    },
    {
        "id": "doc_microservices_patterns",
        "title": "Microservices Architecture: API Gateway, Service Discovery, and Circuit Breakers",
        "topic": "System Design",
        "skill": "System Design",
        "source": "Placement Prep Knowledge Base - Microservice Patterns",
        "url": "https://microservices.io/patterns/index.html",
        "content": (
            "Microservices decompose monolithic applications into independently deployable, loosely coupled domain services communicating via HTTP/REST or gRPC. "
            "An API Gateway serves as a single reverse-proxy entry point handling SSL termination, authentication, rate limiting, and request routing. "
            "Service Discovery (e.g. Consul, Eureka, Kubernetes DNS) dynamically tracks ephemeral container IP addresses. "
            "Resilience patterns such as Circuit Breakers (Hystrix, Resilience4j) prevent cascading failures by tripping open when downstream services fail, "
            "returning fast fallbacks while periodic half-open probes test for recovery."
        )
    },

    # -------------------------------------------------------------
    # 5. DEVOPS, CONTAINERS & CLOUD
    # -------------------------------------------------------------
    {
        "id": "doc_docker_internals",
        "title": "Docker Container Internals: Namespaces, Cgroups, and Multi-Stage Builds",
        "topic": "DevOps & Tools",
        "skill": "Docker",
        "source": "Placement Prep Knowledge Base - Container Technology",
        "url": "https://docs.docker.com/build/building/multi-stage/",
        "content": (
            "Containers are isolated Linux processes sharing the host kernel. Isolation is implemented via Linux Namespaces "
            "(PID isolates processes, NET isolates network interfaces, MNT isolates filesystems, IPC isolates inter-process communication) "
            "and Control Groups (cgroups, which enforce CPU, memory, and I/O resource limits). "
            "Multi-stage Dockerfiles use multiple `FROM` instructions to compile dependencies in an intermediate builder stage "
            "and copy only the final binary into a minimal runtime image (e.g. Alpine or distroless), slashing image size and attack surface."
        )
    },
    {
        "id": "doc_kubernetes_architecture",
        "title": "Kubernetes Architecture: Control Plane, Pods, Deployments, and Services",
        "topic": "DevOps & Tools",
        "skill": "Kubernetes",
        "source": "Placement Prep Knowledge Base - Container Orchestration",
        "url": "https://kubernetes.io/docs/concepts/",
        "content": (
            "Kubernetes orchestrates containerized workloads across node clusters. "
            "The Control Plane comprises the API Server (REST gateway), etcd (distributed state store), Kube-Scheduler (assigns Pods to nodes), "
            "and Controller Manager (reconciles desired state). Worker nodes run Kubelet (node agent), Kube-Proxy (networking rules), and the container runtime. "
            "A Pod is the smallest deployable compute unit. Deployments manage declarative ReplicaSets and rolling updates without downtime. "
            "Services provide stable virtual IPs: ClusterIP (internal), NodePort (exposes port on host), and LoadBalancer (cloud external IP)."
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
        "id": "doc_aws_core_services",
        "title": "AWS Cloud Foundations: Compute, Storage, IAM, and Virtual Private Cloud",
        "topic": "DevOps & Tools",
        "skill": "AWS",
        "source": "Placement Prep Knowledge Base - Cloud Infrastructure",
        "url": "https://docs.aws.amazon.com/whitepapers/latest/aws-overview/",
        "content": (
            "Amazon Web Services provides global cloud infrastructure. "
            "Compute options include EC2 (elastic virtual machines) and AWS Lambda (event-driven serverless functions with auto-scaling). "
            "Storage options include S3 (object storage with 99.999999999% durability across storage tiers) and EBS (block storage attached to EC2 instances). "
            "Security is governed by IAM (Identity and Access Management) through users, groups, roles (assumed by services), and least-privilege JSON policies. "
            "Virtual Private Cloud (VPC) provides isolated networks with public/private subnets, Internet Gateways, NAT Gateways, and Security Groups."
        )
    },

    # -------------------------------------------------------------
    # 6. OPERATING SYSTEMS & COMPUTER NETWORKS
    # -------------------------------------------------------------
    {
        "id": "doc_os_concurrency_deadlocks",
        "title": "Operating System Concurrency: Processes vs Threads, Semaphores, and Deadlocks",
        "topic": "CS Fundamentals",
        "skill": "Operating Systems",
        "source": "Placement Prep Knowledge Base - OS Core",
        "url": "https://en.wikipedia.org/wiki/Deadlock",
        "content": (
            "A process is an executing program with its own dedicated virtual address space (code, data, heap, stack). "
            "A thread is the smallest unit of CPU execution sharing memory and file descriptors with peer threads in the same process. "
            "Synchronization primitives like Mutexes (mutual exclusion) and Semaphores (counting locks) prevent race conditions in critical sections. "
            "A Deadlock occurs when processes are unable to proceed because each holds a resource while waiting for another. "
            "Coffman's four deadlock conditions must hold simultaneously: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait."
        )
    },
    {
        "id": "doc_networking_tcp_handshake",
        "title": "Computer Networks: TCP 3-Way Handshake, Flow Control, and HTTP Protocols",
        "topic": "CS Fundamentals",
        "skill": "Computer Networks",
        "source": "Placement Prep Knowledge Base - Network Protocols",
        "url": "https://www.rfc-editor.org/rfc/rfc793",
        "content": (
            "TCP is a connection-oriented, reliable transport protocol. "
            "Connection establishment utilizes the 3-Way Handshake: SYN (client requests connection with initial sequence number), "
            "SYN-ACK (server acknowledges and sends its sequence number), and ACK (client acknowledges server sequence). "
            "TCP guarantees reliability via sliding window flow control, sequence numbering, and congestion avoidance algorithms. "
            "HTTP/1.1 introduced persistent connections; HTTP/2 introduced multiplexed binary streams over a single TCP connection; "
            "HTTP/3 replaces TCP with QUIC over UDP to eliminate head-of-line blocking."
        )
    },
    {
        "id": "doc_dsa_complexity",
        "title": "Data Structures & Algorithm Complexity: Big-O, Hash Collisions, and Trees",
        "topic": "CS Fundamentals",
        "skill": "Data Structures",
        "source": "Placement Prep Knowledge Base - Algorithms",
        "url": "https://en.wikipedia.org/wiki/Big_O_notation",
        "content": (
            "Algorithm complexity evaluates execution time and memory growth as input size n approaches infinity. "
            "Hash tables offer average O(1) time complexity for lookup, insert, and delete; collisions are resolved using separate chaining "
            "(linked lists/red-black trees) or open addressing (linear/quadratic probing). "
            "Binary Search Trees (BST) provide O(log n) average lookups; self-balancing trees (AVL, Red-Black) enforce balance factors to guarantee O(log n) worst-case. "
            "Common complexity classes: O(1) Constant, O(log n) Logarithmic, O(n) Linear, O(n log n) Linearithmic, and O(n^2) Quadratic."
        )
    }
]
