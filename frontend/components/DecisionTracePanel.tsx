"use client";

import { useState, useEffect } from "react";
import {
  Box, Heading, Text, VStack, HStack, Badge, Flex, Button,
} from "@chakra-ui/react";
import { GitBranch, Brain, Wrench, Eye, ChevronDown, ChevronRight, History, ShieldCheck, RotateCcw } from "lucide-react";
import { API_BASE } from "@/lib/config";

interface TraceStep {
  step_number: number;
  thought: string;
  action: string;
  observation?: string;
}

interface DecisionTrace {
  id: string;
  task: string;
  steps: TraceStep[];
  outcome: string;
}

interface PolicyRef {
  id: string;
  title: string;
}

interface PastDecision {
  id: string;
  decision_type: string;
  outcome: string;
  reasoning: string;
  confidence_score: number | null;
  risk_factors: string[] | null;
  policy_citations: string[] | null;
  made_at: string;
  session_id: string;
  customer_name: string | null;
  loyalty_tier: string | null;
  cited_sections: PolicyRef[];
}

const DECISION_COLORS: Record<string, string> = {
  refund_authorized: "green",
  fee_waived:        "teal",
  denied:            "red",
  escalate:          "orange",
  rebook:            "blue",
  policy_lookup:     "purple",
  analytics_query:   "gray",
};

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 85 ? "green" : pct >= 65 ? "yellow" : "red";
  return (
    <HStack gap={1.5} align="center">
      <Box w="48px" h="4px" bg="gray.200" borderRadius="full" overflow="hidden">
        <Box w={`${pct}%`} h="100%" bg={`${color}.400`} borderRadius="full" />
      </Box>
      <Text fontSize="10px" color="gray.500">{pct}%</Text>
    </HStack>
  );
}

export function DecisionTracePanel({ sessionId, lastQuestionTime }: { sessionId?: string | null; lastQuestionTime?: Date | null }) {
  const [view, setView] = useState<"session" | "all">("session");
  const [traces, setTraces] = useState<DecisionTrace[]>([]);
  const [decisions, setDecisions] = useState<PastDecision[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [lastExpanded, setLastExpanded] = useState<string | null>(null);
  const [sessionDecisions, setSessionDecisions] = useState<PastDecision[]>([]);

  useEffect(() => {
    setExpandedIds(new Set());
    setTraces([]);
    setSessionDecisions([]);
    if (!sessionId) return;
    loadTraces();
    loadSessionDecisions();
    const interval = setInterval(() => { loadTraces(); loadSessionDecisions(); }, 5000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (view === "all") {
      loadDecisions();
      const interval = setInterval(loadDecisions, 10000);
      return () => clearInterval(interval);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    if (view === "all" && sessionId) loadDecisions();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // Clear stale session decisions whenever a new question is sent
  useEffect(() => {
    if (lastQuestionTime) setSessionDecisions([]);
  }, [lastQuestionTime]);

  async function loadTraces() {
    try {
      const url = sessionId
        ? `${API_BASE}/traces?session_id=${encodeURIComponent(sessionId)}`
        : `${API_BASE}/traces`;
      const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
      const data = await res.json();
      if (data.traces) {
        setTraces(
          data.traces.map((t: Record<string, unknown>) => ({
            id: (t.id as string) || "",
            task: (t.task as string) || "",
            steps: ((t.steps as TraceStep[]) || []).filter((s) => s && s.thought),
            outcome: (t.outcome as string) || "",
          }))
        );
      }
    } catch { /* backend may not be running */ }
  }

  async function loadSessionDecisions() {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API_BASE}/decisions?session_id=${encodeURIComponent(sessionId)}&limit=10`, { signal: AbortSignal.timeout(10000) });
      const data = await res.json();
      if (data.decisions) setSessionDecisions(data.decisions as PastDecision[]);
    } catch { /* backend may not be running */ }
  }

  async function loadDecisions() {
    try {
      const res = await fetch(`${API_BASE}/decisions?limit=50`, { signal: AbortSignal.timeout(10000) });
      const data = await res.json();
      if (data.decisions) setDecisions(data.decisions as PastDecision[]);
    } catch { /* backend may not be running */ }
  }

  function toggleExpand(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        setLastExpanded(null);
      } else {
        next.add(id);
        setLastExpanded(id);
      }
      return next;
    });
  }

  useEffect(() => {
    if (!lastExpanded) return;
    const el = document.getElementById(`expanded-${lastExpanded}`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [lastExpanded]);

  const visibleSessionDecisions = sessionDecisions;

  return (
    <Flex direction="column" h="100%">
      {/* Toggle */}
      <HStack px={4} py={2} borderBottom="1px solid" borderColor="gray.200" gap={1} flexShrink={0}>
        <Button
          size="xs"
          variant={view === "session" ? "solid" : "ghost"}
          colorPalette={view === "session" ? "blue" : "gray"}
          onClick={() => setView("session")}
        >
          <GitBranch size={12} />
          Session
        </Button>
        <Button
          size="xs"
          variant={view === "all" ? "solid" : "ghost"}
          colorPalette={view === "all" ? "blue" : "gray"}
          onClick={() => setView("all")}
        >
          <History size={12} />
          All Decisions
        </Button>
        {view === "all" && (
          <Button size="xs" variant="ghost" colorPalette="gray" onClick={loadDecisions} ml="auto">
            <RotateCcw size={11} />
          </Button>
        )}
      </HStack>

      {/* Session traces view */}
      {view === "session" && (
        <VStack flex={1} overflow="auto" px={4} py={2} gap={2} align="stretch">
          {traces.length === 0 ? (
            <Box py={8} px={4}>
              <Flex justify="center" mb={3}>
                <GitBranch size={32} color="#A0AEC0" />
              </Flex>
              <Text fontSize="sm" color="gray.500" textAlign="center">
                {sessionId ? "No traces for this session yet" : "No active session"}
              </Text>
              <Text fontSize="xs" color="gray.400" textAlign="center" mt={2} lineHeight="tall">
                {sessionId
                  ? "The agent will record decision traces as it processes your question."
                  : "Ask a question in the chat to start a session — decision traces will appear here."}
              </Text>
            </Box>
          ) : (
            traces.map((trace) => {
              const isOpen = expandedIds.has(trace.id);
              return (
                <Box
                  key={trace.id}
                  borderRadius="md"
                  border="1px solid"
                  borderColor={isOpen ? "blue.300" : "gray.200"}
                  _hover={{ borderColor: "blue.200" }}
                  transition="border-color 0.15s"
                >
                  <Button
                    variant="ghost"
                    w="full"
                    h="auto"
                    px={3}
                    py={2.5}
                    justifyContent="flex-start"
                    onClick={() => toggleExpand(trace.id)}
                    borderRadius="none"
                    _hover={{ bg: "gray.50" }}
                  >
                    <HStack w="full" gap={2} align="flex-start">
                      <Box pt={0.5} flexShrink={0} color="gray.400">
                        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </Box>
                      <Box flex={1} textAlign="left">
                        <Text fontSize="sm" fontWeight="medium" lineClamp={2}>{trace.task}</Text>
                        <HStack mt={1} gap={1}>
                          <Badge size="sm" variant="outline">
                            <Brain size={10} />
                            {trace.steps.length} steps
                          </Badge>
                          {trace.outcome && <Badge size="sm" colorPalette="green">Resolved</Badge>}
                        </HStack>
                      </Box>
                    </HStack>
                  </Button>
                  {isOpen && (
                    <Box id={`expanded-${trace.id}`} px={3} pb={3} pt={1} borderTop="1px solid" borderColor="gray.100" bg="gray.50" maxH="260px" overflowY="auto">
                      <VStack gap={3} align="stretch">
                        {trace.steps.map((step, i) => (
                          <Box key={`step-${i}`} pl={3} borderLeft="2px solid" borderColor="blue.200">
                            <HStack align="flex-start" gap={1}>
                              <Brain size={11} style={{ flexShrink: 0, marginTop: 2 }} color="#718096" />
                              <Text fontSize="xs" color="gray.600" lineHeight="tall">{step.thought}</Text>
                            </HStack>
                            <HStack mt={1} gap={1}>
                              <Wrench size={11} style={{ flexShrink: 0 }} color="#718096" />
                              <Text fontSize="xs" fontFamily="mono" color="gray.700">{step.action}</Text>
                            </HStack>
                            {step.observation && (
                              <HStack mt={1} gap={1} align="flex-start">
                                <Eye size={11} style={{ flexShrink: 0, marginTop: 2 }} color="#276749" />
                                <Text fontSize="xs" color="green.700" lineHeight="tall">{step.observation}</Text>
                              </HStack>
                            )}
                          </Box>
                        ))}
                      </VStack>
                      {trace.outcome && (
                        <Box mt={3} p={2} bg="green.50" borderRadius="md">
                          <Text fontSize="xs" fontWeight="bold" color="green.800">Outcome:</Text>
                          <Text fontSize="xs" color="green.900" mt={0.5}>{trace.outcome}</Text>
                        </Box>
                      )}
                    </Box>
                  )}
                </Box>
              );
            })
          )}
          {/* Decision recorded for this session — filtered to current page load */}
          {visibleSessionDecisions.length > 0 && (
            <Box mt={2}>
              <HStack gap={1.5} mb={2} px={1}>
                <ShieldCheck size={13} color="#4A5568" />
                <Text fontSize="xs" fontWeight="semibold" color="gray.600">Decision Recorded</Text>
              </HStack>
              {visibleSessionDecisions.map((d) => {
                const palette = DECISION_COLORS[d.decision_type] || "gray";
                const confidence = d.confidence_score ?? null;
                return (
                  <Box key={d.id} borderRadius="md" border="1px solid" borderColor="green.200" bg="green.50" px={3} py={2.5}>
                    <HStack gap={1.5} mb={1} flexWrap="wrap">
                      <Badge size="sm" colorPalette={palette}>{d.decision_type.replace(/_/g, " ")}</Badge>
                      {d.customer_name && <Text fontSize="xs" color="gray.700" fontWeight="medium">{d.customer_name}</Text>}
                      {d.loyalty_tier && <Badge size="sm" variant="outline" colorPalette="purple">{d.loyalty_tier}</Badge>}
                      {confidence !== null && <ConfidenceBar score={confidence} />}
                    </HStack>
                    <Text fontSize="xs" color="gray.800" lineHeight="tall" mt={1}>{d.outcome}</Text>
                    {d.risk_factors && d.risk_factors.length > 0 && (
                      <HStack gap={1} mt={1.5} flexWrap="wrap">
                        {d.risk_factors.map((r) => (
                          <Badge key={r} size="xs" colorPalette="orange" variant="subtle">{r.replace(/_/g, " ")}</Badge>
                        ))}
                      </HStack>
                    )}
                    {d.cited_sections && d.cited_sections.length > 0 && (
                      <HStack gap={1} mt={1} flexWrap="wrap">
                        <ShieldCheck size={10} color="#718096" />
                        {d.cited_sections.map((ps) => (
                          <Text key={ps.id} fontSize="10px" color="blue.600">§ {ps.title || ps.id}</Text>
                        ))}
                      </HStack>
                    )}
                  </Box>
                );
              })}
            </Box>
          )}
        </VStack>
      )}

      {/* All decisions view */}
      {view === "all" && (
        <VStack flex={1} overflow="auto" px={4} py={2} gap={2} align="stretch">
          {decisions.length === 0 ? (
            <Box py={8} px={4}>
              <Flex justify="center" mb={3}>
                <History size={32} color="#A0AEC0" />
              </Flex>
              <Text fontSize="sm" color="gray.500" textAlign="center">No decisions recorded yet</Text>
              <Text fontSize="xs" color="gray.400" textAlign="center" mt={2} lineHeight="tall">
                Ask the agent a question — every decision is recorded here with policy citations.
              </Text>
            </Box>
          ) : (
            decisions.map((d) => {
              const isOpen = expandedIds.has(d.id);
              const palette = DECISION_COLORS[d.decision_type] || "gray";
              const confidence = d.confidence_score ?? null;
              return (
                <Box
                  key={d.id}
                  borderRadius="md"
                  border="1px solid"
                  borderColor={isOpen ? "blue.300" : "gray.200"}
                  _hover={{ borderColor: "blue.200" }}
                  transition="border-color 0.15s"
                >
                  <Button
                    variant="ghost"
                    w="full"
                    h="auto"
                    px={3}
                    py={2.5}
                    justifyContent="flex-start"
                    onClick={() => toggleExpand(d.id)}
                    borderRadius="none"
                    _hover={{ bg: "gray.50" }}
                  >
                    <HStack w="full" gap={2} align="flex-start">
                      <Box pt={0.5} flexShrink={0} color="gray.400">
                        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      </Box>
                      <Box flex={1} textAlign="left">
                        <HStack gap={1.5} mb={1} flexWrap="wrap">
                          <Badge size="sm" colorPalette={palette}>{d.decision_type.replace(/_/g, " ")}</Badge>
                          {d.customer_name && (
                            <Text fontSize="xs" color="gray.600" fontWeight="medium">{d.customer_name}</Text>
                          )}
                          {d.loyalty_tier && (
                            <Badge size="sm" variant="outline" colorPalette="purple">{d.loyalty_tier}</Badge>
                          )}
                        </HStack>
                        <Text fontSize="xs" color="gray.600" lineClamp={1}>{d.outcome}</Text>
                        <HStack mt={1.5} gap={2}>
                          {confidence !== null && <ConfidenceBar score={confidence} />}
                          <Text fontSize="10px" color="gray.400">
                            {typeof d.made_at === "string" ? new Date(d.made_at).toLocaleDateString() : "—"}
                          </Text>
                        </HStack>
                      </Box>
                    </HStack>
                  </Button>
                  {isOpen && (
                    <Box id={`expanded-${d.id}`} px={3} pb={3} pt={1} borderTop="1px solid" borderColor="gray.100" bg="gray.50" maxH="320px" overflowY="auto">
                      {/* Outcome */}
                      <Box mb={2}>
                        <Text fontSize="xs" fontWeight="semibold" color="gray.600" mb={0.5}>Outcome</Text>
                        <Text fontSize="xs" color="gray.800" lineHeight="tall">{d.outcome || "—"}</Text>
                      </Box>
                      {/* Reasoning */}
                      <Box mb={2}>
                        <HStack gap={1} mb={1}>
                          <Brain size={11} color="#718096" />
                          <Text fontSize="xs" fontWeight="semibold" color="gray.600">Reasoning</Text>
                        </HStack>
                        <Text fontSize="xs" color="gray.700" lineHeight="tall">{d.reasoning || "No reasoning recorded."}</Text>
                      </Box>

                      {/* Risk factors */}
                      {d.risk_factors && d.risk_factors.length > 0 && (
                        <Box mb={2}>
                          <Text fontSize="xs" fontWeight="semibold" color="gray.600" mb={1}>Risk Factors</Text>
                          <HStack gap={1} flexWrap="wrap">
                            {d.risk_factors.map((r) => (
                              <Badge key={r} size="xs" colorPalette="orange" variant="subtle">
                                {r.replace(/_/g, " ")}
                              </Badge>
                            ))}
                          </HStack>
                        </Box>
                      )}

                      {/* Policy citations */}
                      {d.cited_sections && d.cited_sections.length > 0 && (
                        <Box>
                          <HStack gap={1} mb={1}>
                            <ShieldCheck size={11} color="#718096" />
                            <Text fontSize="xs" fontWeight="semibold" color="gray.600">Policy Citations</Text>
                          </HStack>
                          <VStack align="stretch" gap={1}>
                            {d.cited_sections.map((ps) => (
                              <Text key={ps.id} fontSize="xs" color="blue.600">
                                § {ps.title || ps.id}
                              </Text>
                            ))}
                          </VStack>
                        </Box>
                      )}

                      <Text fontSize="10px" color="gray.400" mt={2}>ID: {d.id}</Text>
                    </Box>
                  )}
                </Box>
              );
            })
          )}
        </VStack>
      )}
    </Flex>
  );
}
