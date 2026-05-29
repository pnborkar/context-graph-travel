"use client";

import {
  Box,
  Button,
  CloseButton,
  Drawer,
  Heading,
  Portal,
  Text,
  VStack,
  Badge,
  HStack,
  Separator,
  Code,
} from "@chakra-ui/react";
import { DEMO_SCENARIOS } from "@/lib/config";

interface SchemaDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const DATA_MODEL = `(:Customer)-[:HAS_TIER]->(:LoyaltyTier)-[:GRANTS]->(:Benefit)
(:Customer)-[:MADE]->(:Booking)-[:OPERATED_BY]->(:PartnerAirline)
(:Booking)-[:ON_ROUTE]->(:Route)<-[:COVERS]-(:Region)
(:Region)<-[:ACTIVE_FOR]-(:WeatherMemo)
(:Booking)-[:GOVERNED_BY]->(:CarrierAgreement)
(:Booking)-[:DISRUPTED_BY]->(:Event)
(:Policy)-[:HAS_SECTION]->(:PolicySection)
(:PolicySection)-[:REFERENCED_BY]->(:PolicySection)
(:Session)-[:FOR_CUSTOMER]->(:Customer)
(:Session)-[:MADE_DECISION]->(:Decision)
(:Decision)-[:BASED_ON]->(:PolicySection)`;

const SCENARIO_COLORS: Record<string, string> = {
  "Disruption & Refunds": "red",
  "Multi-hop GraphRAG": "purple",
  "Policy Lookup": "blue",
  "Customer Intelligence": "green",
};

export function SchemaDrawer({ open, onOpenChange }: SchemaDrawerProps) {
  return (
    <Drawer.Root
      open={open}
      onOpenChange={(e) => onOpenChange(e.open)}
      placement="end"
      size="lg"
    >
      <Portal>
        <Drawer.Backdrop />
        <Drawer.Positioner>
          <Drawer.Content>
            <Drawer.Header px={6} py={5} borderBottomWidth="1px" borderColor="gray.200">
              <Drawer.Title>About Context Graph</Drawer.Title>
              <Drawer.CloseTrigger asChild>
                <CloseButton size="sm" />
              </Drawer.CloseTrigger>
            </Drawer.Header>

            <Drawer.Body py={8} px={6}>
              <VStack gap={8} align="stretch">

                {/* Overview */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">What This Demos</Heading>
                  <Text color="gray.600" fontSize="sm" lineHeight="tall">
                    A live AI agent that handles travel customer service scenarios using a Neo4j
                    knowledge graph. Every answer is grounded in <strong>graph traversal</strong> — the
                    agent follows relationships across customers, bookings, carrier agreements, loyalty
                    tiers, weather memos, and policy sections to reach decisions a text search would miss.
                  </Text>
                </Box>

                {/* Why Context Graph + GraphRAG */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">Why Graph?</Heading>
                  <VStack align="stretch" gap={2}>
                    <HStack align="flex-start" gap={2}>
                      <Text fontSize="sm" color="blue.500" fontWeight="bold" flexShrink={0}>01</Text>
                      <Text fontSize="sm" color="gray.600">A customer's refund eligibility depends on their loyalty tier, their carrier's agreement, an active weather waiver, and the applicable policy — no single document holds all four. Only a graph connects them.</Text>
                    </HStack>
                    <HStack align="flex-start" gap={2}>
                      <Text fontSize="sm" color="blue.500" fontWeight="bold" flexShrink={0}>02</Text>
                      <Text fontSize="sm" color="gray.600">Vector search finds relevant text. Graph traversal finds the right answer. GraphRAG combines both — semantic similarity to locate policy sections, graph hops to verify they actually apply.</Text>
                    </HStack>
                    <HStack align="flex-start" gap={2}>
                      <Text fontSize="sm" color="blue.500" fontWeight="bold" flexShrink={0}>03</Text>
                      <Text fontSize="sm" color="gray.600">Every decision is traceable. The context graph shows exactly which nodes the agent traversed — not a black box, but an auditable path from question to answer.</Text>
                    </HStack>
                  </VStack>
                </Box>

                <Separator />

                {/* Capabilities */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">Capabilities</Heading>
                  <VStack align="stretch" gap={2}>
                    <Box p={3} bg="blue.50" borderRadius="lg" borderWidth="1px" borderColor="blue.100">
                      <Text fontSize="sm" fontWeight="semibold" color="blue.700" mb={1}>GraphRAG</Text>
                      <Text fontSize="sm" color="gray.600">Hybrid vector + multi-hop graph retrieval across the policy knowledge base</Text>
                    </Box>
                    <Box p={3} bg="purple.50" borderRadius="lg" borderWidth="1px" borderColor="purple.100">
                      <Text fontSize="sm" fontWeight="semibold" color="purple.700" mb={1}>Context Graph</Text>
                      <Text fontSize="sm" color="gray.600">Live graph visualization shows exactly which nodes and relationships the agent used</Text>
                    </Box>
                    <Box p={3} bg="green.50" borderRadius="lg" borderWidth="1px" borderColor="green.100">
                      <Text fontSize="sm" fontWeight="semibold" color="green.700" mb={1}>Agent Memory</Text>
                      <Text fontSize="sm" color="gray.600">Conversation context, extracted entities, and detected preferences persist in Neo4j</Text>
                    </Box>
                    <Box p={3} bg="orange.50" borderRadius="lg" borderWidth="1px" borderColor="orange.100">
                      <Text fontSize="sm" fontWeight="semibold" color="orange.700" mb={1}>Decision Audit Trail</Text>
                      <Text fontSize="sm" color="gray.600">Every agent decision is written to Neo4j as a <Code fontSize="xs">Decision</Code> node with confidence score, risk factors, and policy citations. The Session tab shows the current decision + semantically similar past precedents ranked by vector similarity.</Text>
                    </Box>
                  </VStack>
                </Box>

                <Separator />

                {/* Graph Data Model */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">Graph Data Model</Heading>
                  <Box borderRadius="lg" overflow="hidden" borderWidth="1px" borderColor="gray.200" mb={3}>
                    <img src="/schema.jpg" alt="Graph schema diagram" style={{ width: "100%", display: "block" }} />
                  </Box>
                  <Code
                    display="block"
                    whiteSpace="pre"
                    p={4}
                    borderRadius="lg"
                    fontSize="xs"
                    bg="gray.900"
                    color="green.300"
                    overflowX="auto"
                  >
                    {DATA_MODEL}
                  </Code>
                </Box>

                <Separator />

                {/* Demo Scenarios */}
                <Box>
                  <Heading size="sm" mb={1} color="gray.800">Demo Scenarios</Heading>
                  <Text fontSize="xs" color="gray.500" mb={4}>
                    Copy any prompt into the chat to try it
                  </Text>
                  <VStack gap={4} align="stretch">
                    {DEMO_SCENARIOS.map((scenario) => (
                      <Box key={scenario.name}>
                        <HStack mb={2}>
                          <Badge
                            colorPalette={SCENARIO_COLORS[scenario.name] || "gray"}
                            size="sm"
                          >
                            {scenario.name}
                          </Badge>
                        </HStack>
                        <VStack align="stretch" gap={2} pl={2}>
                          {scenario.prompts.map((prompt) => (
                            <Box
                              key={prompt}
                              p={4}
                              bg="gray.50"
                              borderRadius="lg"
                              borderWidth="1px"
                              borderColor="gray.200"
                              cursor="pointer"
                              _hover={{ bg: "blue.50", borderColor: "blue.200" }}
                              transition="all 0.15s"
                              onClick={() => {
                                navigator.clipboard.writeText(prompt).catch(() => {});
                              }}
                            >
                              <Text fontSize="sm" color="gray.700" lineHeight="tall">
                                {prompt}
                              </Text>
                              <Text fontSize="xs" color="gray.400" mt={2}>
                                Click to copy
                              </Text>
                            </Box>
                          ))}
                        </VStack>
                      </Box>
                    ))}
                  </VStack>
                </Box>

                <Separator />

                {/* Links */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">Resources</Heading>
                  <VStack align="stretch" gap={2}>
                    <Button asChild variant="ghost" size="sm" justifyContent="flex-start">
                      <a href="https://neo4j.com/cloud/aura/" target="_blank" rel="noopener noreferrer">
                        Neo4j AuraDB — Free tier available
                      </a>
                    </Button>
                    <Button asChild variant="ghost" size="sm" justifyContent="flex-start">
                      <a href="https://github.com/neo4j-field/context-graph-travel" target="_blank" rel="noopener noreferrer">
                        GitHub — View source code
                      </a>
                    </Button>
                    <Button asChild variant="ghost" size="sm" justifyContent="flex-start">
                      <a href="https://neo4j.com/blog/agentic-ai/hands-on-with-context-graphs-and-neo4j/" target="_blank" rel="noopener noreferrer">
                        Neo4j — Hands-on with Context Graphs
                      </a>
                    </Button>
                  </VStack>
                </Box>

                <Separator />

                {/* Further Reading */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">Further Reading</Heading>
                  <VStack align="stretch" gap={2}>
                    <Button asChild variant="ghost" size="sm" justifyContent="flex-start">
                      <a href="https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/" target="_blank" rel="noopener noreferrer">
                        The Original Thesis — Foundation Capital
                      </a>
                    </Button>
                    <Button asChild variant="ghost" size="sm" justifyContent="flex-start">
                      <a href="https://www.linkedin.com/pulse/context-graphs-capturing-why-age-ai-dharmesh-shah-oyyze" target="_blank" rel="noopener noreferrer">
                        The Reality Check — Dharmesh Shah, HubSpot CTO
                      </a>
                    </Button>
                    <Button asChild variant="ghost" size="sm" justifyContent="flex-start">
                      <a href="https://subramanya.ai/2026/01/01/what-are-context-graphs-really/" target="_blank" rel="noopener noreferrer">
                        The Two Clocks Problem — Subramanya N
                      </a>
                    </Button>
                  </VStack>
                </Box>

              </VStack>
            </Drawer.Body>
          </Drawer.Content>
        </Drawer.Positioner>
      </Portal>
    </Drawer.Root>
  );
}
