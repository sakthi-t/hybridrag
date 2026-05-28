import { useState, useCallback, useRef } from "react";
import { useAuth } from "@clerk/clerk-react";
import { apiStream } from "../lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations: Array<{ page: number | string; text: string }>;
  createdAt: string;
}

interface EvalMetrics {
  faithfulness: number;
  groundedness: number;
  relevance: number;
  overall: number;
}

export function useChat(threadId: string | null) {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [citations, setCitations] = useState<Array<{ page: number | string; text: string }>>([]);
  const [metrics, setMetrics] = useState<EvalMetrics | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [chunksRetrieved, setChunksRetrieved] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadMessages = useCallback((msgs: Message[]) => {
    setMessages(msgs);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!threadId || isStreaming) return;

    const token = await getToken();
    setError(null);
    setMetrics(null);
    setCitations([]);
    setStreamingText("");
    setIsStreaming(true);

    const tempUserMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text,
      citations: [],
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    let savedCitations: Array<{ page: number | string; text: string }> = [];

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const response = await apiStream(`/api/threads/${threadId}/chat/stream`, { message: text }, token);
      if (!response.ok) throw new Error(await response.text());

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));

          if (data.type === "context") {
            savedCitations = data.context.chunks || [];
            setCitations(savedCitations);
          } else if (data.type === "chunk") {
            fullText += data.content;
            setStreamingText(fullText);
          } else if (data.type === "metrics") {
            setLatencyMs(data.metrics.latency_ms);
            setChunksRetrieved(data.metrics.chunks_retrieved);
          } else if (data.type === "done") {
            const assistantMsg: Message = {
              id: data.message_id,
              role: "assistant",
              text: fullText,
              citations: savedCitations,
              createdAt: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingText("");
            setIsStreaming(false);
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") return;
      setError(err.message || "Chat error");
      setIsStreaming(false);
      setStreamingText("");
    }
  }, [threadId, isStreaming, getToken]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setStreamingText("");
  }, []);

  return {
    messages,
    streamingText,
    isStreaming,
    citations,
    metrics,
    latencyMs,
    chunksRetrieved,
    error,
    loadMessages,
    sendMessage,
    stopStreaming,
  };
}
