import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { useChat } from "../hooks/useChat";
import { useThreads } from "../hooks/useThreads";
import { apiFetch } from "../lib/api";
import MessageBubble from "../components/chat/MessageBubble";
import StreamingMessage from "../components/chat/StreamingMessage";
import ChatInput from "../components/chat/ChatInput";
import EvaluationPanel from "../components/chat/EvaluationPanel";

interface EvalMetric {
  label: string;
  score: number;
  key: string;
}

interface EvalRecord {
  query: string;
  metrics: EvalMetric[];
  overall: number;
  at: string;
}

export default function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const { getToken } = useAuth();
  const { threads } = useThreads();
  const activeThreadId = threadId || null;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastSentRef = useRef<{ query: string } | null>(null);

  const {
    messages,
    streamingText,
    isStreaming,
    citations,
    latencyMs,
    chunksRetrieved,
    loadMessages,
    sendMessage,
  } = useChat(activeThreadId);

  const [latestMetrics, setLatestMetrics] = useState<EvalMetric[]>([]);
  const [latestOverall, setLatestOverall] = useState(0);
  const [evalHistory, setEvalHistory] = useState<EvalRecord[]>([]);
  const [evalVisible, setEvalVisible] = useState(true);
  const [prevStreaming, setPrevStreaming] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  useEffect(() => {
    if (prevStreaming && !isStreaming && lastSentRef.current) {
      const lastAssistant = messages.filter(m => m.role === "assistant").pop();
      if (lastAssistant && lastSentRef.current) {
        evaluateResponseAndSave(lastSentRef.current.query, lastAssistant.text, lastAssistant.id);
      }
      lastSentRef.current = null;
    }
    setPrevStreaming(isStreaming);
  }, [isStreaming]);

  useEffect(() => {
    if (!activeThreadId) {
      loadMessages([]);
      setLatestMetrics([]);
      setLatestOverall(0);
      setEvalHistory([]);
      return;
    }
    const load = async () => {
      try {
        const token = await getToken();
        const data = await apiFetch(`/api/threads/${activeThreadId}`, {}, token);
        const msgs = (data.messages || []).map((m: any) => ({
          id: m.id,
          role: m.role,
          text: m.text,
          citations: m.citations || [],
          createdAt: m.created_at,
        }));
        loadMessages(msgs);

        // Load all evaluations from the API response
        const history: EvalRecord[] = [];
        const msgMap = data.messages || [];
        for (let i = 0; i < msgMap.length; i++) {
          const m = msgMap[i];
          if (m.role === "assistant" && m.evaluation) {
            const ev = m.evaluation;
            const metricsList: EvalMetric[] = [
              { label: "Citation", score: ev.citation || 0, key: "citation" },
              { label: "Faithfulness", score: ev.faithfulness || 0, key: "faithfulness" },
              { label: "Groundedness", score: ev.groundedness || 0, key: "groundedness" },
              { label: "Relevance", score: ev.relevance || 0, key: "relevance" },
            ];
            const overall = Math.round(metricsList.reduce((s, m) => s + m.score, 0) / metricsList.length);
            // Find corresponding user message
            const userMsg = msgMap.slice(0, i).reverse().find((u: any) => u.role === "user");
            history.push({
              query: (userMsg?.text || "Question").slice(0, 60),
              metrics: metricsList,
              overall,
              at: m.created_at,
            });
          }
        }
        setEvalHistory(history);

        // Calculate session average from all evaluations
        if (history.length > 0) {
          const last = history[history.length - 1];
          setLatestMetrics(last.metrics);
          const allOveralls = history.map(h => h.overall);
          const avg = Math.round(allOveralls.reduce((s, o) => s + o, 0) / allOveralls.length);
          setLatestOverall(avg);
        }
      } catch (err) {
        console.error("Failed to load thread messages:", err);
      }
    };
    load();
  }, [activeThreadId, getToken, loadMessages]);

  const evaluateResponseAndSave = useCallback(async (
    queryText: string, responseText: string, messageId?: string
  ) => {
    try {
      const token = await getToken();
      const data = await apiFetch("/api/evaluate/response", {
        method: "POST",
        body: JSON.stringify({
          query: queryText,
          response: responseText,
          message_id: messageId,
          latency_ms: latencyMs,
          citations: citations,
        }),
      }, token);
      const metricsList: EvalMetric[] = [
        { label: "Citation", score: data.citation || 0, key: "citation" },
        { label: "Faithfulness", score: data.faithfulness || 0, key: "faithfulness" },
        { label: "Groundedness", score: data.groundedness || 0, key: "groundedness" },
        { label: "Relevance", score: data.relevance || 0, key: "relevance" },
      ];
      const overall = Math.round(metricsList.reduce((s, m) => s + m.score, 0) / metricsList.length);
      setLatestMetrics(metricsList);
      setEvalHistory(prev => {
        const updated = [...prev, {
          query: queryText.slice(0, 60),
          metrics: metricsList,
          overall,
          at: new Date().toISOString(),
        }];
        const allOveralls = updated.map(h => h.overall);
        const avg = Math.round(allOveralls.reduce((s, o) => s + o, 0) / allOveralls.length);
        setLatestOverall(avg);
        return updated;
      });
    } catch (err) {
      console.error("Evaluation failed:", err);
    }
  }, [getToken, latencyMs]);

  const handleSend = async (text: string) => {
    lastSentRef.current = { query: text };
    await sendMessage(text);
  };

  if (!activeThreadId) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p className="text-lg">Select a document from the sidebar to start chatting</p>
          <p className="text-sm mt-2 text-gray-500">Or upload new documents to begin</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex relative">
      <div className="flex-1 flex flex-col">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-3">
          <span className="text-sm font-medium text-gray-300">
            {threads.find(t => t.id === activeThreadId)?.title || "Chat"}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              text={msg.text}
              citations={msg.citations}
              createdAt={msg.createdAt}
            />
          ))}
          {streamingText && (
            <StreamingMessage text={streamingText} citations={citations} />
          )}
          <div ref={messagesEndRef} />
        </div>

        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>

      <EvaluationPanel
        metrics={latestMetrics}
        overall={latestOverall}
        history={evalHistory}
        latencyMs={latencyMs ?? undefined}
        chunksRetrieved={chunksRetrieved ?? undefined}
        visible={evalVisible}
        onToggle={() => setEvalVisible(!evalVisible)}
      />
    </div>
  );
}
