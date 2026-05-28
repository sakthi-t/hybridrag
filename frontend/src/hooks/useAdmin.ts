import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/clerk-react";
import { apiFetch } from "../lib/api";

export function useAdmin() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkAdmin = useCallback(async () => {
    if (!isLoaded || !isSignedIn) {
      setLoading(false);
      return;
    }
    try {
      const token = await getToken();
      const data = await apiFetch("/api/auth/me", {}, token);
      setIsAdmin(data.is_admin === true);
    } catch {
      setIsAdmin(false);
    } finally {
      setLoading(false);
    }
  }, [getToken, isLoaded, isSignedIn]);

  useEffect(() => {
    checkAdmin();
  }, [checkAdmin]);

  return { isAdmin, loading };
}
