# File Index And Graph

Aegix needs fast local file discovery for agents working across large trees. Preview v0.2 adds a lightweight file intelligence layer.

## Purpose

The index helps an agent answer:

- what files exist?
- which files are text, code, structured data, receipts, or notes?
- what files mention a term?
- what paths reference other paths or Markdown links?
- where should a future vector database attach?

## Commands

```bash
agentctl index --json
agentctl index --scope /aegix/projects --scope /aegix/notes --json
agentctl search-index "service restart" --json
agentctl graph --json
```

## Artifacts

```text
/aegix/index/
  files.jsonl              File metadata and snippets
  graph.json               Nodes, containment edges, reference edges, summary
  aegix_index.sqlite       SQLite metadata and FTS search index
  vector-registry.json     Vector DB attachment plan
```

## Design Rule

Files and SQLite/JSON graph records are the source of truth. Vector storage is only an index over that truth.

This keeps memory inspectable:

```bash
rg "rollback" /aegix/index /aegix/notes /aegix/projects
sqlite3 /aegix/index/aegix_index.sqlite '.tables'
agentctl search-index "rollback" --json
```

## Vector DB Plan

The preview VM includes Qdrant as the recommended local vector backend, but v0.2 does not generate embeddings yet. The attachment point is:

```text
/aegix/index/vector-registry.json
```

Future embedding workers should:

- read canonical records from `files.jsonl`
- respect data classification and secret policy
- write vectors to a collection such as `aegix_files`
- keep file path, hash, mtime, and receipt/session ids as metadata
- delete or refresh vectors when the source hash changes

Do not embed secret stores, credential-adjacent files, or private regulated data unless policy explicitly allows it.

