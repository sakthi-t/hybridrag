import { useState } from "react";
import { useClerk, SignOutButton, useUser } from "@clerk/clerk-react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { useDocuments } from "../../hooks/useDocuments";
import { useThreads } from "../../hooks/useThreads";
import { useAdmin } from "../../hooks/useAdmin";
import { apiFetch } from "../../lib/api";

interface SidebarProps {
  onUploadClick: () => void;
  activeThreadId?: string;
}

export default function Sidebar({ onUploadClick, activeThreadId }: SidebarProps) {
  const { user } = useUser();
  const { openUserProfile } = useClerk();
  const { getToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { documents, fetchDocuments, deleteDocument } = useDocuments();
  const { threads, fetchThreads, deleteThread } = useThreads();
  const { isAdmin } = useAdmin();
  const [creatingThread, setCreatingThread] = useState<string | null>(null);

  const handleDocClick = async (docId: string, docTitle: string) => {
    const existingThread = threads.find((t) => t.document_id === docId);
    if (existingThread) {
      navigate(`/chat/${existingThread.id}`);
      return;
    }
    setCreatingThread(docId);
    try {
      const token = await getToken();
      const data = await apiFetch("/api/threads", {
        method: "POST",
        body: JSON.stringify({ document_id: docId, title: `Chat about ${docTitle}` }),
      }, token);
      if (data?.id) {
        await fetchThreads();
        navigate(`/chat/${data.id}`);
      }
    } catch (err) {
      console.error("Failed to create thread:", err);
    } finally {
      setCreatingThread(null);
    }
  };

  const readyDocs = documents.filter((d) => d.ingestion_status === "DONE");
  const processingDocs = documents.filter((d) => d.ingestion_status !== "DONE" && d.ingestion_status !== "FAILED");
  const failedDocs = documents.filter((d) => d.ingestion_status === "FAILED");

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <h1 className="text-lg font-bold text-white cursor-pointer" onClick={() => navigate("/")}>
          Hybrid RAG
        </h1>
      </div>

      <div className="p-3 border-b border-gray-800">
        <button
          onClick={onUploadClick}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Documents
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="mb-3">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 mb-2">Documents</p>
          {documents.length === 0 && (
            <p className="text-xs text-gray-500 px-2">No documents yet</p>
          )}
          {processingDocs.map((doc) => (
            <div key={doc.id} className="w-full text-left px-2 py-1.5 rounded text-sm text-gray-500 truncate flex items-center gap-2 opacity-60">
              <span className="text-xs px-1 py-0.5 rounded bg-yellow-600/20 text-yellow-400 uppercase">{doc.file_type}</span>
              <span className="truncate">{doc.title}</span>
              <span className="animate-pulse text-yellow-400 text-xs ml-auto">...</span>
            </div>
          ))}
          {readyDocs.map((doc) => (
            <div key={doc.id} className="group relative">
              <button
                onClick={() => handleDocClick(doc.id, doc.title)}
                disabled={creatingThread === doc.id}
                className={`w-full text-left pl-2 pr-6 py-1.5 rounded text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors truncate flex items-center gap-2 disabled:opacity-50 ${creatingThread === doc.id ? "cursor-wait" : ""}`}
              >
                <span className="text-xs px-1 py-0.5 rounded bg-gray-700 uppercase flex-shrink-0">{doc.file_type}</span>
                <span className="truncate">{doc.title}</span>
                <svg className="w-3.5 h-3.5 text-purple-400 ml-auto flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </button>
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  await deleteDocument(doc.id);
                  fetchThreads();
                  fetchDocuments();
                }}
                className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-600/20 text-gray-500 hover:text-red-400 transition-all"
                title="Delete document"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          {failedDocs.map((doc) => (
            <div key={doc.id} className="w-full text-left px-2 py-1.5 rounded text-sm text-gray-500 truncate flex items-center gap-2 opacity-50">
              <span className="text-xs px-1 py-0.5 rounded bg-red-600/20 text-red-400 uppercase">{doc.file_type}</span>
              <span className="truncate">{doc.title}</span>
              <span className="text-red-400 text-xs ml-auto">Failed</span>
            </div>
          ))}
        </div>

        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 mb-2">Threads</p>
          {threads.length === 0 && (
            <p className="text-xs text-gray-500 px-2">No threads yet</p>
          )}
          {threads.map((thread) => (
            <div key={thread.id} className="group relative">
              <button
                onClick={() => navigate(`/chat/${thread.id}`)}
                className={`w-full text-left px-2 py-1.5 rounded text-sm transition-colors truncate ${
                  activeThreadId === thread.id
                    ? "bg-purple-600/20 text-purple-300"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white"
                }`}
              >
                {thread.title}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteThread(thread.id).then(() => {
                    if (activeThreadId === thread.id) navigate("/");
                  });
                }}
                className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-600/20 text-gray-500 hover:text-red-400 transition-all"
                title="Delete thread"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </nav>

      <div className="p-3 border-t border-gray-800 space-y-1">
        <button
          onClick={() => openUserProfile()}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-medium text-white flex-shrink-0">
            {user?.firstName?.charAt(0) || user?.emailAddresses?.[0]?.emailAddress?.charAt(0) || "U"}
          </div>
          <span className="truncate">{user?.fullName || user?.emailAddresses?.[0]?.emailAddress || "Profile"}</span>
        </button>
        {isAdmin && (
          <button
            onClick={() => navigate("/admin")}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              location.pathname === "/admin"
                ? "bg-purple-600/20 text-purple-300"
                : "text-gray-300 hover:bg-gray-800 hover:text-white"
            }`}
          >
            Admin Panel
          </button>
        )}
        <SignOutButton>
          <button className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors">
            Sign Out
          </button>
        </SignOutButton>
      </div>
    </aside>
  );
}
