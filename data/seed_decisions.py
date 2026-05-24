"""
Seed sample Decision nodes with embeddings into AuraDB.

Creates realistic past decisions linked to existing Customer, Session, and
PolicySection nodes. Generates OpenAI embeddings so find_precedents() vector
search works immediately.

Usage:
  cd <repo-root>
  python data/seed_decisions.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_driver, EMBEDDING_MODEL, OPENAI_API_KEY
from openai import OpenAI

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def embed(text: str) -> list[float]:
    resp = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


# ---------------------------------------------------------------------------
# Sample decisions — realistic travel customer service scenarios
# Each maps to real customers and policy sections already seeded in AuraDB.
# ---------------------------------------------------------------------------

DECISIONS = [
    {
        "decision_type": "refund_authorized",
        "outcome": "Full refund of $847 authorized for Sarah Chen on booking EXP-991. Alaska Airlines Pacific storm waiver applies. Gold tier priority refund timeline: 3–5 business days.",
        "reasoning": "Customer is Gold tier with priority refund benefit. Booking EXP-991 was disrupted by the Pacific storm (active weather waiver WM-PACIFIC-001). Alaska Airlines carrier agreement section 4.2 mandates full refund for weather-related involuntary cancellations. Gold tier benefit grants priority processing.",
        "confidence_score": 0.97,
        "risk_factors": ["weather_disruption", "mixed_payment_booking"],
        "policy_citations": ["ps-refund-involuntary", "ps-loyalty-gold-benefits", "ps-weather-waiver"],
        "customer_name": "Sarah Chen",
        "days_ago": 3,
    },
    {
        "decision_type": "refund_authorized",
        "outcome": "Partial refund of $612 authorized for James Okafor on booking EXP-887. Points component (18,000 pts) reinstated. Cash component refunded within 5–7 days.",
        "reasoning": "James Okafor is Silver tier. Booking EXP-887 disrupted on ORD→LAX route. No active weather waiver on this route, but disruption was carrier-initiated (mechanical). United Airlines carrier agreement section 3.1 requires refund for carrier-initiated cancellations. Mixed payment booking — points reinstated, cash refunded separately per policy section ps-refund-mixed-payment.",
        "confidence_score": 0.91,
        "risk_factors": ["mixed_payment_booking", "no_weather_waiver", "carrier_initiated_cancellation"],
        "policy_citations": ["ps-refund-involuntary", "ps-refund-mixed-payment"],
        "customer_name": "James Okafor",
        "days_ago": 7,
    },
    {
        "decision_type": "denied",
        "outcome": "Refund denied for Tom Reyes on booking EXP-774. Voluntary cancellation with no qualifying waiver. $150 cancellation fee applies per Blue tier policy.",
        "reasoning": "Tom Reyes is Blue tier with no fee waiver benefit. Cancellation is voluntary — no active weather waiver on ORD→MIA route. Blue tier cancellation policy (ps-cancellation-fees) specifies $150 fee for voluntary cancellations within 14 days of departure. No applicable waiver found across carrier agreements or active weather memos.",
        "confidence_score": 0.95,
        "risk_factors": ["voluntary_cancellation", "no_weather_waiver", "blue_tier_no_benefits"],
        "policy_citations": ["ps-cancellation-fees", "ps-loyalty-blue-benefits"],
        "customer_name": "Tom Reyes",
        "days_ago": 14,
    },
    {
        "decision_type": "fee_waived",
        "outcome": "Cancellation fee waived for Maya Patel on booking EXP-663. Silver tier fee waiver benefit applied. No charge for voluntary cancellation.",
        "reasoning": "Maya Patel is Silver tier. Silver tier benefit includes one annual cancellation fee waiver (ps-loyalty-silver-benefits). This is her first fee waiver request this year. Waiver applied — $100 cancellation fee removed. Cash refund of $423 authorized within 7 business days.",
        "confidence_score": 0.93,
        "risk_factors": ["voluntary_cancellation", "first_waiver_use"],
        "policy_citations": ["ps-loyalty-silver-benefits", "ps-cancellation-fees"],
        "customer_name": "Maya Patel",
        "days_ago": 10,
    },
    {
        "decision_type": "refund_authorized",
        "outcome": "Platinum goodwill credit of $50 applied to account plus full refund of $1,240 for Pacific storm disruption. Expedited 24-hour refund timeline per Platinum tier SLA.",
        "reasoning": "Customer is Platinum tier. Booking disrupted by Pacific storm (active waiver WM-PACIFIC-001). Platinum tier policy grants: (1) automatic $50 goodwill credit for any weather disruption, (2) 24-hour expedited refund SLA, (3) priority rebooking. Full refund authorized under Alaska Airlines carrier agreement weather disruption clause. Goodwill credit applied immediately.",
        "confidence_score": 0.98,
        "risk_factors": ["weather_disruption", "high_value_booking"],
        "policy_citations": ["ps-refund-involuntary", "ps-loyalty-platinum-benefits", "ps-weather-waiver", "ps-goodwill-credits"],
        "customer_name": "Sarah Chen",
        "days_ago": 21,
    },
    {
        "decision_type": "policy_lookup",
        "outcome": "Active weather waiver WM-PACIFIC-001 confirmed for Alaska Airlines flights to Hawaii. Waiver covers involuntary cancellations and delays exceeding 3 hours through the expiry date.",
        "reasoning": "Weather memo WM-PACIFIC-001 is active for the Pacific region. Covers Alaska Airlines routes to Hawaii (HNL, OGG, KOA, LIH). Waiver type: weather — grants full refund eligibility and free rebooking for affected flights. Expiry date confirmed — still within valid window.",
        "confidence_score": 0.99,
        "risk_factors": [],
        "policy_citations": ["ps-weather-waiver"],
        "customer_name": None,
        "days_ago": 5,
    },
    {
        "decision_type": "rebook",
        "outcome": "Complimentary rebook authorized for James Okafor on next available ORD→LAX flight. No fare difference charged per Silver tier disruption policy.",
        "reasoning": "James Okafor's original flight EXP-887 was carrier-cancelled. Silver tier disruption benefit includes one free rebook on an equivalent or lower-fare itinerary. Next available ORD→LAX departure confirmed. No fare difference applies per carrier agreement section 3.2. Customer notified via preferred email channel.",
        "confidence_score": 0.89,
        "risk_factors": ["carrier_initiated_cancellation", "limited_seat_availability"],
        "policy_citations": ["ps-rebooking-rights", "ps-loyalty-silver-benefits"],
        "customer_name": "James Okafor",
        "days_ago": 8,
    },
    {
        "decision_type": "escalate",
        "outcome": "Case escalated to Senior Refund Specialist. Complex multi-leg booking with partially used segments — automated refund calculation not applicable.",
        "reasoning": "Booking involves 3-segment itinerary with one segment already flown. Refund calculation requires manual proration per complex itinerary policy (ps-complex-itinerary). Automated refund tools cannot handle partially-used multi-leg bookings. Escalated to specialist queue with 48-hour SLA. Customer informed of escalation path.",
        "confidence_score": 0.72,
        "risk_factors": ["multi_leg_booking", "partially_used_segments", "complex_proration"],
        "policy_citations": ["ps-complex-itinerary", "ps-escalation-criteria"],
        "customer_name": "Tom Reyes",
        "days_ago": 18,
    },
]


def run():
    driver = get_driver()

    with driver.session() as session:
        print("Creating Decision vector index if not exists...")
        try:
            session.run("""
                CREATE VECTOR INDEX decision_embeddings IF NOT EXISTS
                FOR (n:Decision) ON (n.embedding)
                OPTIONS { indexConfig: {
                    `vector.dimensions`: 1536,
                    `vector.similarity_function`: 'cosine'
                }}
            """)
            print("  Index ready.")
        except Exception as e:
            print(f"  Index warning (may already exist): {e}")

        print(f"\nSeeding {len(DECISIONS)} decisions...\n")

        for i, d in enumerate(DECISIONS):
            decision_id = f"dec-seed-{uuid.uuid4().hex[:8]}"
            session_id  = f"sess-seed-{uuid.uuid4().hex[:8]}"
            made_at     = datetime.now() - timedelta(days=d["days_ago"])

            # Generate embedding
            embed_text = f"{d['decision_type']} {d['outcome']} {d['reasoning'][:500]}"
            print(f"  [{i+1}/{len(DECISIONS)}] Embedding: {d['decision_type']} — {d['customer_name'] or 'no customer'}...")
            embedding = embed(embed_text)

            # Create Session + Decision
            session.run("""
                MERGE (sess:Session {id: $session_id})
                ON CREATE SET sess.active = false, sess.created_at = $made_at
                CREATE (d:Decision {
                    id:               $decision_id,
                    decision_type:    $decision_type,
                    value:            $outcome,
                    reasoning:        $reasoning,
                    policy_citations: $policy_citations,
                    confidence_score: $confidence_score,
                    risk_factors:     $risk_factors,
                    made_at:          $made_at
                })
                CREATE (sess)-[:MADE_DECISION]->(d)
            """, {
                "session_id":       session_id,
                "decision_id":      decision_id,
                "decision_type":    d["decision_type"],
                "outcome":          d["outcome"],
                "reasoning":        d["reasoning"],
                "policy_citations": d["policy_citations"],
                "confidence_score": d["confidence_score"],
                "risk_factors":     d["risk_factors"],
                "made_at":          made_at.isoformat(),
            })

            # Set embedding
            session.run(
                "MATCH (d:Decision {id: $id}) "
                "CALL db.create.setNodeVectorProperty(d, 'embedding', $embedding)",
                {"id": decision_id, "embedding": embedding},
            )

            # Link to Customer if named
            if d["customer_name"]:
                session.run("""
                    MATCH (sess:Session {id: $session_id})
                    MATCH (c:Customer {name: $name})
                    MERGE (sess)-[:FOR_CUSTOMER]->(c)
                """, {"session_id": session_id, "name": d["customer_name"]})

            # Link to PolicySections (best-effort — IDs may not match exactly)
            for ps_id in d["policy_citations"]:
                try:
                    session.run("""
                        MATCH (d:Decision {id: $did})
                        MATCH (ps:PolicySection {id: $psid})
                        MERGE (d)-[:BASED_ON]->(ps)
                    """, {"did": decision_id, "psid": ps_id})
                except Exception:
                    pass

            print(f"     Created {decision_id} (confidence: {d['confidence_score']})")

    driver.close()
    print(f"\nDone. {len(DECISIONS)} decisions seeded with embeddings.")
    print("The 'All Decisions' panel and find_precedents() vector search are now populated.")


if __name__ == "__main__":
    run()
