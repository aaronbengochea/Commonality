"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";

const PASSWORD_MIN_LENGTH = Number(process.env.NEXT_PUBLIC_PASSWORD_MIN_LENGTH) || 8;

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    username: "",
    password: "",
    firstName: "",
    lastName: "",
    nativeLanguage: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.post("/api/auth/signup", {
        username: form.username,
        password: form.password,
        first_name: form.firstName,
        last_name: form.lastName,
        native_language: form.nativeLanguage,
      });
      localStorage.setItem("token", data.access_token);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-4xl font-bold text-transparent">
            Sign Up
          </h1>
          <p className="mt-2 text-muted-foreground">
            Create your Commonality account
          </p>
        </div>

        {error && <Alert variant="destructive">{error}</Alert>}

        <form onSubmit={handleSignup} className="space-y-4">
          <Input
            type="text"
            placeholder="Username"
            value={form.username}
            onChange={(e) => update("username", e.target.value)}
            required
            minLength={3}
            maxLength={50}
          />
          <Input
            type="password"
            placeholder={`Password (min ${PASSWORD_MIN_LENGTH} characters)`}
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            required
            minLength={PASSWORD_MIN_LENGTH}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              type="text"
              placeholder="First name"
              value={form.firstName}
              onChange={(e) => update("firstName", e.target.value)}
              required
            />
            <Input
              type="text"
              placeholder="Last name"
              value={form.lastName}
              onChange={(e) => update("lastName", e.target.value)}
              required
            />
          </div>
          <Select
            value={form.nativeLanguage}
            onChange={(e) => update("nativeLanguage", e.target.value)}
            required
          >
            <option value="">Select your language</option>
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
            <option value="pt">Portuguese</option>
            <option value="zh">Chinese</option>
            <option value="ja">Japanese</option>
            <option value="ko">Korean</option>
            <option value="ar">Arabic</option>
            <option value="hi">Hindi</option>
          </Select>
          <Button type="submit" disabled={loading} className="w-full py-3">
            {loading ? "Creating account..." : "Create Account"}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/" className="text-primary hover:underline">
            Log in
          </Link>
        </p>
      </Card>
    </main>
  );
}
