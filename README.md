# Expedia Context Agent

[![Neo4j](https://img.shields.io/badge/Neo4j-AuraDB-blue?logo=neo4j)](https://neo4j.com/cloud/aura/)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude-orange)](https://anthropic.com)

GraphRAG-powered customer service agent for flight disruptions, refunds, and policy resolution.

## Live Demo

**Frontend:** https://context-graph-travel.vercel.app  
**Backend API:** https://context-graph-travel-production.up.railway.app

---

## What This Demos

A live AI agent that handles Expedia customer service scenarios using a Neo4j knowledge graph. The key distinction from a standard RAG chatbot: every answer is grounded in **graph traversal** — the agent follows relationships across customers, bookings, carrier agreements, loyalty tiers, weather memos, and policy sections to reach decisions a text search would miss entirely.

**Three capabilities on display:**

- **GraphRAG** — hybrid vector + multi-hop graph retrieval across policy knowledge base
- **Context Graph** — live graph visualization updates as the agent works, showing exactly which nodes and relationships were used
- **Agent Memory** — conversation context, extracted entities, and detected preferences persist in Neo4j across sessions

## Graph Data Model

```
(:Customer)-[:HAS_TIER]->(:LoyaltyTier)-[:GRANTS]->(:Benefit)
(:Customer)-[:MADE]->(:Booking)-[:OPERATED_BY]->(:PartnerAirline)
(:Booking)-[:ON_ROUTE]->(:Route)<-[:COVERS]-(:Region)<-[:ACTIVE_FOR]-(:WeatherMemo)
(:Booking)-[:GOVERNED_BY]->(:CarrierAgreement)-[:APPLIES_TO]->(:PartnerAirline)
(:Booking)-[:DISRUPTED_BY]->(:Event)
(:Policy)-[:HAS_SECTION]->(:PolicySection)-[:REFERENCED_BY]->(:PolicySection)
(:Session)-[:MADE_DECISION]->(:Decision)-[:BASED_ON]->(:PolicySection)
```

## Demo Scenarios

### Disruption & Refunds
- Process a refund for Sarah Chen on booking EXP-991 — her Maui flight was canceled due to the Pacific storm
- What refund is James Okafor entitled to for his disrupted booking EXP-887?

### Multi-hop GraphRAG
These questions require 4–6 hops across the graph. Naive text search returns partial answers; the graph connects them correctly.

- Which customers affected by the Pacific storm qualify for the automatic $50 Platinum goodwill credit?
- Tom Reyes wants to cancel his ORD→Miami booking — what cancellation fees apply given his Blue tier and no active weather waiver on that route?
- What is the fastest possible refund timeline for Sarah Chen on EXP-991, combining her Gold status, the Alaska Airlines agreement, and the active Pacific storm waiver?
- If Maya Patel's ORD→Miami flight gets disrupted, is there any active weather waiver covering her route, and what would her Silver tier entitle her to?

### Policy Lookup
- Is there an active weather waiver affecting Alaska Airlines flights to Hawaii?
- What is Expedia's refund policy for involuntary cancellations?
- What fee waivers apply to Gold loyalty members?
- What are the refund terms under the Alaska Airlines carrier agreement?

### Customer Intelligence
- Show me all Gold and Platinum customers with their disrupted bookings
- Which customers have points+cash mixed payment bookings affected by the Pacific storm?
- What past refund decisions have been recorded for storm cancellations?

## Quick Start

```bash
# 1. Copy and fill in credentials
cp .env.example .env

# 2. Install dependencies
make install

# 3. Seed the graph (requires Neo4j AuraDB or local Neo4j)
make seed

# 4. Start backend + frontend
make start
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Neo4j Browser:** http://localhost:7474 *(local only)*

## Architecture

```
/
├── backend/              FastAPI + Anthropic Tools agentic loop
│   ├── app/
│   │   ├── agent.py      Tool definitions + agentic loop
│   │   ├── config.py     Settings (pydantic-settings + .env)
│   │   ├── context_graph_client.py  Neo4j driver + SSE collector
│   │   ├── memory.py     Agent memory (Neo4j Memory SDK)
│   │   └── routes.py     SSE streaming endpoint
│   └── scripts/
│       └── generate_data.py
├── frontend/             Next.js 15 + Chakra UI v3 + Neo4j NVL
│   ├── app/page.tsx      3-panel layout (Chat / Graph / Traces)
│   └── components/
│       ├── ChatInterface.tsx        SSE streaming chat
│       ├── ContextGraphView.tsx     Live graph (NVL)
│       └── DecisionTracePanel.tsx   Decision audit trail
├── rag/
│   └── graphrag.py       Hybrid vector + graph retrieval
├── cypher/
│   └── schema.cypher     Neo4j constraints + vector indexes
├── data/
│   └── seed.py           Sample data generator
├── .env.example          Configuration template
└── Makefile              Dev commands
```

## Agent Tools

| Tool | Description |
|------|-------------|
| `get_customer` | Customer profile, loyalty tier, and benefits |
| `get_booking` | Booking details — carrier, route, payment, disruption |
| `search_policies` | GraphRAG hybrid search across policy KB + carrier agreements + weather memos |
| `get_active_weather` | Weather memos affecting a booking's route (Booking → Route → Region → WeatherMemo) |
| `find_weather_waivers` | Active waivers by airline or destination — no booking required |
| `record_decision` | Write a Decision node with policy citations for audit trail |
| `find_precedents` | Semantic search over past decisions |
| `issue_refund` | Mock refund action (demo) |
| `execute_cypher` | Read-only Cypher escape hatch |
| `get_schema` | Graph schema lookup |

## Environment Variables

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `NEO4J_URI` | Neo4j connection URI (Aura or bolt://) |
| `NEO4J_USERNAME` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `ANTHROPIC_API_KEY` | Claude API key |
| `MEMORY_BACKEND` | `bolt` (self-hosted Neo4j) or `nams` (hosted) |
| `DOMAIN_ID` | Domain identifier — set to `expedia-customer-service` |
| `BACKEND_PORT` | Default: 8000 |
| `FRONTEND_PORT` | Default: 3000 |

## Roadmap

### Agent Memory — Graph-native Persistence
The agent already extracts entities and preferences per conversation. Next step is making this **visible and queryable** as a first-class graph feature:
- Dedicated **Memory panel** in the UI showing what the agent has learned about each customer across sessions — past interactions, stated preferences, inferred travel patterns
- `CustomerMemory` nodes linked to `Customer` via `REMEMBERS` relationships, surfaced in the context graph alongside the live query
- Preference drift tracking — graph edges showing when a preference changed and why

### Precedent Nodes — Decision Provenance as a Graph
Currently decisions are written as `Decision` nodes with policy citations. The roadmap extends this to a full provenance graph:
- `Precedent` nodes linking similar past decisions — "this refund was approved because a structurally identical case was approved in March"
- `(:Decision)-[:CITES_PRECEDENT]->(:Decision)` edges created automatically when the agent finds a matching prior case
- `find_precedents` tool upgraded from keyword search to graph traversal over the precedent chain
- UI: precedent chain visible in the Traces panel, decision audit trail navigable hop-by-hop

### RAG vs GraphRAG Comparison
Side-by-side view showing for each tool call:
- What **vector search alone** would have returned
- What **graph traversal added** on top
- Which nodes in the graph are vector matches vs. graph-expanded — color-coded in the visualization

### Structural Similarity via FastRP
Complement text embeddings with **FastRP graph embeddings** (structural similarity across the knowledge graph). Use case: find past cases that are structurally identical even when the text is different — e.g. a weather disruption on United looks the same structurally as one on Alaska, so the agent can apply the same policy path.

### Graph Data Science — Impact Analysis
- **Community detection** (Louvain) to find clusters of related disruption events and affected customers
- **PageRank** on policy sections to surface the most-cited rules
- **Shortest path** between a customer and a weather memo to explain the disruption chain in plain language

---

## Troubleshooting

**Backend can't connect to Neo4j**
- Verify `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `.env`
- For AuraDB use `neo4j+s://` URI scheme
- Run `make test-connection` to validate

**GraphRAG policy search fails**
- The `rag/graphrag.py` retriever uses a synchronous Neo4j driver — credentials are patched at call time from `settings`, so they don't need to be in `os.environ` separately

**Port conflict**
- Change `BACKEND_PORT` or `FRONTEND_PORT` in `.env`
- Kill existing: `lsof -ti:8000 | xargs kill`

**Frontend build errors**
- Requires Node.js 18+
- Delete `node_modules/` and rerun `npm install`
