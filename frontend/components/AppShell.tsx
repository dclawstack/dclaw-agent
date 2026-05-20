"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getStoredUser, logout, type User } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/agents", label: "Agents" },
  { href: "/builder", label: "Builder" },
  { href: "/marketplace", label: "Marketplace" },
  { href: "/runs", label: "Runs" },
  { href: "/tools", label: "Tools" },
  { href: "/teams", label: "Teams" },
  { href: "/memory", label: "Memory" },
];

const PUBLIC_PATHS = new Set(["/", "/login", "/register", "/marketplace"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setUser(getStoredUser());
    const onStorage = () => setUser(getStoredUser());
    const onAuthChanged = () => setUser(getStoredUser());
    window.addEventListener("storage", onStorage);
    window.addEventListener("dclaw-auth-changed", onAuthChanged);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("dclaw-auth-changed", onAuthChanged);
    };
  }, []);

  // Re-read storage on every route change too: the `storage` DOM event only
  // fires for other tabs, so navigating after login would otherwise see the
  // stale `user` state and bounce us straight back to /login.
  useEffect(() => {
    if (mounted) setUser(getStoredUser());
  }, [pathname, mounted]);

  useEffect(() => {
    if (!mounted) return;
    if (user) return;
    if (PUBLIC_PATHS.has(pathname)) return;
    router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [mounted, user, pathname, router]);

  const handleLogout = () => {
    logout();
    setUser(null);
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="font-semibold text-purple-700">
              DClaw Agent
            </Link>
            <nav className="flex items-center gap-3 text-sm">
              {NAV.map((n) => {
                const active = pathname === n.href;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    className={`px-2 py-1 rounded ${
                      active
                        ? "bg-purple-100 text-purple-800"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    {n.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="text-sm">
            {!mounted ? null : user ? (
              <div className="flex items-center gap-3">
                <span className="text-gray-700">{user.display_name}</span>
                <button
                  onClick={handleLogout}
                  className="px-2 py-1 rounded bg-gray-200 hover:bg-gray-300"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link href="/login" className="text-purple-700 hover:underline">
                  Sign in
                </Link>
                <Link
                  href="/register"
                  className="px-2 py-1 rounded bg-purple-600 text-white hover:bg-purple-700"
                >
                  Sign up
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
