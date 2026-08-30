# PRD — Knowledge Base MCP Server (v1)

## Context

I learn a lot through conversations with LLMs, and that knowledge decays. My hypothesis is that the useful unit to store is not notes but **questions**: if I can answer the same questions later, I've validated that I still understand the topic.

This first version exists to **build a corpus and find out whether it has value**. It is deliberately not a spaced repetition system. I do not yet know what makes a question worth keeping, so the system must not bake in assumptions about scheduling, prioritisation, or review cadence.

The workflow it enables:

1. I have a conversation with Claude about some topic.
2. At the end, I ask Claude to extract the questions worth keeping.
3. I refine them in conversation — drop some, reword others.
4. I approve, and Claude calls `submit_questions`.

## Goals

- Capture questions from a conversation with near-zero friction, while the model still has full context.
- Store enough metadata that a future retrieval can filter usefully without rereading source material.
- Retrieve questions by topic and other filters so I can practice.
- Stay small enough that I can throw it away and rewrite it if the thesis turns out to be wrong.

## Non-goals (v1)

Do not build any of these, even if they seem like obvious extensions:

- Spaced repetition scheduling, intervals, or due dates.
- Automatic grading of my answers.
- A web UI, CLI, or any interface other than MCP.
- Neglect detection ("you haven't reviewed ML in a while").
- Remote hosting, OAuth, or multi-user support.
- A database. Flat files only.
- Semantic/vector search. Plain filtering first; I want to find out where it actually fails.

## Technical constraints

- Python, using the official MCP Python SDK with FastMCP.
- Pin `mcp>=1.27,<2` — v2 is in alpha and the API differs.
- `uv` for dependency management.
- **stdio transport**, run locally. No HTTP server.
- Storage: append-only JSONL under a configurable data directory (default `~/.knowledge-base/`), one JSON object per line.
  - `questions.jsonl`
  - `sessions.jsonl`
- Must be testable with the MCP Inspector (`uv run mcp dev server.py`) before connecting to a client.

## Data model

### Question

| Field | Type | Notes |
|---|---|---|
| `id` | str | Server-generated UUID. |
| `session_id` | str | Groups questions captured from the same conversation. |
| `question` | str | The question text. |
| `answer_sketch` | str | Brief correct answer — enough to self-check, not an essay. |
| `excerpt` | str | Verbatim chunk of the conversation this came from. A few hundred words max. **This is the most important field**: it's where I land when I fail a question. |
| `topic` | str | Primary topic, e.g. `databricks`, `postgres-indexing`. |
| `tags` | list[str] | Freeform, for cross-cutting filters. |
| `origin` | str | What I was doing when I learned this — project, exam, job search, curiosity. |
| `confidence_at_time` | enum | `solid` / `shaky` / `new`. How well I understood it at capture time, judged from the conversation. |
| `source_kind` | enum | `my_question` / `derived`. Whether this was a question I actually asked, or one generated from the material. |
| `created_at` | ISO datetime | Server-generated. |
| `content_volatility` | enum | `stable` / `product`. Product knowledge (tool versions, cloud service APIs) goes stale externally, not just in my head. Retrieval should surface a staleness warning for these. |

### Session

| Field | Type | Notes |
|---|---|---|
| `id` | str | Server-generated. Returned to the model on first submit. |
| `summary` | str | One or two sentences on what the conversation covered. |
| `topic` | str | |
| `source_url` | str \| None | Optional — I may paste the chat URL manually. |
| `created_at` | ISO datetime | |

## Tools

### `submit_questions`

Takes a **batch** — `list[Question]` — not one question per call. A session might produce fifteen; fifteen round trips is unacceptable.

Arguments: the question list, plus an optional `session_id`. If absent, create a new session and return its id so subsequent calls in the same conversation can group correctly.

Returns: the `session_id` and the count saved.

The docstring must state that this is only to be called **after the user has explicitly approved the questions**. Claude should never submit on its own judgement that a conversation was worth keeping.

## Acceptance criteria

- [ ] Server starts over stdio and both tools appear in MCP Inspector.
- [ ] Submitting a batch of 5 questions writes 5 lines to `questions.jsonl` and 1 to `sessions.jsonl`, and returns the session id.
- [ ] A second submit with that session id adds questions without creating a new session.
- [ ] `search_questions(topic="databricks")` returns only those questions.
- [ ] Combined filters work (`topic` + `confidence_at_time`).
- [ ] Malformed input returns a clear error rather than corrupting the file.
- [ ] Data directory is configurable via environment variable.
- [ ] README covers install, running under Inspector, and registering with Claude Code / Claude Desktop.

## Open questions to resolve during implementation

- Where Claude Code persists session transcripts locally (check `~/.claude/projects/`), and whether the server can read them directly instead of relying on the model to reproduce excerpts. If it can, that's a strictly better source for `excerpt` — but confirm the format before building on it.
- Whether `answer_sketch` and `excerpt` are redundant in practice. Keep both for now; the corpus will tell me.