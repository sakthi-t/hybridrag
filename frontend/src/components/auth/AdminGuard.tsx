import { Navigate } from "react-router-dom";
import { useAdmin } from "../../hooks/useAdmin";

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading } = useAdmin();

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
