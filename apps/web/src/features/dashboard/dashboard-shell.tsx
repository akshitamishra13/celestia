"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Icon } from "@/components/ui/icon";
import { FeatureCard } from "./feature-card";
import { useAuth } from "@/features/auth/auth-provider";

const snapshot = [
  { label: "Lagna", value: "Taurus", symbol: "♉" },
  { label: "Moon sign", value: "Cancer", symbol: "☾" },
  { label: "Nakshatra", value: "Pushya", symbol: "✦" },
];

export function DashboardShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) return <div className="auth-loading"><div className="loading-star"><Icon name="sparkles" /></div><p>Opening your cosmic space…</p></div>;

  const firstName = user.name.split(" ")[0];
  const initials = user.name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  const today = new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long" }).format(new Date());

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="app-shell">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} name={user.name} email={user.email} onLogout={handleLogout} />

      <main className="main-content">
        <header className="topbar">
          <button className="menu-button" aria-label="Open navigation" onClick={() => setMenuOpen(true)}><Icon name="menu" /></button>
          <div>
            <p className="topbar-eyebrow">{today}</p>
            <h1>Dashboard</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" aria-label="Notifications"><Icon name="bell" /><span className="notification-dot" /></button>
            <div className="topbar-avatar">{initials}</div>
          </div>
        </header>

        <section className="welcome-panel">
          <div className="welcome-copy">
            <span className="section-kicker"><Icon name="sparkles" /> Your cosmic space</span>
            <h2>Good morning, {firstName}.</h2>
            <p>A thoughtful look at your chart, relationships, and the patterns shaping your journey.</p>
          </div>
          <div className="sun-illustration" aria-hidden="true"><span /><span /><span /></div>
        </section>

        <section className="dashboard-section" aria-labelledby="explore-heading">
          <div className="section-heading">
            <div><span>Begin here</span><h2 id="explore-heading">Explore your astrology</h2></div>
            <a href="#">View all <Icon name="arrow" /></a>
          </div>
          <div className="feature-grid">
            <FeatureCard href="/kundli" eyebrow="Personal insights" title="Your Birth Chart" description="Explore your personalized Vedic chart and understand the placements unique to you." action="View Kundli" icon="chart" tone="sun" />
            <FeatureCard href="/compatibility" eyebrow="Two charts, one story" title="Love Compatibility" description="Discover the natural harmony, strengths, and growth points shared between two charts." action="Check compatibility" icon="heart" tone="rose" />
          </div>
        </section>

        <div className="dashboard-lower-grid">
          <section className="snapshot-card" aria-labelledby="snapshot-heading">
            <div className="card-heading"><div><span>Your chart at a glance</span><h2 id="snapshot-heading">Astrology snapshot</h2></div><button aria-label="Open astrology snapshot"><Icon name="chevron" /></button></div>
            <div className="snapshot-grid">
              {snapshot.map((item) => <div className="snapshot-item" key={item.label}><span className="snapshot-symbol">{item.symbol}</span><div><span>{item.label}</span><strong>{item.value}</strong></div></div>)}
            </div>
            <p className="prototype-note">Sample details shown for the dashboard preview.</p>
          </section>

          <section className="reports-card" aria-labelledby="reports-heading">
            <div className="card-heading"><div><span>Your library</span><h2 id="reports-heading">Recent reports</h2></div><button aria-label="Open reports"><Icon name="chevron" /></button></div>
            <div className="empty-reports"><div><Icon name="reports" /></div><strong>Your reports will live here</strong><p>Generate a Kundli or compatibility report to revisit it anytime.</p></div>
          </section>
        </div>
      </main>
    </div>
  );
}
