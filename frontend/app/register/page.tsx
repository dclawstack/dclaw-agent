"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { register } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(email, password, displayName);
      router.push(next);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-16 p-6 bg-white rounded shadow">
      <h1 className="text-2xl font-bold mb-4">Create your account</h1>
      <form onSubmit={onSubmit} className="space-y-3">
        <input
          type="text"
          required
          placeholder="Display name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Password (min 8 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        {error && (
          <div className="text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded text-sm">
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white rounded py-2 disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-gray-600 mt-4">
        Already have one?{" "}
        <Link href="/login" className="text-purple-700 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
