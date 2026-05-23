"use client";

import { useState, useEffect } from "react";
import {
  Box, Heading, Text, VStack, HStack, Badge, Flex, Button,
} from "@chakra-ui/react";
import { GitBranch, Brain, Wrench, Eye, ChevronDown, ChevronRight } from "lucide-react";
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

export function DecisionTracePanel({ sessionId }: { sessionId?: string | null }) {
  const [traces, setTraces] = useState<DecisionTrace[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setExpandedIds(new Set());
    setTraces([]);
    if (!sessionId) return; // no session yet — don't fetch all historical traces
    loadTraces();
    const interval = setInterval(loadTraces, 5000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

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
    } catch {
      // Backend may not be running yet
    }
  }

  function toggleExpand(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <Flex direction="column" h="100%">
      <Box px={4} py={3} borderBottom="1px solid" borderColor="gray.200">
        <Heading size="sm">
          <HStack>
            <GitBranch size={16} />
            <span>Decision Traces</span>
          </HStack>
        </Heading>
        <Text fontSize="xs" color="gray.500">
          Reasoning provenance & causal chains
        </Text>
      </Box>

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
                overflow="hidden"
                _hover={{ borderColor: "blue.200" }}
                transition="border-color 0.15s"
              >
                {/* Header — click to toggle */}
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
                      <Text fontSize="sm" fontWeight="medium" lineClamp={2}>
                        {trace.task}
                      </Text>
                      <HStack mt={1} gap={1}>
                        <Badge size="sm" variant="outline">
                          <Brain size={10} />
                          {trace.steps.length} steps
                        </Badge>
                        {trace.outcome && (
                          <Badge size="sm" colorPalette="green">
                            Resolved
                          </Badge>
                        )}
                      </HStack>
                    </Box>
                  </HStack>
                </Button>

                {/* Expanded detail — inline, scrollable */}
                {isOpen && (
                  <Box
                    px={3}
                    pb={3}
                    pt={1}
                    borderTop="1px solid"
                    borderColor="gray.100"
                    bg="gray.50"
                    maxH="260px"
                    overflowY="auto"
                  >
                    <VStack gap={3} align="stretch">
                      {trace.steps.map((step, i) => (
                        <Box
                          key={`step-${i}-${(step.action || "").slice(0, 32)}`}
                          pl={3}
                          borderLeft="2px solid"
                          borderColor="blue.200"
                        >
                          <HStack align="flex-start" gap={1}>
                            <Brain size={11} style={{ flexShrink: 0, marginTop: 2 }} color="#718096" />
                            <Text fontSize="xs" color="gray.600" lineHeight="tall">
                              {step.thought}
                            </Text>
                          </HStack>
                          <HStack mt={1} gap={1}>
                            <Wrench size={11} style={{ flexShrink: 0 }} color="#718096" />
                            <Text fontSize="xs" fontFamily="mono" color="gray.700">
                              {step.action}
                            </Text>
                          </HStack>
                          {step.observation && (
                            <HStack mt={1} gap={1} align="flex-start">
                              <Eye size={11} style={{ flexShrink: 0, marginTop: 2 }} color="#276749" />
                              <Text fontSize="xs" color="green.700" lineHeight="tall">
                                {step.observation}
                              </Text>
                            </HStack>
                          )}
                        </Box>
                      ))}
                    </VStack>

                    {trace.outcome && (
                      <Box mt={3} p={2} bg="green.50" borderRadius="md">
                        <Text fontSize="xs" fontWeight="bold" color="green.800">
                          Outcome:
                        </Text>
                        <Text fontSize="xs" color="green.900" mt={0.5}>
                          {trace.outcome}
                        </Text>
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            );
          })
        )}
      </VStack>
    </Flex>
  );
}
