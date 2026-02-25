"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { User } from "@/types";
import { api } from "@/lib/api";

export function useAuth(redirectTo?: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      if (redirectTo) router.push(redirectTo);
      return;
    }

    api
      .get("/api/auth/me")
      .then((data) => {
        setUser({
          userId: data.user_id,
          username: data.username,
          firstName: data.first_name,
          lastName: data.last_name,
          nativeLanguage: data.native_language,
        });
      })
      .catch(() => {
        localStorage.removeItem("token");
        if (redirectTo) router.push(redirectTo);
      })
      .finally(() => setLoading(false));
  }, [redirectTo, router]);

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
    router.push("/login");
  }

  return { user, loading, setUser, logout };
}
