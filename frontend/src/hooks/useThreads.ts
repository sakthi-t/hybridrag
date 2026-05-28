import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/clerk-react";
import { apiFetch } from "../lib/api";

interface Thread {
  id: string;
  document_id: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export function useThreads() {
  const { getToken } = useAuth();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchThreads = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const data = await apiFetch("/api/threads", {}, token);
      setThreads(data.threads || []);
    } catch (err) {
      console.error("Failed to fetch threads:", err);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const createThread = async (documentId: string, title?: string) => {
    const token = await getToken();
    const data = await apiFetch("/api/threads", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, title }),
    }, token);
    await fetchThreads();
    return data;
  };

  const deleteThread = async (id: string) => {
    const token = await getToken();
    await apiFetch(`/api/threads/${id}`, { method: "DELETE" }, token);
    setThreads((prev) => prev.filter((t) => t.id !== id));
  };

  return { threads, loading, fetchThreads, createThread, deleteThread };
}
