# Roadmap

`ctxgraph` is a library-first, local-first code intelligence layer. The roadmap is biased toward structural precision, query ergonomics, and graph-aware retrieval — not toward becoming an app, agent, or generic chatbot.

---

## Current state (v1.0)

Implemented and stable:

- Python AST parsing (files, imports, classes, functions, methods)
- Typed graph construction with stable symbol IDs
- Dependency and reverse-dependency queries (direct and transitive)
- Blast radius analysis with configurable depth and direction
- Shortest-path tracing between two symbols
- Related context extraction (neighborhood BFS)
- Graph-aware retrieval: hybrid scoring (name, path, docstring, centrality)
- Minimal context packing within a token budget
- JSON graph export and reload
- Local CLI: `build`, `load`, `inspect`, `deps`, `blast-radius`, `trace`, `export`
- Zero runtime dependencies (pure stdlib + Python 3.11+)

---

## v1.1 — Developer experience

Focus: faster workflows, better output, stronger structural coverage.

- [ ] Automatic graph caching for CLI commands (hash-based, invalidated on file change)
- [ ] Richer import resolution across sibling modules in a package
- [ ] Better intra-repo symbol linking via import tracking
- [ ] `--json` flag on all query commands (`inspect`, `deps`, `blast-radius`, `trace`)
- [ ] CLI progress indicator for large repositories
- [ ] Improved CLI summary output for repos with 500+ nodes
- [ ] Structured error output for scripting (`--json` on errors too)
- [ ] `ctxgraph context` command: rank and pack context for a query from CLI
- [ ] Documentation and demo assets for public launch

---

## v1.2 — Deeper structural intelligence

Focus: richer relationships, analysis, and output formats.

- [ ] Practical `CALLS` edge extraction for common Python call patterns
- [ ] `REFERENCES` edge extraction for attribute access and name usage
- [ ] Repository hotspot summaries (most depended-on symbols)
- [ ] Graph diffing: compare two saved graph snapshots
- [ ] Mermaid and DOT export for visualization in docs and notebooks
- [ ] `ctxgraph hotspots` command: surface high-centrality nodes
- [ ] Retrieval presets: `--mode onboarding`, `--mode bugfix`, `--mode refactor`
- [ ] `graphviz_exporter` module (optional dependency, not in core)

---

## v1.3 — Scale and robustness

Focus: production-scale usability.

- [ ] Incremental graph updates (re-parse only changed files)
- [ ] Support for `src` layout and namespace packages
- [ ] Configurable node/edge filtering in all query commands
- [ ] Parallel file parsing for large repositories
- [ ] Query result pagination for large blast radius outputs
- [ ] Benchmark suite: parse time and query latency on realistic codebases
- [ ] `ctxgraph validate` command: detect broken edges and unresolved symbols

---

## Longer term

- Broader language support (JavaScript/TypeScript, Go, Java — community-driven)
- Deeper change-impact estimation (probability-weighted blast radius)
- Optional LLM integration as a separate `ctxgraph-llm` package (not in core)
- MCP server adapter for editor and agent integrations
- Notebook-friendly display helpers (Jupyter / Marimo)
- Retrieval quality evaluation framework

---

## Non-goals

These are explicitly out of scope unless the project direction changes:

- Vector database or embedding dependency in the core library
- Mandatory LLM integration
- Web app, dashboard, or server as the primary product surface
- PR-review-only positioning
- Generic code generation or refactoring automation

---

## Contribution ideas

Any of the items above are open for contribution. Additional high-value areas:

- Symbol resolution improvements (especially cross-package)
- Cache invalidation strategy design
- Additional export formats (GraphML, JSON-LD, Parquet)
- Larger and more realistic fixture repositories for integration tests
- Performance benchmarks against well-known OSS Python projects
- Retrieval evaluation examples and quality metrics
- Documentation examples for common developer workflows
