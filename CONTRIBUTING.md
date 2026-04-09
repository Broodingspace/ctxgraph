# Contributing to ctxgraph

Thanks for your interest in contributing. `ctxgraph` is a library-first project — contributions that improve structural precision, query ergonomics, and developer experience are the most valuable.

---

## Setup

```bash
git clone https://github.com/Broodingspace/ctxgraph
cd ctxgraph
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verify the setup:

```bash
pytest
ruff check src tests
mypy src/ctxgraph
```

All three should pass before you open a PR.

---

## Project structure

```
src/ctxgraph/
  graph/        # Core types: Node, Edge, CodeGraph, NodeType, EdgeType
  parser/       # AST parsing, file discovery, symbol ID resolution
  query/        # QueryEngine: deps, blast radius, paths, context
  retrieval/    # RetrievalEngine: scoring, context packing
  exporters/    # JSON exporter
  cli/          # argparse CLI

tests/
  test_graph/       # Unit tests for graph types
  test_parser/      # Unit tests for parser components
  test_query/       # Unit tests for query engine
  test_retrieval/   # Unit tests for retrieval engine
  test_cli/         # CLI integration tests
  fixtures/         # Sample repositories used in tests
    sample_project/ # Small Python project used across all test suites
```

---

## Coding standards

- Python 3.11+, fully typed (no `Any` without justification)
- Docstrings on all public functions and classes
- `ruff` for linting and import sorting
- `mypy --strict` must pass
- Tests required for new functionality
- No new runtime dependencies without a strong reason — the core library has zero

---

## Running tests

```bash
pytest                          # all tests
pytest tests/test_query/        # specific module
pytest -k "blast_radius"        # filter by name
pytest --cov=ctxgraph           # with coverage
```

---

## High-impact contribution areas

These are the areas where a PR would add the most value:

### Symbol resolution
The current import resolver uses heuristics that work well for standard layouts. Improvements to cross-module symbol tracking (especially for `from x import y` and relative imports) would improve graph completeness for real projects.

See: `src/ctxgraph/parser/resolver.py`

### Call graph extraction
`CALLS` edges are not yet extracted. A static analysis pass that captures `name(...)` call sites and maps them to their likely definition nodes would significantly improve blast radius quality.

See: `src/ctxgraph/parser/ast_parser.py`, `src/ctxgraph/graph/types.py`

### Graph caching
The CLI re-parses on every run unless you pass `--graph-file`. An automatic cache (hash input files, store graph, invalidate on change) would make the CLI feel instant on large repos.

See: `src/ctxgraph/cli/main.py`, `src/ctxgraph/io/json_graph.py`

### Export formats
Only JSON export is implemented. Mermaid, DOT (Graphviz), and GraphML are natural next formats. These can live in `src/ctxgraph/exporters/` as optional-dependency modules.

### Fixture repositories
The current fixture (`tests/fixtures/sample_project/`) is small. Larger fixtures — ideally modeling realistic application patterns (API layer, service layer, DB layer, auth) — would improve test coverage and demo quality.

See: `tests/fixtures/`

### Retrieval evaluation
The retrieval engine has no benchmark. A set of expected results for known queries against a fixture repository would let us measure and improve scoring quality.

See: `src/ctxgraph/retrieval/`

---

## Pull request checklist

- [ ] Tests pass: `pytest`
- [ ] Lint passes: `ruff check src tests`
- [ ] Types pass: `mypy src/ctxgraph`
- [ ] New functionality has tests
- [ ] Public API changes are reflected in docstrings
- [ ] No new runtime dependencies unless discussed in an issue first

---

## Opening an issue

For bugs: include a minimal reproducible example with the Python version, ctxgraph version, and the repository structure being parsed if relevant.

For features: describe the use case first, not just the implementation idea. The project has a clear scope — check [ROADMAP.md](ROADMAP.md) to see if the feature is already planned.

---

## License

By contributing, you agree your contributions will be licensed under the MIT License.
