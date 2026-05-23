"use client";

import { Box, Text, VStack, HStack, Badge, Flex, Heading } from "@chakra-ui/react";
import { Search } from "lucide-react";
import { NODE_COLORS } from "@/lib/config";

export interface DirectResult {
  id: string;
  title: string;
  type: string;
  score?: number;
}

export interface GraphAddition {
  id: string;
  title: string;
  type: string;
  via: string;
}

export interface RagComparisonData {
  query_summary: string;
  direct_results: DirectResult[];
  graph_additions: GraphAddition[];
}

function NodeTypeBadge({ type }: { type: string }) {
  const color = NODE_COLORS[type];
  return (
    <Badge
      size="xs"
      style={color ? { backgroundColor: color, color: "white" } : {}}
      colorPalette={color ? undefined : "gray"}
    >
      {type}
    </Badge>
  );
}

function SingleComparison({ data, index }: { data: RagComparisonData; index: number }) {
  const { query_summary, direct_results, graph_additions } = data;
  return (
    <Box
      borderWidth="1px"
      borderColor="gray.200"
      borderRadius="md"
      overflow="hidden"
    >
      {/* Tool call header */}
      <Box px={3} py={2} bg="gray.100" borderBottom="1px solid" borderColor="gray.200">
        <HStack gap={1}>
          <Badge size="xs" colorPalette="purple" variant="subtle">#{index + 1}</Badge>
          <Text fontSize="xs" color="gray.600" fontStyle="italic" flex={1} truncate>
            {query_summary}
          </Text>
        </HStack>
      </Box>

      <VStack align="stretch" gap={0} p={3}>
        {/* Naive RAG */}
        <Box mb={3}>
          <HStack mb={1} gap={2}>
            <Box w={2} h={2} borderRadius="full" bg="blue.500" flexShrink={0} />
            <Text fontSize="xs" fontWeight="semibold" color="gray.700">
              Naive RAG ({direct_results.length})
            </Text>
          </HStack>
          {direct_results.length === 0 ? (
            <Text fontSize="xs" color="gray.400">No direct matches</Text>
          ) : (
            <VStack align="stretch" gap={1}>
              {direct_results.map((r, i) => (
                <Box
                  key={`direct-${r.id}-${i}`}
                  px={2}
                  py={1}
                  bg="blue.50"
                  borderRadius="sm"
                  borderLeft="2px solid"
                  borderColor="blue.400"
                >
                  <Flex justify="space-between" align="center" gap={2}>
                    <Text fontSize="xs" color="gray.800" flex={1} truncate>
                      {r.title}
                    </Text>
                    {r.score !== undefined && (
                      <Badge size="xs" colorPalette="blue" flexShrink={0}>
                        {(r.score * 100).toFixed(0)}%
                      </Badge>
                    )}
                  </Flex>
                  <NodeTypeBadge type={r.type} />
                </Box>
              ))}
            </VStack>
          )}
        </Box>

        {/* GraphRAG additions */}
        <Box mb={2}>
          <HStack mb={1} gap={2}>
            <Box w={2} h={2} borderRadius="full" bg="green.500" flexShrink={0} />
            <Text fontSize="xs" fontWeight="semibold" color="gray.700">
              Graph adds ({graph_additions.length})
            </Text>
          </HStack>
          {graph_additions.length === 0 ? (
            <Text fontSize="xs" color="gray.400">No graph additions</Text>
          ) : (
            <VStack align="stretch" gap={1}>
              {graph_additions.map((a, i) => (
                <Box
                  key={`graph-${a.id}-${i}`}
                  px={2}
                  py={1}
                  bg="green.50"
                  borderRadius="sm"
                  borderLeft="2px solid"
                  borderColor="green.400"
                >
                  <Text fontSize="xs" color="gray.800" truncate>{a.title}</Text>
                  <Flex gap={1} align="center">
                    <NodeTypeBadge type={a.type} />
                    <Text fontSize="xs" color="gray.400">via {a.via}</Text>
                  </Flex>
                </Box>
              ))}
            </VStack>
          )}
        </Box>

        {/* Mini summary */}
        <Box px={2} py={1} bg="gray.50" borderRadius="sm" borderWidth="1px" borderColor="gray.200">
          <Text fontSize="xs" color="gray.600">
            Vector found{" "}
            <Text as="span" fontWeight="semibold" color="blue.600">{direct_results.length}</Text>
            {" · "}Graph added{" "}
            <Text as="span" fontWeight="semibold" color="green.600">{graph_additions.length}</Text>
          </Text>
        </Box>
      </VStack>
    </Box>
  );
}

interface RagComparisonPanelProps {
  data: RagComparisonData[];
}

export function RagComparisonPanel({ data }: RagComparisonPanelProps) {
  if (!data || data.length === 0) {
    return (
      <Flex direction="column" align="center" justify="center" gap={3} px={4} py={8}>
        <Search size={32} color="#CBD5E0" />
        <Text fontSize="sm" color="gray.500" textAlign="center">
          Ask any question to see RAG vs GraphRAG
        </Text>
        <Text fontSize="xs" color="gray.400" textAlign="center" maxW="220px">
          Every tool call shows what direct lookup finds vs what graph traversal adds
        </Text>
      </Flex>
    );
  }

  const totalDirect = data.reduce((s, d) => s + d.direct_results.length, 0);
  const totalGraph = data.reduce((s, d) => s + d.graph_additions.length, 0);

  return (
    <VStack align="stretch" gap={0} p={3}>
      {/* Session summary banner */}
      <Box mb={3} p={3} bg="gray.50" borderRadius="md" borderWidth="1px" borderColor="gray.200">
        <Heading size="xs" color="gray.700" mb={1}>This query — {data.length} tool call{data.length !== 1 ? "s" : ""}</Heading>
        <Text fontSize="xs" color="gray.600">
          Vector search found{" "}
          <Text as="span" fontWeight="semibold" color="blue.600">{totalDirect} node{totalDirect !== 1 ? "s" : ""}</Text>
          {". "}
          Graph traversal added{" "}
          <Text as="span" fontWeight="semibold" color="green.600">{totalGraph} more</Text>
          {totalGraph > 0 ? " — context a naive RAG system would miss entirely." : "."}
        </Text>
      </Box>

      {/* One card per tool call */}
      <VStack align="stretch" gap={2}>
        {data.map((item, i) => (
          <SingleComparison key={i} data={item} index={i} />
        ))}
      </VStack>
    </VStack>
  );
}
