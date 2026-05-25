"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Box,
  Flex,
  Heading,
  Text,
  Container,
  Grid,
  GridItem,
  Button,
  HStack,
  IconButton,
  Spinner,
  Menu,
  Portal,
} from "@chakra-ui/react";
import { Menu as MenuIcon, Network, MessageSquare, Sun, Moon, Plane, GitBranch } from "lucide-react";
import dynamic from "next/dynamic";
import { ChatInterface } from "@/components/ChatInterface";
import { DecisionTracePanel } from "@/components/DecisionTracePanel";
import { SchemaDrawer } from "@/components/SchemaDrawer";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { API_BASE, DOMAIN } from "@/lib/config";
import type { GraphData } from "@/lib/config";

type PanelId = "chat" | "graph" | "details";

function useColorMode() {
  const [colorMode, setColorMode] = useState<"light" | "dark">("light");

  useEffect(() => {
    const stored = localStorage.getItem("ccg-color-mode") as "light" | "dark" | null;
    const initial = stored ?? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setColorMode(initial);
    document.documentElement.dataset.theme = initial;
  }, []);

  const toggleColorMode = () => {
    const next = colorMode === "light" ? "dark" : "light";
    setColorMode(next);
    localStorage.setItem("ccg-color-mode", next);
    document.documentElement.dataset.theme = next;
  };

  return { colorMode, toggleColorMode };
}

const ContextGraphView = dynamic(
  () => import("@/components/ContextGraphView").then((mod) => mod.ContextGraphView),
  {
    ssr: false,
    loading: () => (
      <Flex align="center" justify="center" h="100%" color="gray.400">
        <Spinner size="lg" />
      </Flex>
    ),
  },
);

export default function Home() {
  const { colorMode, toggleColorMode } = useColorMode();
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [activePanel, setActivePanel] = useState<PanelId>("chat");
  const [backendStatus, setBackendStatus] = useState<"ok" | "degraded" | "offline">("offline");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string>("");
  const [currentDecisionId, setCurrentDecisionId] = useState<string | null>(null);
  const [askAboutInput, setAskAboutInput] = useState<string | null>(null);
  const [schemaOpen, setSchemaOpen] = useState(false);

  const handleGraphUpdate = useCallback((data: GraphData) => {
    setGraphData(data);
  }, []);

  const handleSessionChange = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId);
  }, []);

  const handleAskAbout = useCallback((entityName: string) => {
    setAskAboutInput(`Tell me about ${entityName}`);
    setActivePanel("chat");
  }, []);

  useEffect(() => {
    async function checkHealth(retries = 3, delay = 1000) {
      for (let attempt = 0; attempt < retries; attempt++) {
        try {
          const res = await fetch(`${API_BASE.replace("/api", "")}/health`, {
            signal: AbortSignal.timeout(5000),
          });
          const data = await res.json();
          setBackendStatus(data.status === "ok" ? "ok" : "degraded");
          return;
        } catch {
          if (attempt < retries - 1) {
            await new Promise((r) => setTimeout(r, delay * (attempt + 1)));
          }
        }
      }
      setBackendStatus("offline");
    }
    checkHealth();
    const interval = setInterval(() => checkHealth(1), 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box minH="100dvh" bg="bg.canvas">
      <SchemaDrawer open={schemaOpen} onOpenChange={setSchemaOpen} />

      {/* Header */}
      <Box
        as="header"
        bg="gray.800"
        borderBottomWidth="1px"
        borderColor="gray.700"
        py={{ base: 2, md: 3 }}
        px={{ base: 3, md: 6 }}
      >
        <Container maxW="container.2xl">
          <Flex justify="space-between" align="center">
            {/* Logo + Title */}
            <Flex align="center" gap={3}>
              <Box color="blue.300" flexShrink={0}>
                <Plane size={40} />
              </Box>
              <Box>
                <Heading size={{ base: "md", md: "xl" }} color="blue.300">
                  {DOMAIN.name} Context Graph
                </Heading>
                <Text color="gray.400" fontSize="xs" display={{ base: "none", md: "block" }}>
                  {DOMAIN.tagline}
                </Text>
              </Box>
            </Flex>

            {/* Desktop nav */}
            <HStack gap={2} display={{ base: "none", md: "flex" }} align="center">
              {/* Status dot */}
              <HStack gap={1.5}>
                <Box
                  w={2.5}
                  h={2.5}
                  borderRadius="full"
                  bg={
                    backendStatus === "ok"
                      ? "green.400"
                      : backendStatus === "degraded"
                        ? "yellow.400"
                        : "red.400"
                  }
                />
                <Text fontSize="xs" color="gray.400">
                  {backendStatus === "ok" ? "Connected" : backendStatus === "degraded" ? "Degraded" : "Offline"}
                </Text>
              </HStack>
              <Button asChild variant="ghost" size="sm" color="gray.300" _hover={{ color: "white", bg: "gray.700" }}>
                <a href="https://github.com/pnborkar/context-graph-travel" target="_blank" rel="noopener noreferrer">
                  GitHub
                </a>
              </Button>
              <IconButton
                aria-label="Toggle color mode"
                variant="ghost"
                size="sm"
                color="gray.300"
                _hover={{ color: "white", bg: "gray.700" }}
                onClick={toggleColorMode}
              >
                {colorMode === "light" ? <Moon size={16} /> : <Sun size={16} />}
              </IconButton>
              <Button variant="ghost" size="sm" color="gray.300" _hover={{ color: "white", bg: "gray.700" }} onClick={() => setSchemaOpen(true)}>
                About & Schema
              </Button>
            </HStack>

            {/* Mobile hamburger */}
            <HStack gap={2} display={{ base: "flex", md: "none" }}>
              <Box
                w={2.5}
                h={2.5}
                borderRadius="full"
                bg={
                  backendStatus === "ok"
                    ? "green.400"
                    : backendStatus === "degraded"
                      ? "yellow.400"
                      : "red.400"
                }
              />
              <Menu.Root>
                <Menu.Trigger asChild>
                  <IconButton variant="ghost" size="sm" aria-label="Menu">
                    <MenuIcon size={18} />
                  </IconButton>
                </Menu.Trigger>
                <Portal>
                  <Menu.Positioner>
                    <Menu.Content>
                      <Menu.Item value="theme" onClick={toggleColorMode}>
                        {colorMode === "light" ? "Dark mode" : "Light mode"}
                      </Menu.Item>
                      <Menu.Item value="schema" onClick={() => setSchemaOpen(true)}>
                        About & Schema
                      </Menu.Item>
                      <Menu.Item value="github" asChild>
                        <a href="https://github.com/pnborkar/context-graph-travel" target="_blank" rel="noopener noreferrer">
                          GitHub
                        </a>
                      </Menu.Item>
                    </Menu.Content>
                  </Menu.Positioner>
                </Portal>
              </Menu.Root>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Main content */}
      <Container maxW="100%" py={{ base: 3, md: 5 }} px={{ base: 2, md: 6 }}>
        <Grid
          templateColumns={{ base: "1fr", lg: "480px 1fr 300px" }}
          gap={{ base: 3, md: 4 }}
          h={{ base: "calc(100dvh - 112px)", lg: "calc(100dvh - 130px)" }}
        >
          {/* Chat panel */}
          <GridItem
            overflow="hidden"
            display={{ base: activePanel === "chat" ? "flex" : "none", lg: "flex" }}
            flexDirection="column"
          >
            <Box
              bg="bg.surface"
              borderRadius="xl"
              borderWidth="1px"
              borderColor="border.default"
              h="100%"
              display="flex"
              flexDirection="column"
              overflow="hidden"
              shadow="sm"
            >
              <Box px={4} py={3} borderBottomWidth="1px" borderColor="border.subtle" flexShrink={0} bg="gray.100" borderTopRadius="xl">
                <Heading size="sm" color="gray.800">AI Assistant</Heading>
                <Text fontSize="xs" color="gray.500" mt={0.5}>
                  Ask about customers, refunds, policies, and disruptions
                </Text>
              </Box>
              <Box flex="1" minH={0} overflow="hidden">
                <ChatInterface
                  onGraphUpdate={handleGraphUpdate}
                  externalInput={askAboutInput}
                  onExternalInputConsumed={() => setAskAboutInput(null)}
                  onSessionChange={handleSessionChange}
                  onResponseComplete={(q, id) => { setLastQuestion(q); setCurrentDecisionId(id ?? null); }}
                />
              </Box>
            </Box>
          </GridItem>

          {/* Graph panel */}
          <GridItem
            overflow="hidden"
            display={{ base: activePanel === "graph" ? "flex" : "none", lg: "flex" }}
            flexDirection="column"
          >
            <Box
              bg="bg.surface"
              borderRadius="xl"
              borderWidth="1px"
              borderColor="border.default"
              h="100%"
              display="flex"
              flexDirection="column"
              overflow="hidden"
              shadow="sm"
            >
              <Box flex="1" minH={0}>
                <ErrorBoundary fallbackMessage="Graph visualization error">
                  <ContextGraphView
                    externalGraphData={graphData}
                    onAskAbout={handleAskAbout}
                  />
                </ErrorBoundary>
              </Box>
            </Box>
          </GridItem>

          {/* Right panel: Decision Traces */}
          <GridItem
            overflow="hidden"
            display={{ base: activePanel === "details" ? "flex" : "none", lg: "flex" }}
            flexDirection="column"
          >
            <Box
              bg="bg.surface"
              borderRadius="xl"
              borderWidth="1px"
              borderColor="border.default"
              h="100%"
              display="flex"
              flexDirection="column"
              overflow="hidden"
              shadow="sm"
            >
              <Box borderBottomWidth="1px" borderColor="border.subtle" flexShrink={0} px={4} py={3} bg="gray.100" borderTopRadius="xl">
                <Heading size="sm" color="gray.800">Decision Traces</Heading>
              </Box>
              <Box flex="1" minH={0} overflow="auto">
                <DecisionTracePanel sessionId={currentSessionId} lastQuestion={lastQuestion} currentDecisionId={currentDecisionId} />
              </Box>
            </Box>
          </GridItem>
        </Grid>
      </Container>

      {/* Mobile bottom tab bar */}
      <HStack
        display={{ base: "flex", lg: "none" }}
        justify="space-around"
        py={2}
        px={4}
        borderTop="1px solid"
        borderColor="border.default"
        bg="bg.surface"
        position="fixed"
        bottom={0}
        left={0}
        right={0}
        zIndex={10}
      >
        <IconButton
          aria-label="Chat"
          variant={activePanel === "chat" ? "solid" : "ghost"}
          colorPalette={activePanel === "chat" ? "blue" : "gray"}
          size="sm"
          onClick={() => setActivePanel("chat")}
        >
          <MessageSquare size={18} />
        </IconButton>
        <IconButton
          aria-label="Graph"
          variant={activePanel === "graph" ? "solid" : "ghost"}
          colorPalette={activePanel === "graph" ? "blue" : "gray"}
          size="sm"
          onClick={() => setActivePanel("graph")}
        >
          <Network size={18} />
        </IconButton>
        <IconButton
          aria-label="Details"
          variant={activePanel === "details" ? "solid" : "ghost"}
          colorPalette={activePanel === "details" ? "blue" : "gray"}
          size="sm"
          onClick={() => setActivePanel("details")}
        >
          <GitBranch size={18} />
        </IconButton>
      </HStack>
    </Box>
  );
}
