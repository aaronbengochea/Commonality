"use client";

import { useState, useEffect } from "react";
import { User } from "@/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // TODO: Check token and fetch /me in Phase 2
    setLoading(false);
  }, []);

  return { user, loading, setUser };
}
