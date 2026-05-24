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
            <Drawer.Header borderBottomWidth="1px" borderColor="gray.200">
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
                  </VStack>
                </Box>

                <Separator />

                {/* Graph Data Model */}
                <Box>
                  <Heading size="sm" mb={3} color="gray.800">Graph Data Model</Heading>
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
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      justifyContent="flex-start"
                    >
                      <a
                        href="https://neo4j.com/cloud/aura/"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Neo4j AuraDB — Free tier available
                      </a>
                    </Button>
                    <Button
                      asChild
                      variant="outline"
                      size="sm"
                      justifyContent="flex-start"
                    >
                      <a
                        href="https://github.com/pnborkar/context-graph-travel"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        GitHub — View source code
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
