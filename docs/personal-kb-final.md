# Personal Self-Analysis Engine: Implementation Guide (Final)

> **Purpose:** Complete implementation spec for building a personal knowledge base and behavioral analysis system from ~2GB of ChatGPT conversation exports. Designed to be handed to Claude Code, Codex, or a developer. Each phase is self-contained with inputs, outputs, tool choices, and concrete commands.

> **Owner:** Hayk  
> **Stack:** Python + Claude Batch API + Obsidian + MCP servers, running on WSL  
> **Philosophy:** Use existing open-source tools wherever a solved problem exists. Build custom code only for the unique personal analysis logic. Evidence-first — every answer must trace back to source chunks, not just wiki summaries.

---

## Table of Contents

1. [Architecture Decision Record](#1-architecture-decision-record)
2. [System Architecture](#2-system-architecture)
3. [Data Model](#3-data-model)
4. [Phase 0 — Foundation: Ingest & Store](#4-phase-0--foundation-ingest--store)
5. [Phase 1 — Classification: Tag Every Conversation](#5-phase-1--classification-tag-every-conversation)
6. [Phase 2 — Wiki Layer: Compile Knowledge](#6-phase-2--wiki-layer-compile-knowledge)
7. [Phase 3 — Emotional & Behavioral Analysis](#7-phase-3--emotional--behavioral-analysis)
8. [Phase 4 — Temporal Knowledge Graph](#8-phase-4--temporal-knowledge-graph)
9. [Phase 5 — Retrieval Service: Evidence-Grounded Answers](#9-phase-5--retrieval-service-evidence-grounded-answers)
10. [Phase 6 — Obsidian Visualization & MCP Query Interface](#10-phase-6--obsidian-visualization--mcp-query-interface)
11. [Project Structure](#11-project-structure)
12. [Prompts Reference](#12-prompts-reference)
13. [Cost Estimates](#13-cost-estimates)
14. [Human Checkpoints](#14-human-checkpoints)
15. [Use Cases & Output Modes](#15-use-cases--output-modes)

---

## 1. Architecture Decision Record

These decisions were made deliberately based on extensive tool research. Each one explains what was chosen, what was rejected, and why.

### ADR-1: Python over Go for the entire pipeline

**Decision:** Use Python everywhere. No Go.

**Why:** The earlier plan proposed Go for parsing because of "2GB file I/O performance." But every tool in the ecosystem — MyChatArchive, NRCLex, BERTopic, ruptures, GoEmotions, pysentimiento, Graphiti, Basic Memory — is Python. Using Go for Stage 1 means parsing in Go, serializing to disk, then loading in Python for everything else. That's added complexity for a performance gain that doesn't matter (you parse 2GB once, not continuously).

MyChatArchive already handles 2GB+ exports and the non-trivial ChatGPT tree structure in Python. Writing a Go parser reimplements what already exists.

**What Go would be useful for:** A long-running service with concurrent MCP server handling. If the system evolves into something that runs continuously, Go could orchestrate. For now, this is a batch pipeline — Python is the right tool.

**Rejected alternative — Go + PostgreSQL + pgvector:** This is a strong architecture for a multi-user production system. But for a single-user personal project, it means maintaining a Postgres instance, writing importers from scratch, and losing access to the entire Python NLP ecosystem without FFI or subprocess shells. SQLite + Markdown files are more portable, more inspectable, and more ownable long-term — if every tool dies, your data is still plain SQL and plain text files.

### ADR-2: MyChatArchive as the ingestion foundation (not a custom parser)

**Decision:** Use MyChatArchive (`1ch1n/chat-export-structurer`) for initial parsing and storage.

**Why it wins over alternatives:**
- Handles ChatGPT's tree-structured JSON (conversations use parent-child node references, not linear lists) and sharded exports (`conversations-000.json`, `conversations-001.json`)
- Imports ChatGPT, Claude, Grok, and Cursor exports into a **unified SQLite database**
- SHA1-based deduplication (critical for re-imports)
- Local vector embeddings via `sentence-transformers`
- Built-in **MCP server** with `search_brain`, `get_context`, `get_profile` tools — gives you a working query interface from Day 1
- LLM-powered thread summarization

**Why not Convoviz or ChatGPT-to-Markdown:** These convert to Markdown but don't give you a queryable database. We want structured SQLite for the analysis pipeline AND Markdown for Obsidian. MyChatArchive gives us the database; we generate Obsidian Markdown as an output of Phase 2.

**Why not LangChain's ChatGPT loader:** Good reference implementation but doesn't handle deduplication or sharded exports. MyChatArchive is more complete.

**Why not GPT Chat Analysis (`T-rav/gpt-chat-analysis`):** Closest to our pipeline's architecture (it does per-conversation GPT-4 analysis + trend analysis), but it's locked to GPT-4. We want Claude Batch API. Its architecture patterns (incremental processing, date filtering) are worth studying and replicating.

### ADR-3: Claude Batch API for all heavy LLM work

**Decision:** Use Claude Batch API (`anthropic.messages.batches`) for classification, wiki compilation, and deep analysis. Use `claude-batch-toolkit` for CLI convenience.

**Why:** 50% cost reduction vs. real-time API. Supports up to 100,000 requests per batch. Most batches complete within 1 hour. Prompt caching adds further savings for the wiki compilation pass where many conversations share the same system prompt.

**Model choice:** `claude-sonnet-4-20250514` for classification (cost-efficient, accurate enough). `claude-sonnet-4-20250514` for wiki compilation too — the task is synthesis, not reasoning. Reserve Opus for the final behavioral pattern analysis in Phase 3 if Sonnet's outputs feel shallow.

### ADR-4: Tiered emotion analysis — start cheap, upgrade if needed

**Decision:** Three tiers, implemented incrementally:

| Tier | Tool | What It Gives You | Cost | When to Add |
|------|------|-------------------|------|-------------|
| 1 | **NRCLex** + **VADER** | 10 emotion categories + sentiment polarity. Fast, no GPU, processes thousands of conversations in minutes. | Free | Phase 3 (immediate) |
| 2 | **GoEmotions** (HuggingFace) | 27 fine-grained categories: admiration, confusion, curiosity, disappointment, embarrassment, nervousness, remorse. Far more nuanced for personal struggle conversations. | Free (GPU helpful) | Phase 3 (if Tier 1 is too coarse) |
| 3 | **LIWC-22** | 90+ psychological dimensions: analytical thinking, authenticity, cognitive processes, depression markers, coping mechanisms. | ~$100 license | Only if clinical depth needed |

**Why not start with GoEmotions:** It needs a GPU or runs slowly on CPU. NRCLex gives you a working emotional timeline in 10 minutes. Upgrade when you know the system works.

### ADR-5: Basic Memory over Graphiti for the knowledge graph

**Decision:** Use Basic Memory (`basicmachines-co/basic-memory`) for the temporal knowledge graph.

**Why Basic Memory wins:**
- Stores everything in standard Markdown files compatible with Obsidian — your knowledge graph IS your Obsidian vault
- Has explicit personal knowledge management templates (life domains, weekly reviews, goal tracking, energy/mood patterns)
- MCP integration means Claude Desktop can traverse the graph directly
- No external database infrastructure needed

**Why not Graphiti:** Graphiti is more powerful (temporal context graphs, hybrid retrieval, Neo4j/FalkorDB backends) but requires Neo4j or FalkorDB running. That's infrastructure overhead for a personal project. If the system outgrows Basic Memory, Graphiti is the upgrade path.

**Why not Mem0:** Well-funded (41K stars, $24M Series A) but more suited for application memory layers than personal knowledge management. Its Chrome extension is interesting for future capture but not relevant for processing historical data.

### ADR-6: Obsidian as the visualization and query layer

**Decision:** Don't build a custom web UI. Use Obsidian with targeted plugins.

**Plugin stack:**
- **Smart Connections** (100K+ users) — semantic search across the vault, surfaces related notes
- **Obsidian Tracker** — line charts, bar charts, calendar heatmaps from frontmatter fields (emotional tracking)
- **Chronos Timeline** — interactive timelines from Markdown, AI-assisted generation
- **Dataview** — SQL-like queries across all notes (the backbone of analytics)
- **Mood Tracker** — embeddable emotion graphs (radar, polar, line)
- **Charts View** — bar, pie, radar, treemap, word cloud visualizations
- **Heatmap Calendar** — GitHub-style activity visualization

**Why not a custom React/web app:** Building and maintaining a UI is weeks of work that doesn't advance the analysis goal. Obsidian already has everything needed, and the plugin ecosystem keeps improving without your effort.

### ADR-7: L1/L2 cache architecture for the wiki layer

**Decision:** Adopt the MehmetGoekce/llm-wiki L1/L2 pattern.

- **L1 (always loaded):** Core identity, key preferences, major life events, persistent behavioral patterns. Loaded into every Claude session as system prompt context. Small — under 4,000 tokens.
- **L2 (loaded on demand):** Domain-specific wiki articles (CRM project details, learning history, relationship dynamics). Retrieved via MCP search when a query touches that domain.

**Why this matters:** Without this separation, every query either loads too much context (slow, expensive) or too little (misses connections). L1 gives Claude the "who is Hayk" foundation; L2 gives it the specific knowledge needed for the current question.

### ADR-8: Evidence-first retrieval — wiki summaries are not enough

**Decision:** Build a retrieval service that can answer from wiki articles AND drill down to raw source chunks with explicit evidence links.

**Why:** Wiki articles are compiled summaries. They're great for "remind me about the CRM migration" but insufficient for "what exactly did I say about connection pooling on March 15th?" or "find evidence that I led the ClickHouse migration." The system must support both:
- **Fast path:** query → wiki article → answer (good enough 80% of the time)
- **Evidence path:** query → chunk-level search → raw messages → grounded answer with source citations

Without this, the system becomes a "trust the summary" tool rather than an "inspect the evidence" tool. The Grok PRD's emphasis on evidence linking and confidence scores is correct and incorporated here.

### ADR-9: Layered retrieval pipeline over simple search

**Decision:** Build a multi-step retrieval pipeline instead of relying solely on MyChatArchive's built-in search or Obsidian's Smart Connections.

**Pipeline steps:**
1. **Query analysis** — classify intent (fact lookup, timeline, decision review, pattern analysis, interview story, agent brief)
2. **Filter construction** — infer project, date range, entities, topics
3. **Candidate retrieval** — hybrid: semantic similarity + keyword/BM25 + metadata filters
4. **Reranking** — by topical relevance, project match, time proximity, tag overlap
5. **Context expansion** — pull adjacent messages/chunks to restore conversational meaning
6. **Answer generation** — grounded output with explicit references to evidence IDs

**Why this matters:** Semantic search alone returns "related" results. Adding metadata filters returns "relevant to this project/period" results. Adding reranking returns "most useful" results. Adding context expansion returns "understandable" results. Each step increases answer quality.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         QUERY LAYER                              │
│                                                                  │
│   Claude Desktop / Claude Code + MCP Servers                     │
│   ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│   │ Basic Memory │  │ MyChatArchive│  │ obra/knowledge-    │     │
│   │ MCP Server   │  │ MCP Server   │  │ graph MCP Server   │     │
│   │ (wiki +      │  │ (raw convs,  │  │ (graph traversal,  │     │
│   │  graph)      │  │  search)     │  │  PageRank, claims) │     │
│   └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘     │
│          │                 │                    │                 │
└──────────┼─────────────────┼────────────────────┼────────────────┘
           │                 │                    │
┌──────────▼─────────────────▼────────────────────▼────────────────┐
│                      STORAGE LAYER                               │
│                                                                  │
│   Obsidian Vault (Markdown)          SQLite (MyChatArchive DB)   │
│   ┌────────────────────┐             ┌──────────────────────┐    │
│   │ wiki/              │             │ conversations        │    │
│   │   L1-identity.md   │             │ messages             │    │
│   │   crm-migration.md │             │ embeddings           │    │
│   │   learning-rust.md │             │ chunks               │    │
│   │ analysis/          │             │ classifications      │    │
│   │   emotional-arc.md │             │ tags                 │    │
│   │   topic-evolution/ │             │ entities             │    │
│   │ timeline/          │             │ evidence_links       │    │
│   │ stories/           │             │ decisions            │    │
│   │   leadership.md    │             │ query_log            │    │
│   │   technical.md     │             └──────────────────────┘    │
│   └────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────┘
           ▲                          ▲
           │                          │
┌──────────┴──────────────────────────┴────────────────────────────┐
│                    PROCESSING PIPELINE                           │
│                                                                  │
│  Phase 0: MyChatArchive ingests raw JSON → SQLite                │
│  Phase 1: Claude Batch API classifies each conversation          │
│  Phase 2: Claude Batch API compiles wiki articles from clusters  │
│  Phase 3: NRCLex/BERTopic/ruptures analyze patterns over time   │
│  Phase 4: Basic Memory builds temporal knowledge graph           │
│  Phase 5: Retrieval service with hybrid search + reranking       │
│  Phase 6: Results written as Obsidian Markdown + frontmatter     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
           ▲
           │
┌──────────┴──────────────────────────────────────────────────────┐
│                       RAW DATA                                   │
│  data/raw/conversations.json (or sharded: conversations-NNN.json)│
│  ~2GB, ~2000+ conversations, 4 years                            │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow summary:**
1. Raw ChatGPT JSON → MyChatArchive → SQLite database (parsed, deduplicated, embedded)
2. SQLite conversations → chunking service → chunks table with embeddings
3. Chunks → Claude Batch API → classification metadata + extracted entities/decisions (stored back in SQLite)
4. Classified conversations clustered by topic → Claude Batch API → wiki articles (Obsidian Markdown)
5. Conversation text → NRCLex (emotion scores) + BERTopic (topic evolution) + ruptures (change points)
6. All outputs → Obsidian vault with frontmatter → visualized via plugins
7. Retrieval service queries both SQLite (chunks, evidence) and Obsidian (wiki articles) for grounded answers
8. MCP servers connect Claude to everything for conversational querying

---

## 3. Data Model

This schema extends MyChatArchive's existing tables. We ADD tables to MyChatArchive's SQLite database rather than creating a separate one.

### Core tables (added by us to MyChatArchive's DB)

```sql
-- Retrievable content units. A chunk is a slice of one or more
-- adjacent messages within a single conversation, sized for
-- embedding and retrieval.
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    message_start_id TEXT NOT NULL,
    message_end_id TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER,
    chunk_summary TEXT,              -- LLM-generated 1-sentence summary
    embedding BLOB,                  -- vector embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Per-conversation structured metadata extracted by Claude
CREATE TABLE IF NOT EXISTS classifications (
    conv_id TEXT PRIMARY KEY,
    categories TEXT,                 -- JSON array: ["work/crm", "technical/database"]
    emotions TEXT,                   -- JSON array of {emotion, intensity, context}
    decisions_made TEXT,             -- JSON array of strings
    lessons_learned TEXT,            -- JSON array of strings
    people_mentioned TEXT,           -- JSON array of strings
    outcome TEXT,                    -- "success" | "failure" | "ongoing" | "unclear" | "trivial"
    time_period TEXT,                -- "2023-Q1"
    key_topics TEXT,                 -- JSON array of strings
    summary TEXT,                    -- 2-3 sentence summary
    raw_llm_response TEXT,           -- full Claude response for debugging
    confidence REAL DEFAULT 0.0,     -- how confident the LLM was (0.0–1.0)
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conv_id) REFERENCES conversations(id)
);

-- Named entities extracted from conversations
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,       -- person, project, skill, tool, organization, etc.
    normalized_name TEXT,            -- canonical form for dedup
    first_seen TEXT,                 -- "2023-Q1"
    last_seen TEXT,
    description TEXT,
    UNIQUE(normalized_name, entity_type)
);

-- Junction: which chunks mention which entities
CREATE TABLE IF NOT EXISTS chunk_entities (
    chunk_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    relevance REAL DEFAULT 0.5,      -- 0.0–1.0
    extraction_method TEXT,          -- "llm" | "rule" | "manual"
    PRIMARY KEY (chunk_id, entity_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(id),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
);

-- Tags with types (project, topic, intent, emotional, behavioral)
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tag_type TEXT NOT NULL,          -- "project" | "topic" | "intent" | "emotional" | "behavioral"
    description TEXT
);

-- Junction: which chunks have which tags
CREATE TABLE IF NOT EXISTS chunk_tags (
    chunk_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    extraction_method TEXT,          -- "llm" | "rule" | "manual"
    PRIMARY KEY (chunk_id, tag_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);

-- Extracted decisions with evidence trails
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    project_name TEXT,
    title TEXT NOT NULL,
    description TEXT,
    decision_date_estimate TEXT,
    status TEXT,                     -- "made" | "deferred" | "reversed" | "unclear"
    confidence REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Universal evidence linker: connects any object to any other object
-- This is the critical table that makes "evidence-first" work
CREATE TABLE IF NOT EXISTS evidence_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,       -- "chunk" | "conversation" | "wiki_article" | "decision"
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,       -- "decision" | "entity" | "tag" | "wiki_article" | "story"
    target_id TEXT NOT NULL,
    relation_type TEXT,              -- "supports" | "contradicts" | "part_of" | "caused_by" | "led_to"
    confidence REAL DEFAULT 0.5,
    context TEXT,                    -- brief explanation of how they're linked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Interview stories / STAR examples extracted from evidence
CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    competency TEXT,                 -- "leadership" | "technical" | "problem-solving" | "collaboration"
    situation TEXT,
    task TEXT,
    action TEXT,
    result TEXT,
    source_chunk_ids TEXT,           -- JSON array of chunk IDs that support this story
    project_name TEXT,
    time_period TEXT,
    confidence REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Log of queries for debugging and improving retrieval
CREATE TABLE IF NOT EXISTS query_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    query_mode TEXT,                 -- "fact" | "timeline" | "decision" | "pattern" | "story" | "brief"
    filters_json TEXT,
    retrieved_chunk_ids TEXT,        -- JSON array
    output_text TEXT,
    user_rating INTEGER,            -- optional: 1-5 rating for retrieval quality
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tag taxonomy (seeded during Phase 1)

```sql
-- Project tags
INSERT INTO tags (id, name, tag_type) VALUES
    ('proj_crm', 'CRM', 'project'),
    ('proj_payment', 'Payment Gateway', 'project'),
    ('proj_personal', 'Personal Growth', 'project'),
    ('proj_interview', 'Interview Prep', 'project'),
    ('proj_learning', 'Learning', 'project'),
    ('proj_ai_kb', 'AI Knowledge System', 'project');

-- Topic tags
INSERT INTO tags (id, name, tag_type) VALUES
    ('top_architecture', 'Architecture', 'topic'),
    ('top_database', 'Database', 'topic'),
    ('top_clickhouse', 'ClickHouse', 'topic'),
    ('top_postgresql', 'PostgreSQL', 'topic'),
    ('top_leadership', 'Leadership', 'topic'),
    ('top_performance', 'Performance', 'topic'),
    ('top_system_design', 'System Design', 'topic');

-- Intent tags
INSERT INTO tags (id, name, tag_type) VALUES
    ('int_decision', 'Decision', 'intent'),
    ('int_problem', 'Problem', 'intent'),
    ('int_postmortem', 'Postmortem', 'intent'),
    ('int_plan', 'Plan', 'intent'),
    ('int_achievement', 'Achievement', 'intent'),
    ('int_lesson', 'Lesson Learned', 'intent');

-- Emotional/behavioral tags
INSERT INTO tags (id, name, tag_type) VALUES
    ('emo_anxiety', 'Anxiety', 'emotional'),
    ('emo_overwhelm', 'Overwhelm', 'emotional'),
    ('emo_avoidance', 'Avoidance', 'behavioral'),
    ('emo_motivation', 'Motivation', 'emotional'),
    ('emo_recovery', 'Recovery', 'behavioral'),
    ('emo_perfectionism', 'Perfectionism', 'behavioral'),
    ('emo_confidence', 'Confidence', 'emotional');
```

---

## 4. Phase 0 — Foundation: Ingest & Store

**Goal:** Get all 2GB of conversations into a searchable SQLite database with vector embeddings. Have a working MCP server for basic querying immediately.

**Time estimate:** 1-2 days (mostly waiting for embeddings to compute)

### Step 0.1: Install MyChatArchive

```bash
# In WSL
git clone https://github.com/1ch1n/chat-export-structurer.git
cd chat-export-structurer
pip install -r requirements.txt
```

### Step 0.2: Prepare ChatGPT export

```bash
mkdir -p data/raw
unzip chatgpt-export.zip -d data/raw/
```

### Step 0.3: Run ingestion

```bash
# Consult MyChatArchive's README for exact CLI commands
python structurer.py import --source chatgpt --path data/raw/conversations.json
```

**What this produces:**
- SQLite database with all conversations parsed, messages extracted, tree structure flattened
- SHA1-based dedup (safe to re-import if you get a new export later)
- Local vector embeddings via sentence-transformers
- Working MCP server you can connect to Claude Desktop

### Step 0.4: Verify and explore

```bash
sqlite3 brain.db "SELECT COUNT(*) FROM conversations;"
sqlite3 brain.db "SELECT title, datetime(create_time, 'unixepoch') FROM conversations ORDER BY create_time LIMIT 20;"
```

### Step 0.5: Add our custom tables

```bash
# Run our schema additions on top of MyChatArchive's database
sqlite3 brain.db < scripts/schema/001_add_chunks.sql
sqlite3 brain.db < scripts/schema/002_add_classifications.sql
sqlite3 brain.db < scripts/schema/003_add_entities_tags.sql
sqlite3 brain.db < scripts/schema/004_add_decisions_evidence.sql
sqlite3 brain.db < scripts/schema/005_add_stories_querylog.sql
sqlite3 brain.db < scripts/schema/006_seed_tags.sql
```

### Step 0.6: Generate chunks from conversations

```python
# Chunk conversations into retrievable units
# Conversation-aware: don't split mid-exchange
# Each chunk = 1-5 message pairs (user + assistant)
# Overlap: include last message of previous chunk as first of next

import sqlite3
import hashlib

db = sqlite3.connect("brain.db")

for conv_id, in db.execute("SELECT id FROM conversations"):
    messages = db.execute("""
        SELECT id, role, content, timestamp 
        FROM messages 
        WHERE conversation_id = ? 
        ORDER BY sequence_number
    """, (conv_id,)).fetchall()
    
    # Group into chunks of ~2000 tokens each
    # Keep user+assistant pairs together
    chunks = create_conversation_chunks(messages, max_tokens=2000, overlap=1)
    
    for chunk in chunks:
        chunk_id = hashlib.sha256(chunk["text"].encode()).hexdigest()[:16]
        db.execute("""
            INSERT OR IGNORE INTO chunks 
            (id, conversation_id, message_start_id, message_end_id, 
             chunk_text, token_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chunk_id, conv_id, chunk["start_msg_id"], 
              chunk["end_msg_id"], chunk["text"], chunk["tokens"]))

db.commit()
```

### Step 0.7: Connect MCP server to Claude Desktop

```json
{
  "mcpServers": {
    "my-brain": {
      "command": "python",
      "args": ["path/to/chat-export-structurer/mcp_server.py"],
      "env": {
        "DATABASE_PATH": "path/to/brain.db"
      }
    }
  }
}
```

**⚠️ HUMAN CHECKPOINT 0:** After ingestion, spot-check 10-20 conversations. Verify titles, timestamps, message content. Check chunk boundaries — do they break at natural points?

---

## 5. Phase 1 — Classification: Tag Every Conversation

**Goal:** Add structured metadata (categories, emotions, decisions, outcomes) to every conversation AND extract entities, decisions, and evidence links at the chunk level.

**Time estimate:** 3-5 days (prompt iteration + batch processing + review)

### Step 1.1: Test classification prompt on 10-20 conversations manually

Before running a batch on 2000+ conversations, test the prompt (see Section 12.1) on a diverse sample:
- 2-3 CRM/work conversations
- 2-3 learning conversations
- 2-3 personal/emotional conversations
- 2-3 philosophy/reflection conversations
- 2-3 short/trivial conversations

```python
import anthropic
import json

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2000,
    system=CLASSIFICATION_SYSTEM_PROMPT,  # Section 12.1
    messages=[{"role": "user", "content": conv_text}]
)

result = json.loads(response.content[0].text)
print(json.dumps(result, indent=2))
```

**⚠️ HUMAN CHECKPOINT 1A:** Review the 10-20 test classifications:
- Are the categories right? Do you need categories that aren't in the taxonomy?
- Are the emotion labels meaningful? Too broad? Too narrow?
- Are decisions and lessons being extracted accurately?
- Are short/trivial conversations being handled well (marked as low-value)?
- Revise the prompt and taxonomy based on findings.

### Step 1.2: Run classification batch

```python
import anthropic
import json
import sqlite3

client = anthropic.Anthropic()

db = sqlite3.connect("brain.db")
conversations = db.execute("""
    SELECT c.id, c.title, GROUP_CONCAT(m.content, '\n---\n')
    FROM conversations c
    JOIN messages m ON m.conversation_id = c.id
    LEFT JOIN classifications cl ON cl.conv_id = c.id
    WHERE cl.conv_id IS NULL
    GROUP BY c.id
""").fetchall()

requests = []
for conv_id, title, content in conversations:
    truncated = content[:80000] if len(content) > 80000 else content
    
    requests.append({
        "custom_id": conv_id,
        "params": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": CLASSIFICATION_SYSTEM_PROMPT,
            "messages": [{
                "role": "user",
                "content": f"Conversation title: {title}\n\n{truncated}"
            }]
        }
    })

batch = client.messages.batches.create(requests=requests)
print(f"Batch submitted: {batch.id}")

# Poll and process results (see Phase 1 detailed code in scripts/03_classify_batch.py)
```

### Step 1.3: Extract entities and decisions at the chunk level

After conversation-level classification, run a second batch on individual chunks to extract fine-grained entities and decisions:

```python
# For chunks belonging to conversations classified as containing decisions
decision_chunks = db.execute("""
    SELECT ch.id, ch.chunk_text, c.title, cl.categories
    FROM chunks ch
    JOIN conversations c ON ch.conversation_id = c.id
    JOIN classifications cl ON cl.conv_id = c.id
    WHERE cl.decisions_made != '[]'
""").fetchall()

# Send each chunk to Claude for entity + decision extraction
# (See Section 12.5 for the entity extraction prompt)
# Store results in entities, chunk_entities, decisions, evidence_links tables
```

### Step 1.4: Generate classification report

```python
import pandas as pd

df = pd.read_sql("""
    SELECT categories, outcome, time_period, summary
    FROM classifications
""", db)

# Show distribution: how many conversations per category, per time period
```

**⚠️ HUMAN CHECKPOINT 1B:** Review the classification distribution report. Also spot-check 5-10 entity extractions and decision records — are they accurate? Are confidence scores reasonable?

---

## 6. Phase 2 — Wiki Layer: Compile Knowledge

**Goal:** Group related conversations and compile them into synthesized wiki articles. Build the L1 identity document and L2 domain articles. Maintain evidence links from wiki articles back to source chunks.

**Time estimate:** 3-5 days

### Step 2.1: Cluster conversations by topic

```python
from collections import defaultdict

clusters = defaultdict(list)
for row in db.execute("""
    SELECT conv_id, categories, key_topics, summary 
    FROM classifications
"""):
    primary_cat = json.loads(row[1])[0] if row[1] else "uncategorized"
    clusters[primary_cat].append({
        "id": row[0],
        "topics": json.loads(row[2]),
        "summary": row[3]
    })
```

### Step 2.2: Build the L1 identity document

Target: under 4,000 tokens. Loaded into every Claude session.

Save as `vault/wiki/L1-identity.md` with YAML frontmatter:
```yaml
---
type: identity
layer: L1
last_compiled: 2026-04-10
source_conversations: 2147
token_count: 3800
---
```

(See Section 12.2 for the full L1 compilation prompt)

### Step 2.3: Compile L2 domain wiki articles via Batch API

```python
requests = []
for cluster_name, conversations in clusters.items():
    conv_ids = [c["id"] for c in conversations]
    full_text = load_conversations_text(db, conv_ids)
    
    if len(full_text) > 150000:
        full_text = build_representative_sample(conversations, db)
    
    requests.append({
        "custom_id": f"wiki_{cluster_name}",
        "params": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "system": WIKI_COMPILATION_PROMPT,  # Section 12.3
            "messages": [{
                "role": "user",
                "content": f"Topic cluster: {cluster_name}\n"
                           f"Number of conversations: {len(conversations)}\n"
                           f"Time span: {get_time_span(conversations)}\n\n"
                           f"{full_text}"
            }]
        }
    })
```

### Step 2.4: Save wiki articles as Obsidian Markdown with evidence links

```python
for article in compiled_articles:
    filename = f"vault/wiki/{article['slug']}.md"
    
    frontmatter = f"""---
type: wiki
layer: L2
category: {article['category']}
source_conversations: {json.dumps(article['source_conv_ids'])}
source_chunks: {json.dumps(article['source_chunk_ids'])}
time_span: {article['time_span']}
last_compiled: {article['compiled_at']}
cross_references: {json.dumps(article['cross_refs'])}
token_count: {article['token_count']}
---

"""
    with open(filename, 'w') as f:
        f.write(frontmatter + article['content'])
    
    # Create evidence links from wiki article to source chunks
    for chunk_id in article['source_chunk_ids']:
        db.execute("""
            INSERT INTO evidence_links 
            (source_type, source_id, target_type, target_id, relation_type)
            VALUES ('chunk', ?, 'wiki_article', ?, 'supports')
        """, (chunk_id, article['slug']))
```

### Step 2.5: Cross-reference pass

```python
# Send all wiki article summaries to Claude, ask it to identify connections
# Add [[wikilinks]] between related articles
```

**⚠️ HUMAN CHECKPOINT 2:** Read 5-10 wiki articles, especially:
- The L1 identity document (does it capture who you are?)
- A CRM-related article (is the technical detail accurate?)
- A personal/emotional article (does it feel right? Not too clinical?)
- Check cross-references and evidence links — can you trace back to source?

---

## 7. Phase 3 — Emotional & Behavioral Analysis

**Goal:** Build emotional timelines, detect behavioral patterns, find change points where something shifted in your life.

**Time estimate:** 5-7 days (this is the most analytically rich phase)

### Step 3.1: Emotion scoring with NRCLex (Tier 1 — immediate)

```python
from nrclex import NRCLex
import pandas as pd
from datetime import datetime

emotion_records = []

for conv_id, content, timestamp in db.execute("""
    SELECT c.id, GROUP_CONCAT(m.content, ' '), c.create_time
    FROM conversations c
    JOIN messages m ON m.conversation_id = c.id
    WHERE m.role = 'user'  -- Only analyze YOUR messages, not the AI's
    GROUP BY c.id
"""):
    nrc = NRCLex(content)
    scores = nrc.affect_frequencies
    emotion_records.append({
        "conv_id": conv_id,
        "timestamp": datetime.fromtimestamp(timestamp),
        **scores
    })

emotion_df = pd.DataFrame(emotion_records)
emotion_df = emotion_df.set_index("timestamp").sort_index()
weekly_emotions = emotion_df.resample("W").mean()
```

### Step 3.2: Change point detection with ruptures

```python
import ruptures as rpt

for emotion in ["sadness", "anger", "joy", "fear", "trust"]:
    signal = weekly_emotions[emotion].dropna().values
    if len(signal) < 10:
        continue
    
    algo = rpt.Pelt(model="rbf").fit(signal)
    change_points = algo.predict(pen=3)
    
    dates = weekly_emotions[emotion].dropna().index
    change_dates = [dates[cp-1] for cp in change_points if cp < len(dates)]
    
    print(f"\n{emotion.upper()} — shift points detected:")
    for d in change_dates:
        print(f"  {d.strftime('%Y-%m-%d')}")
```

### Step 3.3: Topic evolution with BERTopic

```python
from bertopic import BERTopic

docs = []
timestamps = []

for conv_id, content, ts in db.execute("""
    SELECT c.id, GROUP_CONCAT(m.content, ' '), c.create_time
    FROM conversations c
    JOIN messages m ON m.conversation_id = c.id
    WHERE m.role = 'user'
    GROUP BY c.id
"""):
    docs.append(content[:2000])
    timestamps.append(datetime.fromtimestamp(ts))

topic_model = BERTopic(verbose=True)
topics, probs = topic_model.fit_transform(docs)

topics_over_time = topic_model.topics_over_time(docs, timestamps, nr_bins=20)
fig = topic_model.visualize_topics_over_time(topics_over_time)
fig.write_html("vault/analysis/topic-evolution.html")

fig2 = topic_model.visualize_hierarchy()
fig2.write_html("vault/analysis/topic-hierarchy.html")
```

### Step 3.4: Behavioral pattern detection via Claude

```python
analysis_package = f"""
## Emotional Timeline Summary
{weekly_emotions.describe().to_string()}

## Change Points Detected
{format_change_points(all_change_points)}

## Topic Evolution Summary  
{format_topic_evolution(topics_over_time)}

## Classification Distribution Over Time
{format_classification_trends(classification_df)}

## All Conversation Summaries (chronological)
{format_all_summaries(classifications)}
"""

response = client.messages.create(
    model="claude-sonnet-4-20250514",  # or opus for deeper analysis
    max_tokens=8000,
    system=BEHAVIORAL_ANALYSIS_PROMPT,  # Section 12.4
    messages=[{"role": "user", "content": analysis_package}]
)
```

### Step 3.5: Seasonality and cyclical pattern detection

```python
from statsmodels.tsa.seasonal import seasonal_decompose

for emotion in ["sadness", "joy", "anger"]:
    series = weekly_emotions[emotion].dropna()
    if len(series) > 52:
        decomposition = seasonal_decompose(series, period=52, model='additive')
        decomposition.plot()
```

### Step 3.6: Generate analysis Markdown for Obsidian

```python
with open("vault/analysis/emotional-arc.md", "w") as f:
    f.write("""---
type: analysis
category: emotional-timeline
---

# Emotional Arc: 2022-2026

## Change Points
""")
    for emotion, dates in all_change_points.items():
        for d in dates:
            f.write(f"- **{d.strftime('%B %Y')}**: {emotion} baseline shifted\n")
    
    f.write("\n## Behavioral Patterns\n")
    f.write(behavioral_analysis_response)
```

**⚠️ HUMAN CHECKPOINT 3:** This is the most important review point:
- Do the change points correspond to real life events you remember?
- Are the behavioral patterns accurate or is the system seeing noise?
- Are there patterns you recognize but would rather not have surfaced?
- Does the emotional arc feel true?

---

## 8. Phase 4 — Temporal Knowledge Graph

**Goal:** Build a knowledge graph that tracks how facts, beliefs, and priorities changed over time.

**Time estimate:** 3-5 days

### Step 4.1: Install and configure Basic Memory

```bash
pip install basic-memory
basic-memory init --vault-path ./vault
```

### Step 4.2: Define entity types

```python
ENTITY_TYPES = {
    "person": "People mentioned in conversations",
    "project": "Work projects, personal projects, learning projects",
    "skill": "Technical or personal skills being developed",
    "belief": "Core beliefs, values, philosophical positions",
    "concern": "Worries, fears, recurring anxieties",
    "goal": "Explicit or implicit goals",
    "decision": "Significant decisions and their outcomes",
    "coping_mechanism": "How challenges were handled",
    "tool": "Software, frameworks, libraries used",
}

RELATIONSHIP_TYPES = {
    "works_with": "person → person",
    "works_on": "person → project", 
    "struggles_with": "self → concern (temporal)",
    "learns": "self → skill (temporal)",
    "decides": "self → decision",
    "uses": "self → coping_mechanism (temporal)",
    "evolves_to": "belief → belief (tracks how thinking changed)",
    "triggers": "event → emotion",
    "resolves": "decision → concern",
}
```

### Step 4.3: Extract entities and relationships via Batch API

```python
requests = []
for article in wiki_articles:
    requests.append({
        "custom_id": article["slug"],
        "params": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 3000,
            "system": ENTITY_EXTRACTION_PROMPT,  # Section 12.5
            "messages": [{"role": "user", "content": article["content"]}]
        }
    })
```

### Step 4.4: Build the graph in Basic Memory

Each entity and relationship becomes an Obsidian note with temporal metadata. Basic Memory handles the graph structure and MCP integration.

### Step 4.5: Connect obra/knowledge-graph MCP

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "node",
      "args": ["path/to/obra/knowledge-graph/server.js"],
      "env": { "DATABASE_PATH": "path/to/graph.db" }
    }
  }
}
```

Provides: Louvain community detection, PageRank, prove-claim skill.

**⚠️ HUMAN CHECKPOINT 4 (soft):** Check entity/relationship accuracy.

---

## 9. Phase 5 — Retrieval Service: Evidence-Grounded Answers

**Goal:** Build a retrieval pipeline that answers questions with evidence from raw chunks, not just wiki summaries. Support multiple output modes.

**Time estimate:** 3-5 days

### Step 5.1: Implement the retrieval pipeline

```python
# scripts/retrieval/pipeline.py

class RetrievalPipeline:
    def __init__(self, db_path: str, embedding_model):
        self.db = sqlite3.connect(db_path)
        self.embedder = embedding_model
    
    def answer(self, query: str, mode: str = "auto", 
               project: str = None, date_range: tuple = None) -> dict:
        """
        Main entry point. Returns grounded answer with evidence.
        
        Modes: fact, timeline, decision_review, pattern, 
               interview_story, agent_brief
        """
        # Step 1: Query analysis
        if mode == "auto":
            mode = self.classify_query(query)
        
        # Step 2: Filter construction
        filters = self.build_filters(query, project, date_range)
        
        # Step 3: Candidate retrieval (hybrid)
        candidates = self.hybrid_search(query, filters)
        
        # Step 4: Reranking
        ranked = self.rerank(candidates, query, mode)
        
        # Step 5: Context expansion
        expanded = self.expand_context(ranked[:10])
        
        # Step 6: Answer generation
        answer = self.generate_answer(query, expanded, mode)
        
        # Log the query
        self.log_query(query, mode, filters, ranked, answer)
        
        return answer
    
    def classify_query(self, query: str) -> str:
        """Classify query intent using Claude."""
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            system="Classify this query into one mode: fact, timeline, "
                   "decision_review, pattern, interview_story, agent_brief. "
                   "Respond with just the mode name.",
            messages=[{"role": "user", "content": query}]
        )
        return response.content[0].text.strip()
    
    def hybrid_search(self, query: str, filters: dict) -> list:
        """Combine semantic + keyword + metadata search."""
        # Semantic: embed query, find similar chunks
        query_embedding = self.embedder.encode(query)
        semantic_results = self.vector_search(query_embedding, top_k=50)
        
        # Keyword: FTS5 search on chunk_text
        keyword_results = self.fts_search(query, top_k=50)
        
        # Metadata: filter by project/date/entity/tag
        if filters:
            metadata_results = self.metadata_search(filters, top_k=50)
        else:
            metadata_results = []
        
        # Merge and deduplicate
        return self.merge_results(semantic_results, keyword_results, 
                                  metadata_results)
    
    def rerank(self, candidates: list, query: str, mode: str) -> list:
        """Score candidates by relevance to query + mode."""
        for c in candidates:
            score = c["base_score"]
            
            # Boost if chunk has matching project tag
            if self.has_project_match(c, query):
                score *= 1.5
            
            # Boost decision-like chunks for decision_review mode
            if mode == "decision_review" and self.is_decision_chunk(c):
                score *= 1.3
            
            # Boost story-like chunks for interview_story mode
            if mode == "interview_story" and self.is_achievement_chunk(c):
                score *= 1.3
            
            # Recency boost for pattern mode
            if mode == "pattern":
                score *= self.recency_weight(c)
            
            c["final_score"] = score
        
        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    
    def expand_context(self, chunks: list) -> list:
        """Pull adjacent messages around each chunk for context."""
        expanded = []
        for chunk in chunks:
            # Get 2 messages before and after the chunk
            surrounding = self.db.execute("""
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                AND sequence_number BETWEEN 
                    (SELECT sequence_number FROM messages WHERE id = ?) - 2
                AND (SELECT sequence_number FROM messages WHERE id = ?) + 2
                ORDER BY sequence_number
            """, (chunk["conversation_id"], 
                  chunk["message_start_id"], 
                  chunk["message_end_id"])).fetchall()
            
            chunk["expanded_context"] = surrounding
            expanded.append(chunk)
        
        return expanded
    
    def generate_answer(self, query: str, evidence: list, mode: str) -> dict:
        """Generate grounded answer with source citations."""
        evidence_text = self.format_evidence(evidence)
        
        # Load L1 identity context
        l1 = open("vault/wiki/L1-identity.md").read()
        
        # Load relevant L2 wiki articles
        l2_articles = self.find_relevant_wiki(query)
        
        system_prompt = self.get_mode_prompt(mode)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": f"""
Identity context:
{l1}

Wiki context:
{l2_articles}

Raw evidence (cite by [chunk_id]):
{evidence_text}

Question: {query}
"""}]
        )
        
        return {
            "answer": response.content[0].text,
            "evidence_ids": [e["id"] for e in evidence],
            "mode": mode,
            "wiki_articles_used": [a["slug"] for a in l2_articles]
        }
```

### Step 5.2: Build CLI interface

```python
# scripts/cli.py
import click

@click.group()
def cli():
    pass

@cli.command()
@click.argument("question")
@click.option("--project", default=None)
@click.option("--mode", default="auto")
@click.option("--date-from", default=None)
@click.option("--date-to", default=None)
def answer(question, project, mode, date_from, date_to):
    """Ask a question and get a grounded answer."""
    pipeline = RetrievalPipeline("brain.db", embedder)
    result = pipeline.answer(question, mode=mode, project=project)
    
    click.echo(f"\n{'='*60}")
    click.echo(f"Mode: {result['mode']}")
    click.echo(f"Evidence chunks: {len(result['evidence_ids'])}")
    click.echo(f"Wiki articles: {result['wiki_articles_used']}")
    click.echo(f"{'='*60}\n")
    click.echo(result["answer"])

@cli.command()
@click.argument("question")
@click.option("--project", default=None)
def timeline(question, project):
    """Generate a timeline for a topic."""
    pipeline = RetrievalPipeline("brain.db", embedder)
    result = pipeline.answer(question, mode="timeline", project=project)
    click.echo(result["answer"])

@cli.command()
@click.option("--project", default=None)
@click.option("--competency", default=None)
def stories(project, competency):
    """Extract STAR interview stories."""
    pipeline = RetrievalPipeline("brain.db", embedder)
    result = pipeline.answer(
        f"Find interview stories demonstrating {competency or 'leadership'} "
        f"in {project or 'all projects'}",
        mode="interview_story"
    )
    click.echo(result["answer"])

@cli.command()
@click.argument("task_description")
def agent_brief(task_description):
    """Generate a context pack for a coding agent."""
    pipeline = RetrievalPipeline("brain.db", embedder)
    result = pipeline.answer(task_description, mode="agent_brief")
    click.echo(result["answer"])
```

**Example usage:**

```bash
# Fact lookup
python cli.py answer "When did we start discussing ClickHouse migration?" --project CRM

# Decision review  
python cli.py answer "What were the weak decisions in the CRM project?" --mode decision_review

# Timeline
python cli.py timeline "CRM architecture changes" --project CRM

# Interview stories
python cli.py stories --project CRM --competency leadership

# Agent brief
python cli.py agent-brief "Implement decision analysis module for CRM project"

# Pattern analysis
python cli.py answer "What recurring causes lead me into procrastination?" --mode pattern
```

---

## 10. Phase 6 — Obsidian Visualization & MCP Query Interface

**Goal:** Make everything browsable, searchable, and visually rich in Obsidian. Connect all MCP servers.

**Time estimate:** 2-3 days

### Step 6.1: Install Obsidian plugins

```
1. Smart Connections — semantic search
2. Dataview — query engine
3. Obsidian Tracker — time-series charts from frontmatter
4. Chronos Timeline — interactive life timeline
5. Mood Tracker — emotional radar/polar charts
6. Charts View — general-purpose charts
7. Heatmap Calendar — activity visualization
```

### Step 6.2: Create Dataview dashboards

```markdown
# vault/dashboards/overview.md

## Conversations by Category
```dataview
TABLE length(rows) AS Count
FROM "wiki"
GROUP BY category
SORT length(rows) DESC
```

## Recent Change Points
```dataview
TABLE emotion, date, context
FROM "analysis/change-points"
SORT date DESC
LIMIT 10
```

## Active Concerns (Unresolved)
```dataview
LIST
FROM "wiki"
WHERE contains(cross_references, "concern") AND outcome != "resolved"
```

## Key Decisions
```dataview
TABLE project_name, status, time_period
FROM "decisions"
SORT decision_date_estimate DESC
```
```

### Step 6.3: Connect all MCP servers to Claude Desktop

```json
{
  "mcpServers": {
    "my-brain": {
      "command": "python",
      "args": ["path/to/chat-export-structurer/mcp_server.py"]
    },
    "basic-memory": {
      "command": "basic-memory",
      "args": ["serve"]
    },
    "knowledge-graph": {
      "command": "node", 
      "args": ["path/to/obra/knowledge-graph/server.js"]
    }
  }
}
```

**⚠️ HUMAN CHECKPOINT 5:** Overall: does this system help you understand yourself? Can you ask a question and trust the answer because you can see the evidence?

---

## 11. Project Structure

```
personal-kb/
├── data/
│   ├── raw/                          # Original ChatGPT export (gitignored)
│   │   └── conversations.json
│   └── brain.db                      # MyChatArchive SQLite + our tables (gitignored)
│
├── scripts/
│   ├── schema/                       # SQL migrations
│   │   ├── 001_add_chunks.sql
│   │   ├── 002_add_classifications.sql
│   │   ├── 003_add_entities_tags.sql
│   │   ├── 004_add_decisions_evidence.sql
│   │   ├── 005_add_stories_querylog.sql
│   │   └── 006_seed_tags.sql
│   │
│   ├── 01_ingest.py                  # Phase 0: run MyChatArchive import
│   ├── 02_chunk.py                   # Phase 0: generate chunks from conversations
│   ├── 03_classify_test.py           # Phase 1: test prompt on sample
│   ├── 04_classify_batch.py          # Phase 1: batch classification
│   ├── 05_extract_entities.py        # Phase 1: chunk-level entity/decision extraction
│   ├── 06_cluster.py                 # Phase 2: cluster conversations
│   ├── 07_compile_wiki_batch.py      # Phase 2: batch wiki compilation
│   ├── 08_crossref.py                # Phase 2: cross-reference pass
│   ├── 09_emotion_analysis.py        # Phase 3: NRCLex + ruptures
│   ├── 10_topic_evolution.py         # Phase 3: BERTopic
│   ├── 11_behavioral_analysis.py     # Phase 3: Claude deep analysis
│   ├── 12_entity_graph.py            # Phase 4: knowledge graph entities
│   ├── 13_generate_obsidian.py       # Phase 6: write Obsidian Markdown
│   │
│   ├── retrieval/                    # Phase 5: retrieval service
│   │   ├── pipeline.py
│   │   ├── search.py
│   │   ├── reranker.py
│   │   └── answer_modes.py
│   │
│   ├── cli.py                        # CLI interface
│   │
│   └── prompts/
│       ├── classify.txt              # Section 12.1
│       ├── l1_identity.txt           # Section 12.2
│       ├── wiki_compile.txt          # Section 12.3
│       ├── behavioral_analysis.txt   # Section 12.4
│       ├── entity_extraction.txt     # Section 12.5
│       ├── interview_story.txt       # Section 12.6
│       └── agent_brief.txt           # Section 12.7
│
├── vault/                            # Obsidian vault
│   ├── wiki/
│   │   ├── L1-identity.md
│   │   ├── crm-report-migration.md
│   │   ├── learning-rust-journey.md
│   │   └── ...
│   ├── analysis/
│   │   ├── emotional-arc.md
│   │   ├── topic-evolution.html
│   │   ├── topic-hierarchy.html
│   │   └── change-points.md
│   ├── stories/
│   │   ├── leadership-under-pressure.md
│   │   ├── technical-improvements.md
│   │   └── ...
│   ├── timeline/
│   │   └── life-events.md
│   ├── dashboards/
│   │   ├── overview.md
│   │   └── emotional-tracker.md
│   └── .obsidian/
│
├── requirements.txt
├── .env.example                      # ANTHROPIC_API_KEY=
├── .gitignore                        # data/raw/, data/brain.db
└── README.md
```

---

## 12. Prompts Reference

### 12.1: Classification System Prompt

```
You are analyzing a personal conversation from a 4-year ChatGPT archive belonging to a software developer named Hayk. Your job is to extract structured metadata about THIS conversation.

Focus on HAYK's side — his questions, concerns, decisions, emotional state. The AI assistant's responses are context but not the subject of analysis.

Respond with ONLY valid JSON (no markdown fencing, no preamble):

{
  "categories": ["primary/sub", "secondary/sub"],
  "emotions": [
    {"emotion": "frustrated", "intensity": 0.7, "context": "deadline pressure"},
    {"emotion": "curious", "intensity": 0.9, "context": "exploring new framework"}
  ],
  "decisions_made": ["Chose X over Y because Z"],
  "lessons_learned": ["Learned that A leads to B"],
  "people_mentioned": ["person_name or role"],
  "outcome": "success | failure | ongoing | unclear | trivial",
  "time_period": "YYYY-QN",
  "key_topics": ["specific_topic_1", "specific_topic_2"],
  "summary": "2-3 sentences: what was this conversation about, what was Hayk trying to accomplish, what was the result?",
  "confidence": 0.85
}

Category taxonomy:
- work/crm — CRM project: features, bugs, architecture, migrations
- work/technical — general technical work, non-CRM coding
- work/team — colleague dynamics, management, workplace relationships
- work/career — career decisions, job concerns, professional growth
- learning/successful — learning that produced lasting skill/knowledge
- learning/abandoned — started learning something, stopped
- learning/ongoing — still actively learning
- personal/struggles — depression, anxiety, life difficulties, emotional processing
- personal/philosophy — philosophical discussions, meaning, values, worldview
- personal/relationships — family, friends, romantic, social dynamics
- personal/health — physical or mental health discussions
- meta/planning — goal setting, life planning, project planning
- meta/reflection — looking back, self-analysis, pattern recognition
- meta/dreams — aspirations, future visions, what-ifs

Rules:
- A conversation can have multiple categories (list all that apply)
- For emotions, score intensity 0.0-1.0 where 0.5 is neutral/mild, 0.8+ is strong
- If the conversation is trivial (small talk, single question), set outcome to "trivial"
- Be specific in key_topics — "postgresql connection pooling" not just "database"
- For people, use their name if mentioned, otherwise their role ("team lead", "friend")
- Set confidence 0.0-1.0 for how sure you are about the overall classification
- All metadata is INFERRED, not ground truth — mark appropriately
```

### 12.2: L1 Identity Compilation Prompt

```
You are compiling a core identity document from summaries of 2000+ personal conversations spanning 4 years. This document will be loaded into every future AI session as context about who Hayk is.

Target length: 3,000-4,000 tokens. Every sentence must earn its place.

Structure:

## Who I Am
Core identity: profession, values, what drives me. 2-3 sentences.

## Major Life Arc (2022-2026)
Chronological, 1-2 sentences per significant period. What was happening, what mattered most.

## Persistent Patterns
Behavioral patterns that show up repeatedly across years:
- Productive patterns (what works for me)
- Concerning patterns (cycles that cause harm)
- Decision-making tendencies

## Core Beliefs & Values
What I consistently care about across all domains.

## Key Relationships
The people who matter most and the dynamics at play. No gossip — just what's structurally important.

## Current State
Where things stand now. Active concerns, ongoing projects, immediate priorities.

## How I Communicate
My communication style, preferences, what I respond well to.

Write in first person ("I tend to..." not "Hayk tends to...") because this will be used as self-knowledge.
Be honest about negative patterns — this document is for self-awareness, not self-flattery.
```

### 12.3: Wiki Compilation Prompt

```
You are compiling a wiki article from multiple related conversations. These conversations all relate to the same topic from one person's life over several years.

Your job:
1. Synthesize key information across all conversations into one coherent article
2. Organize chronologically where relevant
3. Preserve important details, decisions, and outcomes — don't over-summarize
4. Note emotional context where it matters (not every conversation, but when emotions shaped decisions)
5. Target length: 1,500-3,000 words
6. Use markdown formatting
7. Include source references: when citing a specific fact or decision, note which conversation it came from using [conv_id] markers

Structure:
## Overview
What this topic is about, why it matters, time span.

## Timeline
Key events and developments, chronologically.

## Decisions & Outcomes  
What was decided, why, and what happened as a result.

## Lessons & Patterns
What was learned. What patterns repeated.

## People Involved
Who played a role and how.

## Connections
What other life domains does this connect to? (Reference as [[wiki-article-name]])

Write as a personal encyclopedia entry — something the person can read to quickly remember everything about this topic. Be concrete and specific, not vague and general.

DO NOT include information that wasn't in the source conversations. If something is unclear, say so.
```

### 12.4: Behavioral Pattern Analysis Prompt

```
You are a behavioral analyst examining 4 years of one person's life data. You have:
- Emotional time-series data showing weekly emotion scores
- Statistically detected change points (dates when emotional baselines shifted)
- Topic evolution data (what subjects dominated which periods)
- Classification summaries of all conversations

Your analysis should focus on:

1. **Recurring Cycles**: Identify loops — motivation → overcommit → burnout → recovery, or hope → attempt → failure → withdrawal. How long are the cycles? What triggers them?

2. **Coping Mechanisms**: How does this person handle difficulty? Do their strategies change over time? Which ones work?

3. **Growth Trajectory**: In what areas has genuine growth happened? Where has the person been stuck?

4. **Trigger-Response Patterns**: What situations consistently produce negative emotional responses? Positive ones?

5. **Decision Quality**: When does this person make good decisions? Bad ones? What conditions correlate?

6. **Blind Spots**: What patterns might this person NOT be aware of? What questions should they be asking themselves?

Be direct and honest. This person specifically asked for this analysis to understand themselves better, including uncomfortable truths. Don't be cruel, but don't soften important patterns.

Ground every observation in the data — cite specific time periods, topics, or change points.
```

### 12.5: Entity Extraction Prompt

```
Extract entities and relationships from this text for a temporal knowledge graph.

Return ONLY valid JSON:

{
  "entities": [
    {
      "name": "CRM Report Migration",
      "type": "project",
      "first_seen": "2023-Q1",
      "last_seen": "2023-Q3",
      "status": "completed",
      "description": "Migration of legacy reports to ClickHouse"
    }
  ],
  "relationships": [
    {
      "from": "Self",
      "to": "CRM Report Migration", 
      "type": "works_on",
      "time_start": "2023-Q1",
      "time_end": "2023-Q3",
      "context": "Led the migration, struggled with connection pooling"
    }
  ],
  "temporal_changes": [
    {
      "entity": "Self",
      "attribute": "attitude_toward",
      "target": "CRM Project",
      "from_state": "frustrated",
      "to_state": "accomplished",
      "change_period": "2023-Q2 to 2023-Q3",
      "trigger": "Successfully completed migration"
    }
  ],
  "decisions": [
    {
      "title": "Chose ClickHouse over TimescaleDB for reporting",
      "project": "CRM",
      "date_estimate": "2023-Q1",
      "status": "made",
      "reasoning": "Better for analytical queries on large datasets",
      "confidence": 0.8
    }
  ]
}

Entity types: person, project, skill, belief, concern, goal, decision, coping_mechanism, tool, organization
Relationship types: works_with, works_on, struggles_with, learns, decides, uses, evolves_to, triggers, resolves

Mark all extracted data as INFERRED. Focus on temporal_changes and decisions — these are the most valuable.
```

### 12.6: Interview Story Extraction Prompt

```
You are extracting STAR (Situation, Task, Action, Result) interview stories from evidence chunks about a software developer's work history.

For each story you identify, return:

{
  "stories": [
    {
      "title": "Led CRM Reporting Migration Under Deadline",
      "competency": "leadership | technical | problem-solving | collaboration | resilience",
      "situation": "The CRM reporting system was hitting performance limits...",
      "task": "I needed to migrate 200+ reports from PostgreSQL to ClickHouse...",
      "action": "I proposed a phased approach, designed the ETL pipeline...",
      "result": "Completed migration 2 weeks ahead of schedule, query times dropped 10x...",
      "source_evidence": ["chunk_id_1", "chunk_id_2"],
      "strength": 0.9,
      "project": "CRM"
    }
  ]
}

Rules:
- Only create stories that are well-supported by the evidence chunks
- Each story should demonstrate a clear competency
- Use the person's actual words and details where possible
- Rate strength 0.0-1.0 based on how complete and impressive the evidence is
- A strong story has clear situation, measurable result, and personal agency
```

### 12.7: Agent Brief Generation Prompt

```
You are generating a structured context brief for a coding agent (Claude Code, Codex, Cursor) that will work on a task related to this person's project history.

Given the task description and retrieved evidence, produce:

## Task Context
What the coding agent needs to know about the project, its history, and current state.

## Relevant Technical Decisions
Past decisions that affect how this task should be implemented. Include the reasoning.

## Known Constraints
Technical constraints, architectural patterns, and lessons learned that apply.

## Suggested Approach
Based on past experience and outcomes, recommend an implementation approach.

## References
List the source chunk IDs and wiki articles the agent should read for deeper context.

## Warnings
Any past failures, known pitfalls, or anti-patterns to avoid based on historical evidence.

Keep the brief under 2,000 tokens — enough context to start, not so much it overwhelms.
```

---

## 13. Cost Estimates

| Phase | API Calls | Input Tokens | Output Tokens | Batch Cost | Notes |
|-------|-----------|-------------|---------------|------------|-------|
| Phase 1 (classify) | ~2,000 | ~6M | ~1M | ~$17 | Sonnet Batch pricing |
| Phase 1 (entities) | ~500 | ~1.5M | ~500K | ~$6 | Chunk-level extraction |
| Phase 2 (wiki) | ~200 | ~2M | ~600K | ~$8 | Sonnet Batch |
| Phase 2 (L1) | 1 | ~50K | ~4K | ~$0.10 | Real-time API |
| Phase 2 (crossref) | ~50 | ~500K | ~200K | ~$2 | Batch |
| Phase 3 (behavioral) | 1-3 | ~100K | ~8K | ~$0.50 | Real-time, possibly Opus |
| Phase 4 (entities) | ~200 | ~2M | ~600K | ~$8 | Batch |
| Phase 5 (stories) | ~50 | ~300K | ~100K | ~$1.50 | Batch |
| **Total** | | | | **~$43** | |

NRCLex, BERTopic, ruptures, statsmodels — all free and local.

---

## 14. Human Checkpoints (Summary)

| Checkpoint | After | What to Review | Blocking? |
|-----------|-------|---------------|-----------|
| **HC-0** | Phase 0 (ingestion + chunks) | Spot-check 10-20 conversations + chunk boundaries | Yes |
| **HC-1A** | Phase 1 (test classify) | Review 10-20 test classifications, revise prompt/taxonomy | Yes |
| **HC-1B** | Phase 1 (full classify) | Review distribution report, check entity/decision accuracy | Soft |
| **HC-2** | Phase 2 (wiki) | Read L1 doc + 5-10 wiki articles, verify evidence links | Yes |
| **HC-3** | Phase 3 (analysis) | Validate change points against memory, review patterns | Yes |
| **HC-4** | Phase 4 (graph) | Check entity/relationship accuracy | Soft |
| **HC-5** | Phase 5+6 (retrieval + Obsidian) | End-to-end: ask questions, verify evidence grounding | Yes |

**"Blocking"** means: do not proceed to the next phase until this checkpoint passes.

---

## 15. Use Cases & Output Modes

### A. Project Memory and Technical Reasoning

```
"Show all important decisions related to the CRM project."
"When did we start discussing moving reports from PostgreSQL to ClickHouse?"
"Which decisions now look weak in hindsight?"
"Build a timeline of CRM architecture changes."
```
→ Uses: decision_review mode, timeline mode, project filter

### B. Career and Interview Preparation

```
"Find stories that demonstrate leadership under pressure."
"Turn my payment gateway experience into STAR answers."
"Extract examples where I improved reliability or scalability."
"Summarize my strongest technical achievements by project."
```
→ Uses: interview_story mode, stories table, competency filter

### C. Personal Reflection and Self-Analysis

```
"What recurring causes led me into procrastination cycles?"
"Compare the periods when I was disciplined versus when I collapsed."
"What patterns show up before I abandon routines?"
"Which habits consistently helped me recover?"
```
→ Uses: pattern mode, emotional timeline, change points

### D. Learning Support

```
"What have I already studied about Go, system design, Kafka?"
"What topics are still weak?"
"Build a revision plan from my previous study notes."
```
→ Uses: fact mode, learning/* category filter

### E. Agent Context Assembly

```
"Prepare a context pack for Claude Code to implement the CRM analysis feature."
"Create a briefing so Codex can continue the project from current state."
```
→ Uses: agent_brief mode, project filter, decision extraction

---

## Appendix A: Tools Quick Reference

| Tool | Purpose | Install | Phase |
|------|---------|---------|-------|
| MyChatArchive | Parse ChatGPT JSON → SQLite | `git clone 1ch1n/chat-export-structurer` | 0 |
| anthropic (Python SDK) | Claude Batch API | `pip install anthropic` | 1-4 |
| claude-batch-toolkit | Batch CLI convenience | `pip install claude-batch-toolkit` | 1-4 |
| NRCLex | Lexicon-based emotion scoring | `pip install NRCLex` | 3 |
| VADER | Sentiment polarity | `pip install vaderSentiment` | 3 |
| BERTopic | Topic modeling + evolution | `pip install bertopic` | 3 |
| ruptures | Change point detection | `pip install ruptures` | 3 |
| statsmodels | Seasonality detection | `pip install statsmodels` | 3 |
| sentence-transformers | Embeddings for chunks | `pip install sentence-transformers` | 0, 5 |
| Basic Memory | Temporal knowledge graph + MCP | `pip install basic-memory` | 4 |
| obra/knowledge-graph | Graph algorithms MCP | `npm install` | 4 |
| PyPlutchik | Plutchik wheel visualizations | `pip install pyplutchik` | 3 |

## Appendix B: Future Extensions (Not MVP)

| Tool | What It Adds | When to Add |
|------|-------------|-------------|
| **GoEmotions** (HuggingFace) | 27 fine-grained emotion categories instead of NRCLex's 10 | When Tier 1 emotions feel too coarse |
| **LIWC-22** | 90+ psychological dimensions, depression markers | When clinical-grade analysis is wanted |
| **Graphiti** (Zep) | Temporal context graphs with Neo4j, hybrid retrieval | When Basic Memory feels limiting |
| **Thinking-MCP** | Captures decision-making heuristics, not just facts | After wiki layer is stable |
| **BERTrend** | Weak signal detection — finds emerging concerns early | After BERTopic baseline works |
| **COG Second Brain** | 17 Claude Code skills for daily braindump → monthly insight cycle | When moving from historical analysis to ongoing journaling |
| **kytmanov/obsidian-llm-wiki-local** | 100% local wiki with Ollama, zero cloud | For privacy-sensitive reprocessing |
| **Mem0** | Universal memory layer across ChatGPT/Claude/Perplexity | For ongoing cross-platform memory capture |
| **InfraNodus** | 3D force-graph visualization with blind spot detection | For visual exploration of the knowledge graph |

## Appendix C: Key Research References

- **Karpathy LLM Wiki** (April 4, 2026) — The foundational pattern of LLM-compiled knowledge articles
- **Mind Mapper** (ACM 2025) — Multi-stage LLM pipeline for behavioral pattern extraction from conversations
- **PsychAdapter** (Nature, 2026) — Claude achieving 96.7% accuracy for depression/life satisfaction detection
- **Anthropic emotion vectors study** — 171 emotion vectors identified in Claude Sonnet, validating Claude as emotional analysis engine
- **Hedonometer project** (UVM Computational Story Lab) — 6 core emotional arc shapes, sliding-window methodology
- **MehmetGoekce/llm-wiki** — L1/L2 cache architecture for personal vs. situational knowledge
- **Steve Kinney Temporal + Batch API** — Production-grade durable batch execution pattern

## Appendix D: What's New vs. Previous Versions

This final version merges the best of three prior documents:

| From Our Implementation Guide (v2) | From Grok PRD | New in This Version |
|------|------|------|
| MyChatArchive for ingestion | Full relational data model with evidence links | Chunks table with message-level traceability |
| Python-only stack | Hybrid retrieval pipeline (semantic + keyword + filters + reranking) | RetrievalPipeline class with 6-step pipeline |
| Obsidian + plugins for visualization | Decision extraction as first-class feature | `decisions` and `evidence_links` tables |
| NRCLex/BERTopic/ruptures for analysis | Interview story extraction (STAR format) | `stories` table + extraction prompt |
| Basic Memory for knowledge graph | Agent brief generation | Agent brief prompt + CLI command |
| L1/L2 cache architecture | Confidence scores on all inferred metadata | `confidence` field on all LLM-derived data |
| Claude Batch API for cost | Query logging for retrieval improvement | `query_log` table |
| Human checkpoints between phases | Multiple output modes | 5 explicit output modes with mode-specific prompts |
