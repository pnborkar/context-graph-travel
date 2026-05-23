"""
GraphRAG Retrieval Engine

Two-phase hybrid retrieval:
  Phase 1 — Vector search: embed the user query, find semantically
             similar PolicySections, CarrierAgreements, WeatherMemos
  Phase 2 — Graph expansion: from matched nodes, traverse relationships
             to pull in connected context (cross-doc links, tier benefits,
             active weather overrides, booking details)

The combined subgraph is serialized into structured text that Claude
receives as grounded context, with every claim traceable to a source node.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from openai import OpenAI
from config import get_driver, EMBEDDING_MODEL, OPENAI_API_KEY

_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        import config as _cfg
        _openai_client = OpenAI(api_key=_cfg.OPENAI_API_KEY)
    return _openai_client


def embed(text: str) -> list[float]:
    resp = get_openai_client().embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


# ── Data classes for retrieval results ───────────────────────

@dataclass
class PolicyMatch:
    id: str
    title: str
    text: str
    policy_name: str
    score: float
    source: str = "vector"          # "vector" | "graph_expansion"


@dataclass
class CarrierAgreementMatch:
    id: str
    airline_name: str
    airline_code: str
    text: str
    score: float


@dataclass
class WeatherMemoMatch:
    id: str
    memo_number: str
    title: str
    text: str
    active: bool
    region_code: str


@dataclass
class BookingContext:
    booking_id: str
    booking_ref: str
    customer_name: str
    loyalty_tier: str
    payment_type: str
    points_amount: float
    cash_amount: float
    destination: str
    carrier_name: str
    carrier_code: str
    booking_status: str
    disruption_event: str | None
    benefits: list[dict] = field(default_factory=list)


@dataclass
class RetrievalResult:
    query: str
    policy_matches: list[PolicyMatch] = field(default_factory=list)
    carrier_agreements: list[CarrierAgreementMatch] = field(default_factory=list)
    weather_memos: list[WeatherMemoMatch] = field(default_factory=list)
    booking: BookingContext | None = None
    reasoning_path: list[dict] = field(default_factory=list)   # for graph viz


# ── Main retriever ────────────────────────────────────────────

class GraphRAGRetriever:

    def __init__(self):
        self.driver = get_driver()

    def close(self):
        self.driver.close()

    # ── Phase 1: Vector search ────────────────────────────────

    def _vector_search_policies(self, embedding: list[float], top_k: int = 4) -> list[PolicyMatch]:
        with self.driver.session() as s:
            result = s.run("""
                CALL db.index.vector.queryNodes('policy_section_embedding', $top_k, $embedding)
                YIELD node AS ps, score
                MATCH (p:Policy)-[:HAS_SECTION]->(ps)
                RETURN ps.id AS id, ps.title AS title, ps.text AS text,
                       p.name AS policy_name, score
                ORDER BY score DESC
            """, top_k=top_k, embedding=embedding)
            return [
                PolicyMatch(
                    id=r["id"], title=r["title"], text=r["text"],
                    policy_name=r["policy_name"], score=round(r["score"], 4)
                )
                for r in result
            ]

    def _vector_search_carrier_agreements(self, embedding: list[float], top_k: int = 2) -> list[CarrierAgreementMatch]:
        with self.driver.session() as s:
            result = s.run("""
                CALL db.index.vector.queryNodes('carrier_agreement_embedding', $top_k, $embedding)
                YIELD node AS ca, score
                RETURN ca.id AS id, ca.airline_name AS airline_name,
                       ca.airline_code AS airline_code, ca.text AS text, score
                ORDER BY score DESC
            """, top_k=top_k, embedding=embedding)
            return [
                CarrierAgreementMatch(
                    id=r["id"], airline_name=r["airline_name"],
                    airline_code=r["airline_code"], text=r["text"],
                    score=round(r["score"], 4)
                )
                for r in result
            ]

    def _vector_search_weather_memos(self, embedding: list[float], top_k: int = 2) -> list[WeatherMemoMatch]:
        with self.driver.session() as s:
            result = s.run("""
                CALL db.index.vector.queryNodes('weather_memo_embedding', $top_k, $embedding)
                YIELD node AS wm, score
                RETURN wm.id AS id, wm.memo_number AS memo_number,
                       wm.title AS title, wm.text AS text,
                       wm.active AS active, wm.region_code AS region_code, score
                ORDER BY score DESC
            """, top_k=top_k, embedding=embedding)
            return [
                WeatherMemoMatch(
                    id=r["id"], memo_number=r["memo_number"], title=r["title"],
                    text=r["text"], active=r["active"], region_code=r["region_code"]
                )
                for r in result
            ]

    # ── Phase 2: Graph expansion ──────────────────────────────

    def _expand_cross_doc_links(self, section_ids: list[str]) -> list[PolicyMatch]:
        """Follow REFERENCED_BY and OVERRIDDEN_BY edges to pull in related sections."""
        if not section_ids:
            return []
        with self.driver.session() as s:
            result = s.run("""
                MATCH (ps:PolicySection)
                WHERE ps.id IN $section_ids
                MATCH (ps)-[:REFERENCED_BY]->(related:PolicySection)
                MATCH (p:Policy)-[:HAS_SECTION]->(related)
                RETURN DISTINCT related.id AS id, related.title AS title,
                       related.text AS text, p.name AS policy_name
            """, section_ids=section_ids)
            return [
                PolicyMatch(
                    id=r["id"], title=r["title"], text=r["text"],
                    policy_name=r["policy_name"], score=0.0, source="graph_expansion"
                )
                for r in result
            ]

    def _get_carrier_agreement_for_booking(self, booking_id: str) -> CarrierAgreementMatch | None:
        """Directly fetch the carrier agreement governing this specific booking."""
        with self.driver.session() as s:
            result = s.run("""
                MATCH (bkg:Booking {id: $booking_id})-[:GOVERNED_BY]->(ca:CarrierAgreement)
                RETURN ca.id AS id, ca.airline_name AS airline_name,
                       ca.airline_code AS airline_code, ca.text AS text
            """, booking_id=booking_id)
            row = result.single()
            if row:
                return CarrierAgreementMatch(
                    id=row["id"], airline_name=row["airline_name"],
                    airline_code=row["airline_code"], text=row["text"], score=1.0
                )
            return None

    def _get_active_weather_for_booking(self, booking_id: str) -> list[WeatherMemoMatch]:
        """Traverse Booking → Route → Region → active WeatherMemo."""
        with self.driver.session() as s:
            result = s.run("""
                MATCH (bkg:Booking {id: $booking_id})-[:ON_ROUTE]->(rt:Route)
                MATCH (r:Region)-[:COVERS]->(rt)
                MATCH (wm:WeatherMemo)-[:ACTIVE_FOR]->(r)
                WHERE wm.active = true
                RETURN wm.id AS id, wm.memo_number AS memo_number,
                       wm.title AS title, wm.text AS text,
                       wm.active AS active, wm.region_code AS region_code
            """, booking_id=booking_id)
            return [
                WeatherMemoMatch(
                    id=r["id"], memo_number=r["memo_number"], title=r["title"],
                    text=r["text"], active=r["active"], region_code=r["region_code"]
                )
                for r in result
            ]

    def _get_loyalty_policy_for_tier(self, tier_name: str) -> list[PolicyMatch]:
        """Pull loyalty policy sections relevant to this customer's tier."""
        with self.driver.session() as s:
            result = s.run("""
                MATCH (p:Policy {id: 'pol-loyalty'})-[:HAS_SECTION]->(ps:PolicySection)
                RETURN ps.id AS id, ps.title AS title,
                       ps.text AS text, p.name AS policy_name
            """)
            return [
                PolicyMatch(
                    id=r["id"], title=r["title"], text=r["text"],
                    policy_name=r["policy_name"], score=0.0, source="graph_expansion"
                )
                for r in result
            ]

    # ── Booking + customer context ────────────────────────────

    def _get_booking_context(self, customer_id: str) -> BookingContext | None:
        """Fetch the customer's most recent disrupted booking with full context."""
        with self.driver.session() as s:
            result = s.run("""
                MATCH (c:Customer {id: $customer_id})-[:HAS_TIER]->(lt:LoyaltyTier)
                MATCH (c)-[:MADE]->(bkg:Booking)
                WHERE bkg.status IN ['canceled', 'disrupted']
                MATCH (bkg)-[:OPERATED_BY]->(pa:PartnerAirline)
                MATCH (bkg)-[:ON_ROUTE]->(rt:Route)
                OPTIONAL MATCH (bkg)-[:DISRUPTED_BY]->(e:Event)
                RETURN c.name AS customer_name,
                       lt.name AS loyalty_tier,
                       bkg.id AS booking_id, bkg.ref AS booking_ref,
                       bkg.payment_type AS payment_type,
                       bkg.points_amount AS points_amount,
                       bkg.cash_amount AS cash_amount,
                       bkg.status AS booking_status,
                       rt.destination_name AS destination,
                       pa.name AS carrier_name, pa.code AS carrier_code,
                       e.name AS disruption_event
                ORDER BY bkg.departure_date DESC
                LIMIT 1
            """, customer_id=customer_id)
            row = result.single()
            if not row:
                return None

            # Fetch tier benefits
            benefits_result = s.run("""
                MATCH (c:Customer {id: $customer_id})-[:HAS_TIER]->(lt:LoyaltyTier)
                MATCH (lt)-[:GRANTS]->(b:Benefit)
                RETURN b.type AS type, b.description AS description,
                       b.fee_waiver AS fee_waiver, b.priority_refund AS priority_refund
            """, customer_id=customer_id)

            return BookingContext(
                booking_id=row["booking_id"],
                booking_ref=row["booking_ref"],
                customer_name=row["customer_name"],
                loyalty_tier=row["loyalty_tier"],
                payment_type=row["payment_type"],
                points_amount=row["points_amount"] or 0,
                cash_amount=row["cash_amount"] or 0,
                destination=row["destination"],
                carrier_name=row["carrier_name"],
                carrier_code=row["carrier_code"],
                booking_status=row["booking_status"],
                disruption_event=row["disruption_event"],
                benefits=[dict(b) for b in benefits_result]
            )

    # ── Build reasoning path for graph visualization ──────────

    def _build_reasoning_path(
        self,
        booking: BookingContext | None,
        policy_matches: list[PolicyMatch],
        carrier_agreements: list[CarrierAgreementMatch],
        weather_memos: list[WeatherMemoMatch],
    ) -> list[dict]:
        """
        Returns a list of edges describing the reasoning path —
        used by the frontend to render the live context graph.
        """
        path = []

        if booking:
            path.append({"from": f"Booking {booking.booking_ref}", "to": booking.carrier_name, "rel": "OPERATED_BY"})
            if booking.disruption_event:
                path.append({"from": f"Booking {booking.booking_ref}", "to": booking.disruption_event, "rel": "DISRUPTED_BY"})
            path.append({"from": booking.customer_name, "to": f"{booking.loyalty_tier} Tier", "rel": "HAS_TIER"})

        for ca in carrier_agreements:
            path.append({"from": ca.airline_name, "to": f"Agreement §{ca.id.split('-')[-1].upper()}", "rel": "GOVERNED_BY"})

        for pm in policy_matches:
            if pm.score > 0 or pm.source == "graph_expansion":
                path.append({"from": pm.policy_name, "to": pm.title, "rel": "HAS_SECTION"})

        for wm in weather_memos:
            if wm.active:
                path.append({"from": f"Memo {wm.memo_number}", "to": wm.region_code, "rel": "ACTIVE_FOR"})

        if booking:
            fee_waiver = any(b.get("fee_waiver") for b in booking.benefits)
            if fee_waiver:
                path.append({"from": f"{booking.loyalty_tier} Tier", "to": "Fee Waiver", "rel": "GRANTS"})

        return path

    # ── Main retrieve ─────────────────────────────────────────

    def retrieve(self, query: str, customer_id: str | None = None) -> RetrievalResult:
        result = RetrievalResult(query=query)

        # Phase 1: embed query and run vector searches in parallel conceptually
        embedding = embed(query)
        policy_matches    = self._vector_search_policies(embedding, top_k=4)
        carrier_matches   = self._vector_search_carrier_agreements(embedding, top_k=2)
        weather_matches   = self._vector_search_weather_memos(embedding, top_k=2)

        # Phase 2: graph expansion from vector hits
        matched_section_ids = [pm.id for pm in policy_matches]
        cross_doc = self._expand_cross_doc_links(matched_section_ids)

        # Deduplicate — don't add cross-doc sections already found by vector search
        existing_ids = {pm.id for pm in policy_matches}
        for sec in cross_doc:
            if sec.id not in existing_ids:
                policy_matches.append(sec)
                existing_ids.add(sec.id)

        result.policy_matches = policy_matches
        result.carrier_agreements = carrier_matches
        result.weather_memos = weather_matches

        # Customer-specific graph expansion
        if customer_id:
            booking = self._get_booking_context(customer_id)
            result.booking = booking

            if booking:
                # Override carrier agreements with the exact one governing this booking
                direct_ca = self._get_carrier_agreement_for_booking(booking.booking_id)
                if direct_ca:
                    # Put the direct match first
                    ca_ids = {ca.id for ca in result.carrier_agreements}
                    if direct_ca.id not in ca_ids:
                        result.carrier_agreements.insert(0, direct_ca)
                    else:
                        # Promote it to first position
                        result.carrier_agreements = [direct_ca] + [
                            ca for ca in result.carrier_agreements if ca.id != direct_ca.id
                        ]

                # Active weather memos for this specific route
                route_weather = self._get_active_weather_for_booking(booking.booking_id)
                existing_wm_ids = {wm.id for wm in result.weather_memos}
                for wm in route_weather:
                    if wm.id not in existing_wm_ids:
                        result.weather_memos.insert(0, wm)

                # Always include loyalty policy when customer has tier benefits
                loyalty_sections = self._get_loyalty_policy_for_tier(booking.loyalty_tier)
                for sec in loyalty_sections:
                    if sec.id not in existing_ids:
                        result.policy_matches.append(sec)
                        existing_ids.add(sec.id)

        # Build reasoning path for visualization
        result.reasoning_path = self._build_reasoning_path(
            result.booking, result.policy_matches,
            result.carrier_agreements, result.weather_memos
        )

        return result

    # ── Format context for Claude ─────────────────────────────

    def format_context_for_llm(self, result: RetrievalResult) -> str:
        lines = ["=== RETRIEVED KNOWLEDGE CONTEXT ===\n"]

        # Customer & booking context
        if result.booking:
            bk = result.booking
            fee_waiver = any(b.get("fee_waiver") for b in bk.benefits)
            priority   = any(b.get("priority_refund") for b in bk.benefits)
            lines.append("── CUSTOMER & BOOKING ──")
            lines.append(f"Customer: {bk.customer_name}")
            lines.append(f"Loyalty Tier: {bk.loyalty_tier} (Fee Waiver: {fee_waiver}, Priority Refund: {priority})")
            lines.append(f"Booking Ref: {bk.booking_ref} | Status: {bk.booking_status}")
            lines.append(f"Route to: {bk.destination} | Carrier: {bk.carrier_name} ({bk.carrier_code}) [PARTNER]")
            lines.append(f"Payment: {bk.payment_type.upper()} — {int(bk.points_amount):,} points + ${bk.cash_amount:.2f} cash")
            if bk.disruption_event:
                lines.append(f"Disruption: {bk.disruption_event}")
            if bk.benefits:
                lines.append("Tier Benefits:")
                for b in bk.benefits:
                    lines.append(f"  • {b['description']}")
            lines.append("")

        # Active weather memos (highest priority — override standard policy)
        active_memos = [wm for wm in result.weather_memos if wm.active]
        if active_memos:
            lines.append("── ACTIVE WEATHER MEMOS (override standard policy) ──")
            for wm in active_memos:
                lines.append(f"[Memo {wm.memo_number}] {wm.title}")
                lines.append(wm.text)
                lines.append("")

        # Carrier agreements
        if result.carrier_agreements:
            lines.append("── CARRIER AGREEMENTS ──")
            for ca in result.carrier_agreements:
                lines.append(f"[{ca.airline_name} Agreement]")
                lines.append(ca.text)
                lines.append("")

        # Policy sections (sorted: vector hits first, then graph expansions)
        if result.policy_matches:
            lines.append("── POLICY SECTIONS ──")
            vector_hits = [p for p in result.policy_matches if p.source == "vector"]
            graph_hits  = [p for p in result.policy_matches if p.source == "graph_expansion"]
            for pm in vector_hits + graph_hits:
                tag = f"[score: {pm.score:.3f}]" if pm.score > 0 else "[graph link]"
                lines.append(f"[{pm.policy_name} — {pm.title}] {tag}")
                lines.append(pm.text)
                lines.append("")

        lines.append("=== END CONTEXT ===")
        return "\n".join(lines)


# ── Quick test ────────────────────────────────────────────────

if __name__ == "__main__":
    retriever = GraphRAGRetriever()

    print("Testing GraphRAG retrieval for demo scenario...\n")
    result = retriever.retrieve(
        query="I need a refund for my canceled flight to Maui. "
              "It was canceled due to the storm. I paid with Points and Cash "
              "on a partner airline and I'm a Gold member.",
        customer_id="cust-sarah"
    )

    print(f"Query: {result.query}\n")
    print(f"Policy sections retrieved : {len(result.policy_matches)}")
    print(f"Carrier agreements        : {len(result.carrier_agreements)}")
    print(f"Weather memos             : {len(result.weather_memos)}")
    print(f"Reasoning path edges      : {len(result.reasoning_path)}")
    print()

    print("── Policy Sections ──")
    for pm in result.policy_matches:
        tag = f"score={pm.score:.3f}" if pm.score > 0 else "graph-expansion"
        print(f"  [{tag}] {pm.title}")

    print("\n── Carrier Agreements ──")
    for ca in result.carrier_agreements:
        print(f"  {ca.airline_name} (score={ca.score:.3f})")

    print("\n── Weather Memos ──")
    for wm in result.weather_memos:
        print(f"  Memo {wm.memo_number} — active={wm.active}")

    print("\n── Reasoning Path (for graph viz) ──")
    for edge in result.reasoning_path:
        print(f"  {edge['from']} --[{edge['rel']}]--> {edge['to']}")

    print("\n── Formatted Context for Claude ──")
    print(retriever.format_context_for_llm(result))

    retriever.close()
