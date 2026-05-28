import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/clerk-react";
import { apiFetch } from "../lib/api";

interface Document {
  id: string;
  title: string;
  original_filename: string;
  file_type: string;
  scope: string;
  ingestion_status: string;
  created_at: string;
}

export function useDocuments() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchDocuments = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    setLoading(true);
    try {
      const token = await getToken();
      const data = await apiFetch("/api/documents", {}, token);
      setDocuments(data.documents || []);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setLoading(false);
    }
  }, [getToken, isLoaded, isSignedIn]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const deleteDocument = async (id: string) => {
    const token = await getToken();
    await apiFetch(`/api/documents/${id}`, { method: "DELETE" }, token);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  return { documents, loading, fetchDocuments, deleteDocument };
}
