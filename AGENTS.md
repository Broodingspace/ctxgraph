# ctxgraph for AI Agent Builders

This document is for developers building AI coding agents, IDE extensions, context-aware tools, or anything that needs to reason about a Python codebase programmatically.

ctxgraph is designed to be the **context layer** underneath those tools — not a product itself.

---

## The problem ctxgraph solves for you

When your agent needs to answer "what code is relevant to this task?", the naive approach is:

- dump all files into the context window (expensive, noisy)
- use vector similarity search (misses structural relationships)
- grep for keywords (no awareness of dependencies)

ctxgraph gives you a third option: **structural retrieval**. It builds a typed graph of the codebase and lets you query it — so you can retrieve the *right* code based on how it's actually connected, not just how it looks like a match.

---

## Quickstart for agent builders

```python
from ctxgraph import build_graph, pack_minimal_context, rank_context_for_query

# Build once, query many times
graph = build_graph("/path/to/user/repo")

# Rank relevant symbols for a task
ranked = rank_context_for_query(graph, "user authentication and JWT handling")
for scored in ranked.ranked_nodes[:10]:
    print(f"{scored.score:.2f}  {scored.node.id}")

# Pack into a token budget (ready to inject into a prompt)
context = pack_minimal_context(
    graph,
    query="user authentication and JWT handling",
    token_budget=4000,
)
print(f"{len(context.nodes)} nodes, ~{context.estimated_tokens} tokens")

# Access the nodes to build your prompt
for node in context.nodes:
    if node.location:
        # Read the actual source lines
        print(f"# {node.id} ({node.location.file_path}:{node.location.line_start})")
```

---

## Core queries an agent will use

### "What does this function depend on?"

```python
from ctxgraph import QueryEngine

engine = QueryEngine(graph)

result = engine.get_dependencies("myapp.services.user_service.create_user")
for dep in result.dependencies:
    print(dep.id, [et.name for et in result.dependency_types[dep.id]])
```

### "What breaks if I change this?"

```python
result = engine.find_blast_radius(
    "myapp.models.User",
    max_depth=3,
    direction="incoming",  # what depends on User?
)

print(f"{result.count} symbols potentially affected")
for node in result.nodes_at_distance(1):
    print(f"  direct: {node.id}")
for node in result.nodes_at_distance(2):
    print(f"  indirect: {node.id}")
```

### "How is A connected to B?"

```python
result = engine.trace_path("myapp.api.handlers.create_order", "myapp.db.session")
if result.exists:
    print(f"Path length: {result.length}")
    for i, node_id in enumerate(result.path):
        print(f"  {node_id}")
        if i < len(result.edges):
            print(f"    --[{result.edges[i].name.lower()}]-->")
```

### "What are the most important symbols in this repo?"

```python
# High in-degree = many things depend on this
hotspots = sorted(
    graph.nodes(),
    key=lambda n: len(graph.get_incoming_edges(n.id)),
    reverse=True,
)[:10]

for node in hotspots:
    deg = len(graph.get_incoming_edges(node.id))
    print(f"  {deg:>4}  {node.id}")
```

---

## Edge types available for traversal

```python
from ctxgraph import EdgeType

EdgeType.IMPORTS    # module A imports module B
EdgeType.DEFINES    # module/class defines a symbol
EdgeType.CONTAINS   # structural containment (class → method)
EdgeType.INHERITS   # class A inherits from class B
EdgeType.CALLS      # function A calls function B  ← behavior graph
```

Filter traversal to specific edge types:

```python
# Only follow call edges (behavioral blast radius)
result = engine.find_blast_radius(
    "myapp.auth.verify_token",
    max_depth=3,
    direction="incoming",
    edge_types=[EdgeType.CALLS],
)
```

---

## Save and reload (avoid re-parsing on every run)

```python
from ctxgraph import save_graph, load_graph

# Parse once and cache
graph = build_graph("/path/to/repo")
save_graph(graph, ".ctxgraph_cache.json")

# Reload in subsequent runs
graph = load_graph(".ctxgraph_cache.json")
```

---

## Accessing source locations

Every node has an optional `location` for reading back the actual source:

```python
from pathlib import Path

for node in context.nodes:
    if node.location:
        source_lines = Path(node.location.file_path).read_text().splitlines()
        snippet = source_lines[node.location.line_start - 1 : node.location.line_end]
        print(f"# {node.id}")
        print("\n".join(snippet))
        print()
```

---

## Customising retrieval scoring

```python
from ctxgraph.retrieval.scoring import ScoringWeights
from ctxgraph import RetrievalEngine

# Bias more toward name matching, less toward centrality
weights = ScoringWeights(
    name_match=5.0,
    path_match=1.0,
    docstring_match=2.0,
    centrality=0.5,
    type_bonus=1.5,
    entrypoint_bonus=3.0,
)

engine = RetrievalEngine(graph, weights=weights)
result = engine.rank_context_for_query(
    "database connection pooling",
    entrypoints=["myapp.db"],   # bias toward db-related nodes
)
```

---

## What's not in v1 (and how to work around it)

| Gap | Workaround |
|-----|-----------|
| No external imports (stdlib, pip packages) | After getting context nodes, read their import lists and supplement manually |
| CALLS edges are intra-repo only | Combine with `IMPORTS` edge traversal for module-level connectivity |
| No config file parsing | Add config file paths as metadata on module nodes manually |
| No test ↔ source links | Use naming conventions: `test_foo.py` → `foo.py` |

---

## Contribution ideas for agent builders

If you're building on ctxgraph and hit a limitation, that's the best kind of contribution:

- **Call graph completeness** — improve resolution for dynamic dispatch, decorators, `functools.partial`
- **External symbol stubs** — create lightweight placeholder nodes for stdlib/pip imports so cross-library blast radius works
- **Config dependency edges** — parse `pyproject.toml`, `settings.py`, `.env` and link config keys to the symbols that read them
- **Test coverage edges** — link test functions to the functions they test via name convention or `pytest` markers
- **Incremental graph updates** — re-parse only changed files instead of the whole repo

Open an issue first — these are all welcome and several are already on the [roadmap](ROADMAP.md).

---

## Full CLI reference for agent-adjacent tooling

```bash
# Build and explore any repo
ctxgraph build /path/to/repo
ctxgraph hotspots --repo /path/to/repo --top 20 --type function
ctxgraph context --repo /path/to/repo "payment processing" --budget 4000
ctxgraph blast-radius --repo /path/to/repo myapp.models.Order --depth 3
ctxgraph deps --repo /path/to/repo --reverse --transitive myapp.models.User
ctxgraph trace --repo /path/to/repo myapp.api.checkout myapp.db.transaction

# Export once, query fast
ctxgraph export /path/to/repo --out repo_graph.json
ctxgraph hotspots --graph-file repo_graph.json --json | jq '.[0:5]'
ctxgraph context --graph-file repo_graph.json "auth middleware" --json
```
