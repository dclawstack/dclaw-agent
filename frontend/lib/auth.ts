"use client";

const BASE = process.env.NEXT_PUBLIC_API_URL || "";
const TOKEN_KEY = "dclaw_token";
const USER_KEY = "dclaw_user";

export type User = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

function storeAuth(resp: AuthResponse) {
  localStorage.setItem(TOKEN_KEY, resp.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
}

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE}/api/v1/agent/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await res.text()) || "Login failed");
  const data = (await res.json()) as AuthResponse;
  storeAuth(data);
  return data.user;
}

export async function register(
  email: string,
  password: string,
  display_name: string
): Promise<User> {
  const res = await fetch(`${BASE}/api/v1/agent/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name }),
  });
  if (!res.ok) throw new Error((await res.text()) || "Register failed");
  const data = (await res.json()) as AuthResponse;
  storeAuth(data);
  return data.user;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
