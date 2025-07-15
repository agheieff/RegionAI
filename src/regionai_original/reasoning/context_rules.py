"""
Default context detection rules for the RegionAI reasoning engine.

This module defines the initial knowledge base for automatically detecting
the appropriate analysis context from source code.
"""
from .context import ContextRule


DEFAULT_CONTEXT_RULES = [
    ContextRule(
        context_tag="database-interaction",
        keywords=["SQL", "SELECT", "INSERT", "UPDATE", "DELETE", "db.execute", ".query(", 
                  "cursor.", "connection.", "database", "FROM", "WHERE", "JOIN"]
    ),
    ContextRule(
        context_tag="file-io",
        keywords=["open(", ".read(", ".write(", "Path", "File", "with open", 
                  "os.path", "shutil.", ".close()", "readlines", "writelines"]
    ),
    ContextRule(
        context_tag="api-design",
        keywords=["@app.route", "@api.post", "@api.get", "request", "response", "JSON",
                  "FastAPI", "Flask", "django", "endpoint", "REST", "GraphQL"]
    ),
    ContextRule(
        context_tag="workflow-analysis",
        keywords=["workflow", "pipeline", "step", "stage", "process", "flow",
                  "sequence", "chain", "orchestrat"]
    ),
    ContextRule(
        context_tag="object-oriented",
        keywords=["class ", "self.", "__init__", "super()", "inheritance", "@property",
                  "@classmethod", "@staticmethod", "extends", "implements"]
    ),
    ContextRule(
        context_tag="functional",
        keywords=["lambda", "map(", "filter(", "reduce(", "functools", "partial",
                  "curry", "compose", "pure function"]
    ),
    ContextRule(
        context_tag="data-processing",
        keywords=["pandas", "numpy", "DataFrame", "Series", "array", ".transform",
                  ".aggregate", ".groupby", ".pivot", "matplotlib", "seaborn"]
    ),
    ContextRule(
        context_tag="testing",
        keywords=["test_", "assert", "pytest", "unittest", "mock", "@patch",
                  "fixture", "parametrize", "TestCase", "setUp", "tearDown"]
    ),
    ContextRule(
        context_tag="concurrency",
        keywords=["async", "await", "asyncio", "threading", "multiprocessing",
                  "concurrent", "Lock", "Semaphore", "Queue", "Future"]
    ),
    ContextRule(
        context_tag="error-handling",
        keywords=["try:", "except", "raise", "finally:", "Exception", "Error",
                  "catch", "throw", "handle", "traceback"]
    )
]