import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/clerk-react";
import { apiFetch } from "../lib/api";

export default function AdminPage() {
  const { getToken } = useAuth();
  const [users, setUsers] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [tab, setTab] = useState<"users" | "documents">("users");
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    const token = await getToken();
    try {
      const [usersData, statsData, meData] = await Promise.all([
        apiFetch("/api/admin/users", {}, token),
        apiFetch("/api/admin/stats", {}, token),
        apiFetch("/api/auth/me", {}, token),
      ]);
      setUsers(usersData.users || []);
      setStats(statsData);
      setCurrentUserId(meData.id);
    } catch (err) {
      console.error(err);
    }
  }, [getToken]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const deleteUser = async (id: string) => {
    const token = await getToken();
    await apiFetch(`/api/admin/users/${id}`, { method: "DELETE" }, token);
    setUsers((prev) => prev.filter((u) => u.id !== id));
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Admin Dashboard</h1>

      {stats && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: "Users", value: stats.total_users },
            { label: "Documents", value: stats.total_documents },
            { label: "Jobs Done", value: `${stats.ingestion_jobs?.done || 0}/${stats.ingestion_jobs?.total || 0}` },
          ].map((s) => (
            <div key={s.label} className="bg-gray-800 rounded-xl p-4">
              <p className="text-sm text-gray-400">{s.label}</p>
              <p className="text-2xl font-bold text-white mt-1">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-4 mb-6">
        {(["users", "documents"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? "bg-purple-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "users" && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Name</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Email</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Role</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Created</th>
                <th className="text-right px-4 py-3 text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-800/50 hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-gray-200">{u.name || u.email || "—"}</td>
                  <td className="px-4 py-3 text-gray-400">{u.email || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      u.role === "admin" ? "bg-purple-600/20 text-purple-300" : "bg-gray-700 text-gray-400"
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">
                    {u.id !== currentUserId && (
                      <button
                        onClick={() => deleteUser(u.id)}
                        className="text-red-400 hover:text-red-300 text-xs"
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "documents" && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
          <p className="text-gray-400">Document management is handled by each user from their sidebar.</p>
          <p className="text-sm text-gray-500 mt-2">Deleting a document removes its B2 objects, Chroma vectors, threads, messages, and evaluations.</p>
        </div>
      )}
    </div>
  );
}
