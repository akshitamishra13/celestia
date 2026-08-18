"use client";
import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/auth-provider";

export function ProtectedPage({ title, children }: { title: string; children: ReactNode }) {
  const { user, loading } = useAuth(); const router = useRouter();
  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  if (loading || !user) return <main className="flow-page"><p>Opening your cosmic space...</p></main>;
  return <main className="flow-page"><header className="flow-header"><a href="/dashboard">AstroLive</a><div><a href="/dashboard">Dashboard</a><a href="/reports">Reports</a></div></header><div className="flow-title"><span>Your cosmic space</span><h1>{title}</h1></div>{children}</main>;
}
