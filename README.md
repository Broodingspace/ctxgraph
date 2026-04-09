# ctxgraph

**Structure-first code intelligence for engineers and AI.**

`ctxgraph` converts Python codebases into queryable context graphs — a typed, traversable layer of modules, classes, functions, and their relationships. No embeddings. No vector database. No LLM required.

```bash
pip install ctxgraph
```

---

## What it does

Most code tooling gives you one of:

- **text search** — fast, but no structure
- **static analysis** — rule violations, not relationships
- **PR diffing** — change-centric, not repo-wide

`ctxgraph` gives you a different layer: **a programmatic graph of how your code is structured and connected**, so you can ask:

- *What does this function depend on?*
- *What breaks if I change this class?*
- *How are these two symbols connected?*
- *What is the smallest context window that covers this task?*

Designed to be **library-first**, **local-first**, and **useful without any LLM** — but better when one is involved.

---

## Quickstart

### Install

```bash
pip install ctxgraph
# or from source:
git clone https://github.com/Broodingspace/ctxgraph.git
cd ctxgraph && pip install -e .
```

### Build a graph from your repo

```python
from ctxgraph import build_graph, QueryEngine

graph = build_graph("./src", package_name="myproject")
print(graph.stats())
# {'total_nodes': 84, 'total_edges': 127, ...}

engine = QueryEngine(graph)
```

### Query dependencies

```python
result = engine.get_dependencies("myproject.api.handlers.create_user")
for dep in result.dependencies:
    print(dep.id, dep.type.name)
```

### Estimate blast radius

```python
result = engine.find_blast_radius("myproject.models.User", max_depth=2)
print(f"{result.count} nodes potentially affected")
for node in result.nodes_at_distance(1):
    print(f"  direct: {node.id}")
```

### Trace a path between symbols

```python
result = engine.trace_path("myproject.api.main", "myproject.db.session")
if result.exists:
    print(" -> ".join(result.path))
```

### Pack minimal context for an LLM

```python
from ctxgraph import pack_minimal_context

context = pack_minimal_context(graph, "user authentication", token_budget=2000)
print(f"{len(context.nodes)} nodes, ~{context.estimated_tokens} tokens")
```

---

## CLI

`ctxgraph` ships a local CLI built with `argparse` — zero extra dependencies.

### Build and summarize

```bash
ctxgraph build ./src
# Repository: /abs/path/src
# Nodes: 84
# Edges: 127
# Node types:
#   class: 12
#   function: 51
#   module: 21
```

### Inspect a symbol

```bash
ctxgraph inspect --repo ./src myproject.models.User
```

### Show dependencies

```bash
# Direct outgoing dependencies
ctxgraph deps --repo ./src myproject.models.User

# Reverse: what depends on User?
ctxgraph deps --repo ./src --reverse myproject.models.User

# Transitive closure
ctxgraph deps --repo ./src --reverse --transitive myproject.models.User
```

### Blast radius analysis

```bash
ctxgraph blast-radius --repo ./src myproject.models.User --depth 2 --direction both
# Blast radius for myproject.models.User (depth=2, direction=both):
#   1 hop:
#     myproject.models.User.__init__
#     myproject.services.user_service
#   2 hops:
#     myproject.api.handlers.create_user
#     myproject.api.handlers.get_user
```

### Trace a path

```bash
ctxgraph trace --repo ./src myproject.api.handlers myproject.db.session
```

### Export graph to JSON

```bash
ctxgraph export ./src --format json --out graph.json
```

### Load a saved graph (fast, no re-parse)

```bash
ctxgraph load graph.json
ctxgraph inspect --graph-file graph.json myproject.models.User
ctxgraph blast-radius --graph-file graph.json myproject.models.User --depth 3
```

---

## GitHub Action

`ctxgraph` now includes a proof-of-concept GitHub Action for structural PR impact analysis.

It is aimed at a gap most tooling does not cover cleanly for Python repositories:

- detect changed Python files in a pull request
- map changed lines to graph symbols
- compute blast radius for each changed symbol
- identify likely high-risk callers
- post a PR comment with a structural impact summary

Minimal workflow example:

```yaml
name: ctxgraph impact

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: Broodingspace/ctxgraph@main
        with:
          repo-path: .
          base-ref: ${{ github.event.pull_request.base.sha }}
          head-ref: ${{ github.event.pull_request.head.sha }}
          comment-mode: pr
          run-tests: "true"
          test-command: "pytest"
```

Local preview example:

```bash
python scripts/github_action.py \
  --repo-path . \
  --base-ref HEAD~1 \
  --head-ref HEAD \
  --comment-mode none \
  --markdown-out .ctxgraph/impact-report.md
```

Action test inputs:

- `run-tests`: run the repository test suite before impact reporting
- `test-command`: test command to execute, for example `pytest` or `python -m pytest`
- `fail-on-test-failure`: fail the action if tests fail

Implementation files:

- [action.yml](action.yml)
- [scripts/github_action.py](scripts/github_action.py)
- [.github/workflows/ctxgraph-impact-demo.yml](.github/workflows/ctxgraph-impact-demo.yml)

---

## Architecture

`ctxgraph` is organized in five layers:

```
┌─────────────────────────────────────────────────────┐
│  CLI             ctxgraph build / inspect / deps...  │
├─────────────────────────────────────────────────────┤
│  Retrieval       rank_context_for_query              │
│                  pack_minimal_context                │
├─────────────────────────────────────────────────────┤
│  Query           get_dependencies                    │
│                  find_blast_radius                   │
│                  trace_path                          │
│                  get_related_context                 │
├─────────────────────────────────────────────────────┤
│  Graph           CodeGraph, Node, Edge               │
│                  NodeType, EdgeType, SourceLocation  │
├─────────────────────────────────────────────────────┤
│  Parser          AST-based Python parsing            │
│                  file discovery, symbol resolution   │
└─────────────────────────────────────────────────────┘
```

### Nodes

| Type | Description |
|------|-------------|
| `MODULE` | A Python file or package |
| `CLASS` | A class definition |
| `FUNCTION` | A function or method |
| `PACKAGE` | A directory with `__init__.py` |

### Edges

| Type | Description |
|------|-------------|
| `IMPORTS` | Module imports another module |
| `DEFINES` | Module/class defines a symbol |
| `CONTAINS` | Structural containment (module → class → method) |
| `INHERITS` | Class inherits from another class |
| `CALLS` | Function calls another function *(v1.2)* |
| `REFERENCES` | Symbol references another symbol *(v1.2)* |

### Package layout

```
src/ctxgraph/
  graph/        # Node, Edge, EdgeType, NodeType, CodeGraph
  parser/       # AST parsing, file discovery, symbol resolution
  query/        # QueryEngine — deps, blast radius, paths, context
  retrieval/    # RetrievalEngine — ranking, context packing
  exporters/    # JSON graph export
  cli/          # CLI entrypoint
```

---

## Retrieval

The retrieval layer ranks code entities by relevance to a text query using **hybrid structural scoring** — no embeddings required in v1:

| Signal | Weight |
|--------|--------|
| Symbol name match | high |
| File path match | medium |
| Docstring match | medium |
| Graph centrality (degree) | low |
| Node type preference (function/class) | low |
| Entrypoint proximity | configurable |

```python
from ctxgraph import rank_context_for_query, pack_minimal_context

ranked = rank_context_for_query(graph, "database session")
for scored in ranked.ranked_nodes[:5]:
    print(f"{scored.node.id}: {scored.score:.2f}")

context = pack_minimal_context(
    graph,
    query="user authentication",
    token_budget=3000,
    entrypoints=["myproject.api.handlers"],
)
print(f"Budget utilization: {context.utilization:.1f}%")
```

---

## Programmatic API

### Build

```python
from ctxgraph import build_graph, GraphBuilder

# Simple
graph = build_graph("./src")

# With options
builder = GraphBuilder(
    root_path="./src",
    package_name="myproject",
    exclude_dirs={"migrations", "vendor"},
    include_tests=False,
)
graph = builder.build()
```

### Query

```python
from ctxgraph import QueryEngine

engine = QueryEngine(graph)

# Dependencies
result = engine.get_dependencies("myproject.auth.login", transitive=True)

# Reverse dependencies
result = engine.get_reverse_dependencies("myproject.models.User")

# Blast radius
result = engine.find_blast_radius(
    "myproject.db.connection",
    max_depth=3,
    direction="incoming",  # what depends on this?
)

# Path tracing
result = engine.trace_path("myproject.cli.main", "myproject.db.session")

# Local context neighborhood
result = engine.get_related_context("myproject.models.User", radius=2)
```

### Persist and reload

```python
from ctxgraph import save_graph, load_graph

save_graph(graph, "graph.json")
graph = load_graph("graph.json")
```

---

## Why not X?

| Tool | What it optimizes for | How ctxgraph differs |
|------|----------------------|----------------------|
| RAG / vector search | text similarity | structure-first, no embeddings in v1 |
| Static analyzers (pylint, mypy) | rule violations | structural context, not diagnostics |
| Code review tools (reviewdog, etc.) | PR diffs | repo-wide, library-first |
| ast/tree-sitter libraries | raw AST | higher-level typed graph + query APIs |
| code2flow, pyan | visualization | programmatic API, queryable, retrieval-ready |

---

## Limitations

- **v1 is Python-only.** Language support can be extended in future versions.
- **Import and inheritance resolution is conservative.** Cross-module resolution uses heuristics that work well for standard layouts but may miss complex dynamic imports.
- **No call graph in v1.** `CALLS` and `REFERENCES` edges are planned for v1.2.
- **Retrieval is structure-first, not embedding-based.** Semantic similarity is not yet supported.
- **No automatic graph caching in v1.** CLI commands re-parse on each run, or you can use `--graph-file` with a pre-exported JSON.

---

## Development

```bash
git clone https://github.com/Broodingspace/ctxgraph
cd ctxgraph
pip install -e ".[dev]"

# Tests
pytest

# Lint
ruff check src tests

# Type check
mypy src/ctxgraph
```

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan.

**Near term (v1.1):**
- automatic graph caching for CLI workflows
- richer import and symbol resolution
- `--json` output on all query commands
- Mermaid / DOT export for visualization

**Medium term (v1.2):**
- `CALLS` edge extraction for common call patterns
- graph diffing between snapshots
- repository hotspot summaries
- retrieval presets for onboarding, bugfixing, refactoring

**Longer term:**
- broader language support
- deeper change-impact analysis
- optional LLM integrations as a separate optional package

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and contribution guidelines.

High-impact areas where contributions are especially welcome:

- **symbol resolution** — better cross-module import tracking
- **call graph extraction** — static analysis of function calls
- **graph caching** — invalidation strategy for the CLI
- **export formats** — Mermaid, DOT, GraphML
- **fixture repositories** — larger and more realistic test codebases
- **retrieval evaluation** — benchmarks and quality metrics

---

## License

MIT. See [LICENSE](LICENSE).
