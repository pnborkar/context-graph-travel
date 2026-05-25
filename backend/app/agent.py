"""Travel Context Graph — Customer Service Agent (Anthropic Tools).

Tools:
  get_customer          — look up customer profile + loyalty tier
  get_booking           — retrieve booking details for a customer
  search_policies       — GraphRAG hybrid search across policy KB
  get_active_weather    — active weather memos for a booking's route
  record_decision       — write a Decision node to the context graph
  find_precedents       — semantic search over past decisions
  issue_refund          — mock refund action (demo)
  execute_cypher        — generic read-only Cypher escape hatch
  get_schema            — graph schema lookup
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import sys

from app.config import settings

if not os.environ.get("ANTHROPIC_API_KEY"):
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

# Pydantic settings reads .env but does NOT write to os.environ.
# The synchronous GraphRAG driver (rag/graphrag.py → config.py) uses os.getenv(),
# so we propagate the credentials here before config.py is ever imported.
if settings.neo4j_uri:
    os.environ.setdefault("NEO4J_URI", settings.neo4j_uri)
    os.environ.setdefault("NEO4J_USERNAME", settings.neo4j_username)
    os.environ.setdefault("NEO4J_PASSWORD", settings.neo4j_password)

# Make our rag/ and memory/ modules importable from the parent project
# 2 levels up: app/ -> backend/ -> frontend/ (where rag/ and config.py live)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import anthropic
from app.context_graph_client import execute_cypher, get_schema
from app.memory import store_message, get_context, resolve_session_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Travel AI Customer Service Agent powered by a Neo4j knowledge graph.
You handle flight refunds, cancellations, and travel disruptions for customers.

DATABASE SCHEMA — use these EXACT property names in any Cypher you write:
Nodes:
  Customer:       id, name, email, loyalty_tier (Blue/Silver/Gold/Platinum), member_since, total_points, preferred_channel
  Booking:        id, ref, status (active/disrupted/refunded), payment_type (Points/Cash/Mixed),
                  points_amount, cash_amount, departure_date
  PartnerAirline: id, name, code
  Route:          id, origin, destination, destination_name
  Region:         id, name, code (e.g. PACIFIC, NORTHEAST, SOUTHEAST)
  LoyaltyTier:    tier, min_points, max_points, annual_fee_waiver
  Benefit:        type, description, fee_waiver (bool), priority_refund (bool)
  Policy:         id, name, version
  PolicySection:  id, title, text, section_number
  CarrierAgreement: id, airline_name, content
  WeatherMemo:    id, memo_number, title, text, active (bool), expiry_date, region_code
  Event:          id, name, type
  Decision:       id, decision_type, value, reasoning, made_at
  Session:        id, active, created_at

Key relationships:
  (:Customer)-[:MADE]->(:Booking)
  (:Customer)-[:HAS_TIER]->(:LoyaltyTier)-[:GRANTS]->(:Benefit)
  (:Booking)-[:OPERATED_BY]->(:PartnerAirline)
  (:Booking)-[:ON_ROUTE]->(:Route)
  (:Booking)-[:DISRUPTED_BY]->(:Event)
  (:Booking)-[:GOVERNED_BY]->(:CarrierAgreement)
  (:CarrierAgreement)-[:APPLIES_TO]->(:PartnerAirline)
  (:WeatherMemo)-[:ACTIVE_FOR]->(:Region)-[:COVERS]->(:Route)
  (:Policy)-[:HAS_SECTION]->(:PolicySection)
  (:PolicySection)-[:REFERENCED_BY]->(:PolicySection)
  (:Session)-[:MADE_DECISION]->(:Decision)
  (:Decision)-[:BASED_ON]->(:PolicySection)

DECISION PROCESS — follow this order for EVERY question, no exceptions:
1. Look up the customer (get_customer) to know their loyalty tier and benefits
2. Get their disrupted booking (get_booking) for carrier, route, and payment details
3. Search policies (search_policies) using their specific situation as the query
4. Check active weather memos (get_active_weather) for their booking
5. For weather waiver questions without a customer: use find_weather_waivers(airline, destination)
6. For other analytics/list queries: use execute_cypher with CORRECT schema
7. ALWAYS call record_decision with the session_id given in the [CONTEXT] header
8. Confirm the outcome with clear citations

MANDATORY: You MUST call record_decision on EVERY request before answering.
- For refund/cancellation: decision_type="refund_authorized" or "denied"
- For policy lookups: decision_type="policy_lookup"
- For analytics queries: decision_type="analytics_query"
- The session_id to pass is printed in [CONTEXT] at the start of each message.
- confidence_score: 0.0–1.0 reflecting how clearly the policy evidence supports the decision (0.95 = explicit policy match, 0.7 = inferred, 0.5 = ambiguous)
- risk_factors: JSON array of relevant risk strings e.g. '["mixed_payment","international_route","no_weather_waiver"]'

RESPONSE FORMAT — always include:
- The answer to the customer's question with specific data from the graph
- Which policy sections or agreements authorise any decisions
- The decision record ID as an audit reference

CYPHER GUIDELINES — when using execute_cypher, ALWAYS return full node objects so the graph panel updates:
  CORRECT: MATCH (c:Customer)-[r:MADE]->(b:Booking)-[o:OPERATED_BY]->(a:PartnerAirline) RETURN c, r, b, o, a LIMIT 25
  WRONG:   MATCH (c:Customer)-[:MADE]->(b:Booking) RETURN c.name, b.ref, b.total_amount
  Always include relationships (r, o, etc.) in RETURN alongside the nodes.
  For analytics, also add columns for display: RETURN c, r, b, o, a, c.loyalty_tier AS tier, b.status AS status

CRITICAL: Call tools directly — no preamble. Call the tool, then respond with findings."""


client = anthropic.AsyncAnthropic()

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict] = {}


def register_tool(name: str, description: str):
    def decorator(func):
        TOOL_REGISTRY[name] = {"function": func, "description": description}
        return func
    return decorator


# -- Customer & booking lookup -----------------------------------------------

@register_tool("get_customer", "Look up a customer profile, loyalty tier, and tier benefits by name or email")
async def get_customer(query: str) -> str:
    cypher = """
        MATCH (c:Customer)
        WHERE toLower(c.name) CONTAINS toLower($query)
           OR toLower(c.email) CONTAINS toLower($query)
        MATCH (c)-[r1:HAS_TIER]->(lt:LoyaltyTier)
        MATCH (lt)-[r2:GRANTS]->(ben:Benefit)
        RETURN c, lt, r1, r2, ben,
               c.id AS customer_id, c.name AS name, c.email AS email,
               c.loyalty_tier AS tier, c.member_since AS member_since,
               c.total_points AS total_points, c.preferred_channel AS preferred_channel,
               collect({type: ben.type, description: ben.description,
                        fee_waiver: ben.fee_waiver, priority_refund: ben.priority_refund}) AS benefits
    """
    result = await execute_cypher(cypher, {"query": query}, tool_name="get_customer")
    return json.dumps(result, default=str)


@register_tool("get_booking", "Get booking details including carrier, route, payment type, and disruption event for a customer")
async def get_booking(customer_id: str) -> str:
    cypher = """
        MATCH (c:Customer {id: $customer_id})-[r1:MADE]->(bkg:Booking)
        MATCH (bkg)-[r2:OPERATED_BY]->(pa:PartnerAirline)
        MATCH (bkg)-[r3:ON_ROUTE]->(rt:Route)
        OPTIONAL MATCH (bkg)-[r4:DISRUPTED_BY]->(e:Event)
        OPTIONAL MATCH (bkg)-[r5:GOVERNED_BY]->(ca:CarrierAgreement)
        OPTIONAL MATCH (ca)-[r6:APPLIES_TO]->(pa2:PartnerAirline)
        RETURN c, bkg, pa, rt, e, ca, pa2, r1, r2, r3, r4, r5, r6,
               bkg.id AS booking_id, bkg.ref AS ref, bkg.status AS status,
               bkg.payment_type AS payment_type,
               bkg.points_amount AS points_amount, bkg.cash_amount AS cash_amount,
               bkg.departure_date AS departure_date,
               rt.origin AS origin, rt.destination AS destination,
               rt.destination_name AS destination_name,
               pa.name AS carrier_name, pa.code AS carrier_code,
               e.name AS disruption, e.type AS disruption_type,
               ca.airline_name AS agreement_carrier, ca.id AS agreement_id
        ORDER BY bkg.departure_date DESC
    """
    result = await execute_cypher(cypher, {"customer_id": customer_id}, tool_name="get_booking")
    return json.dumps(result, default=str)


# -- GraphRAG policy search --------------------------------------------------

@register_tool("search_policies", "GraphRAG hybrid search — vector + multi-hop graph traversal across policy sections, carrier agreements, and weather memos. Use the customer's specific situation as the query.")
async def search_policies(query: str, customer_id: str = "") -> str:
    try:
        # Patch the sync-driver config module directly — os.environ.setdefault only runs
        # once at agent import time, but config.py constants are cached at first import.
        import config as _rag_config
        if settings.neo4j_uri:
            _rag_config.NEO4J_URI = settings.neo4j_uri
            _rag_config.NEO4J_USER = settings.neo4j_username
            _rag_config.NEO4J_PASSWORD = settings.neo4j_password
        if settings.openai_api_key:
            _rag_config.OPENAI_API_KEY = settings.openai_api_key

        from rag.graphrag import GraphRAGRetriever
        retriever = GraphRAGRetriever()
        result = retriever.retrieve(query=query, customer_id=customer_id or None)
        context = retriever.format_context_for_llm(result)
        retriever.close()

        # Emit matched nodes + relationships so the graph panel shows full context.
        section_ids = [m.id for m in result.policy_matches if m.id]
        carrier_ids = [c.id for c in result.carrier_agreements if c.id]
        memo_ids = [w.id for w in result.weather_memos if w.id]
        if section_ids or carrier_ids or memo_ids:
            viz_cypher = """
                OPTIONAL MATCH (p:Policy)-[r1:HAS_SECTION]->(ps:PolicySection)
                WHERE ps.id IN $section_ids
                WITH collect(DISTINCT p) AS policies, collect(DISTINCT r1) AS pol_rels,
                     collect(DISTINCT ps) AS sections
                OPTIONAL MATCH (ca:CarrierAgreement)-[r2:APPLIES_TO]->(pa:PartnerAirline)
                WHERE ca.id IN $carrier_ids
                WITH policies, pol_rels, sections,
                     collect(DISTINCT ca) AS agreements, collect(DISTINCT r2) AS ca_rels,
                     collect(DISTINCT pa) AS airlines
                OPTIONAL MATCH (wm:WeatherMemo)-[r3:ACTIVE_FOR]->(reg:Region)-[r4:COVERS]->(rt:Route)
                WHERE wm.id IN $memo_ids
                RETURN policies, pol_rels, sections, agreements, ca_rels, airlines,
                       collect(DISTINCT wm) AS memos, collect(DISTINCT r3) AS wm_rels,
                       collect(DISTINCT reg) AS regions, collect(DISTINCT r4) AS reg_rels,
                       collect(DISTINCT rt) AS routes
            """
            try:
                await execute_cypher(viz_cypher, {
                    "section_ids": section_ids[:8],
                    "carrier_ids": carrier_ids[:3],
                    "memo_ids": memo_ids[:3],
                }, tool_name="search_policies")
            except Exception:
                pass  # viz failure is non-critical

        return json.dumps({
            "context": context,
            "reasoning_path": result.reasoning_path,
            "policy_sections_found": len(result.policy_matches),
            "carrier_agreements_found": len(result.carrier_agreements),
            "active_weather_memos": len([w for w in result.weather_memos if w.active]),
        }, default=str)
    except Exception as e:
        logger.error("GraphRAG search failed: %s", e, exc_info=True)
        return json.dumps({"error": str(e)})


# -- Weather memos -----------------------------------------------------------

@register_tool("get_active_weather", "Get active weather memos affecting a booking's route — traverse Booking → Route → Region → WeatherMemo")
async def get_active_weather(booking_id: str) -> str:
    cypher = """
        MATCH (bkg:Booking {id: $booking_id})-[r1:ON_ROUTE]->(rt:Route)
        MATCH (reg:Region)-[r2:COVERS]->(rt)
        MATCH (wm:WeatherMemo)-[r3:ACTIVE_FOR]->(reg)
        WHERE wm.active = true
        RETURN bkg, rt, reg, wm, r1, r2, r3,
               wm.id AS memo_id, wm.memo_number AS memo_number,
               wm.title AS title, wm.text AS text,
               wm.region_code AS region, wm.expiry_date AS expires
    """
    result = await execute_cypher(cypher, {"booking_id": booking_id}, tool_name="get_active_weather")
    return json.dumps(result, default=str)


@register_tool("find_weather_waivers", "Find active weather waivers by airline name or destination — traverses WeatherMemo → Region → Route and optionally links to PartnerAirline bookings. Use for weather questions without a specific customer.")
async def find_weather_waivers(airline: str = "", destination: str = "") -> str:
    cypher = """
        MATCH (wm:WeatherMemo)-[r1:ACTIVE_FOR]->(reg:Region)-[r2:COVERS]->(rt:Route)
        WHERE wm.active = true
          AND ($destination = '' OR toLower(rt.destination_name) CONTAINS toLower($destination)
               OR toLower(rt.destination) CONTAINS toLower($destination))
        OPTIONAL MATCH (bkg:Booking)-[r3:ON_ROUTE]->(rt)
        OPTIONAL MATCH (bkg)-[r4:OPERATED_BY]->(pa:PartnerAirline)
        WHERE $airline = '' OR toLower(pa.name) CONTAINS toLower($airline)
        RETURN wm, r1, reg, r2, rt, bkg, r3, pa, r4,
               wm.id AS memo_id, wm.memo_number AS memo_number,
               wm.title AS title, wm.active AS active,
               wm.expiry_date AS expiry_date, wm.text AS memo_text,
               rt.origin AS origin, rt.destination AS destination,
               rt.destination_name AS destination_name, reg.name AS region_name
        LIMIT 50
    """
    result = await execute_cypher(cypher, {"airline": airline, "destination": destination}, tool_name="find_weather_waivers")
    return json.dumps(result, default=str)


# -- Decision trace ----------------------------------------------------------

@register_tool("record_decision", "Write a decision node to the context graph with full policy citations. Call this after determining the outcome.")
async def record_decision(
    session_id: str,
    decision_type: str,
    outcome: str,
    reasoning: str,
    policy_citations: str = "[]",
    confidence_score: str = "0.8",
    risk_factors: str = "[]",
) -> str:
    """
    decision_type: refund_authorized | fee_waived | escalate | rebook | denied | policy_lookup | analytics_query
    policy_citations: JSON array of policy section IDs e.g. '["ps-refund-involuntary","ps-loyalty-fee-waiver"]'
    confidence_score: 0.0-1.0 — how clearly the policy evidence supports this decision
    risk_factors: JSON array of risk strings e.g. '["mixed_payment","no_weather_waiver"]'
    """
    import asyncio
    import uuid

    try:
        citations = json.loads(policy_citations) if policy_citations else []
    except json.JSONDecodeError:
        citations = []

    try:
        risk_list = json.loads(risk_factors) if risk_factors else []
    except json.JSONDecodeError:
        risk_list = []

    try:
        confidence = float(confidence_score)
    except (ValueError, TypeError):
        confidence = 0.8

    decision_id = f"dec-{uuid.uuid4().hex[:8]}"

    # Generate embedding for similarity search
    embedding = None
    try:
        from rag.graphrag import embed as _embed
        embed_text = f"{decision_type} {outcome} {reasoning[:500]}"
        embedding = await asyncio.to_thread(_embed, embed_text)
    except Exception:
        pass

    cypher = """
        MERGE (sess:Session {id: $session_id})
        ON CREATE SET sess.active = true, sess.created_at = datetime()
        CREATE (d:Decision {
            id: $decision_id,
            decision_type: $decision_type,
            value: $outcome,
            reasoning: $reasoning,
            policy_citations: $citations,
            confidence_score: $confidence,
            risk_factors: $risk_list,
            made_at: datetime()
        })
        CREATE (sess)-[:MADE_DECISION]->(d)
        RETURN d.id AS decision_id
    """
    await execute_cypher(cypher, {
        "session_id": session_id,
        "decision_id": decision_id,
        "decision_type": decision_type,
        "outcome": outcome,
        "reasoning": reasoning,
        "citations": citations,
        "confidence": confidence,
        "risk_list": risk_list,
    }, tool_name="record_decision")

    # Store embedding on the Decision node
    if embedding:
        try:
            await execute_cypher(
                "MATCH (d:Decision {id: $id}) CALL db.create.setNodeVectorProperty(d, 'embedding', $embedding)",
                {"id": decision_id, "embedding": embedding},
                tool_name="record_decision_embed",
            )
        except Exception:
            pass

    # Link to cited policy sections
    for section_id in citations:
        try:
            await execute_cypher(
                """
                MATCH (d:Decision {id: $decision_id})
                MATCH (ps:PolicySection {id: $section_id})
                MERGE (d)-[:BASED_ON]->(ps)
                """,
                {"decision_id": decision_id, "section_id": section_id},
                tool_name="record_decision_link",
            )
        except Exception:
            pass

    get_collector().last_decision_id = decision_id

    return json.dumps({"decision_id": decision_id, "recorded": True})


@register_tool("find_precedents", "Find similar past decisions using vector similarity search — surfaces decisions with the same carrier, disruption type, or tier. Use this to cite consistent policy application.")
async def find_precedents(query: str, limit: str = "3") -> str:
    import asyncio
    try:
        from rag.graphrag import embed as _embed
        q_embedding = await asyncio.to_thread(_embed, query)
        cypher = """
            CALL db.index.vector.queryNodes('decision_embeddings', toInteger($limit), $embedding)
            YIELD node AS d, score
            OPTIONAL MATCH (sess:Session)-[:MADE_DECISION]->(d)
            OPTIONAL MATCH (sess)-[:FOR_CUSTOMER]->(c:Customer)
            RETURN d.id AS decision_id, d.decision_type AS type,
                   d.value AS outcome, d.reasoning AS reasoning,
                   d.policy_citations AS citations,
                   d.confidence_score AS confidence,
                   d.risk_factors AS risk_factors,
                   d.made_at AS decided_at,
                   c.name AS customer_name,
                   round(score * 100) / 100 AS similarity
            ORDER BY score DESC
        """
        result = await execute_cypher(cypher, {"limit": limit, "embedding": q_embedding}, tool_name="find_precedents")
    except Exception:
        # Fallback to recency scan if index not yet populated
        cypher = """
            MATCH (d:Decision)
            WHERE d.reasoning IS NOT NULL
            OPTIONAL MATCH (sess:Session)-[:MADE_DECISION]->(d)
            OPTIONAL MATCH (sess)-[:FOR_CUSTOMER]->(c:Customer)
            RETURN d.id AS decision_id, d.decision_type AS type,
                   d.value AS outcome, d.reasoning AS reasoning,
                   d.policy_citations AS citations,
                   d.confidence_score AS confidence,
                   d.risk_factors AS risk_factors,
                   d.made_at AS decided_at,
                   c.name AS customer_name
            ORDER BY d.made_at DESC
            LIMIT toInteger($limit)
        """
        result = await execute_cypher(cypher, {"limit": limit}, tool_name="find_precedents")
    return json.dumps(result, default=str)


# -- Mock action -------------------------------------------------------------

@register_tool("issue_refund", "Issue the refund — mock action for demo. Returns confirmation reference.")
async def issue_refund(booking_id: str, decision_id: str) -> str:
    import random, string
    ref = "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    cypher = """
        MATCH (bkg:Booking {id: $booking_id})
        SET bkg.status = 'refunded', bkg.refund_ref = $ref, bkg.refunded_at = datetime()
        RETURN bkg.ref AS booking_ref, bkg.points_amount AS points,
               bkg.cash_amount AS cash, $ref AS refund_ref
    """
    result = await execute_cypher(cypher, {
        "booking_id": booking_id, "ref": ref
    }, tool_name="issue_refund")
    return json.dumps(result, default=str)


# -- Generic escape hatch ----------------------------------------------------

@register_tool("execute_cypher", "Execute a read-only Cypher query against the knowledge graph")
async def run_cypher(query: str, parameters: str = "{}") -> str:
    try:
        params = json.loads(parameters) if parameters else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON parameters"})
    try:
        result = await execute_cypher(query, params, tool_name="execute_cypher")
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": f"Cypher query failed: {e}"})


@register_tool("get_schema", "Get the knowledge graph schema — node labels and relationship types")
async def get_graph_schema() -> str:
    result = await get_schema()
    return json.dumps(result, default=str)


# ---------------------------------------------------------------------------
# Build Anthropic tool definitions from registry
# ---------------------------------------------------------------------------

def _build_tool_definitions() -> list[dict]:
    tools = []
    for name, info in TOOL_REGISTRY.items():
        func = info["function"]
        sig = inspect.signature(func)
        properties: dict = {}
        required: list = []
        for pname, param in sig.parameters.items():
            ptype = "string"
            if param.annotation == int:
                ptype = "integer"
            elif param.annotation == float:
                ptype = "number"
            properties[pname] = {"type": ptype, "description": pname}
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        tools.append({
            "name": name,
            "description": info["description"],
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })
    return tools


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

async def handle_message(message: str, session_id: str | None = None) -> dict:
    session_id = resolve_session_id(session_id)
    await store_message(session_id, "user", message)
    context = await get_context(session_id, query=message)
    history = context.get("messages", [])

    session_header = f"[CONTEXT: session_id='{session_id}' — pass this to record_decision]\n\n"
    messages = history + [{"role": "user", "content": session_header + message}]
    tools = _build_tool_definitions()
    max_iterations = 15
    response_text = ""

    for _iteration in range(max_iterations):
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
            timeout=60.0,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_info = TOOL_REGISTRY.get(block.name)
                    if tool_info:
                        try:
                            result = await tool_info["function"](**block.input)
                        except Exception as tool_err:
                            result = json.dumps({"error": f"Tool error: {tool_err}"})
                    else:
                        result = json.dumps({"error": f"Unknown tool: {block.name}"})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result if isinstance(result, str) else json.dumps(result, default=str),
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            text_parts = [b.text for b in response.content if hasattr(b, "text")]
            response_text = "\n".join(text_parts)
            break
    else:
        response_text = "Maximum tool iterations reached — here is what I found so far."

    if not response_text.strip():
        response_text = "I searched the knowledge graph but could not find relevant results. Could you rephrase your question?"

    assistant_result = await store_message(session_id, "assistant", response_text)

    return {
        "response": response_text,
        "session_id": session_id,
        "graph_data": None,
        "entities_extracted": (assistant_result or {}).get("entities", []),
        "preferences_detected": (assistant_result or {}).get("preferences", []),
    }


async def handle_message_stream(message: str, session_id: str | None = None) -> dict:
    from app.context_graph_client import get_collector

    session_id = resolve_session_id(session_id)
    collector = get_collector()
    await store_message(session_id, "user", message)
    context = await get_context(session_id, query=message)
    history = context.get("messages", [])

    session_header = f"[CONTEXT: session_id='{session_id}' — pass this to record_decision]\n\n"
    messages = history + [{"role": "user", "content": session_header + message}]
    tools = _build_tool_definitions()
    max_iterations = 15
    response_text = ""

    try:
        for _iteration in range(max_iterations):
            logger.info("Agent iteration %d — calling Anthropic API", _iteration)
            full_text_parts: list[str] = []
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
                timeout=60.0,
            ) as stream:
                async for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and hasattr(event.delta, "text")
                    ):
                        collector.emit_text_delta(event.delta.text)
                        full_text_parts.append(event.delta.text)
                response = await stream.get_final_message()

            logger.info("Anthropic response: stop_reason=%s", response.stop_reason)
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.info("Calling tool: %s", block.name)
                        tool_info = TOOL_REGISTRY.get(block.name)
                        if tool_info:
                            try:
                                result = await tool_info["function"](**block.input)
                            except Exception as tool_err:
                                logger.error("Tool %s failed: %s", block.name, tool_err)
                                result = json.dumps({"error": f"Tool error: {tool_err}"})
                        else:
                            result = json.dumps({"error": f"Unknown tool: {block.name}"})
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result if isinstance(result, str) else json.dumps(result, default=str),
                        })
                messages.append({"role": "user", "content": tool_results})
                full_text_parts.clear()
            else:
                text_parts = [b.text for b in response.content if hasattr(b, "text")]
                response_text = "\n".join(text_parts)
                break
        else:
            response_text = "Maximum tool iterations reached."
    except Exception as e:
        logger.error("Streaming error: %s", e, exc_info=True)
        if not response_text:
            response_text = f"An error occurred: {e}"

    if not response_text.strip():
        response_text = "I searched the knowledge graph but could not find relevant results."

    assistant_result = await store_message(session_id, "assistant", response_text)
    if assistant_result:
        collector.emit_entities_extracted(assistant_result.get("entities", []))
        collector.emit_preferences_detected(assistant_result.get("preferences", []))
    collector.emit_done(response_text, session_id)

    return {"response": response_text, "session_id": session_id, "graph_data": None}
