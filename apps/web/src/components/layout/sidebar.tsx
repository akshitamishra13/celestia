import { Icon, type IconName } from "@/components/ui/icon";

const navigation: Array<{ label: string; icon: IconName; active?: boolean }> = [
  { label: "Dashboard", icon: "dashboard", active: true },
  { label: "My Kundli", icon: "chart" },
  { label: "Compatibility", icon: "heart" },
  { label: "Reports", icon: "reports" },
  { label: "My Profile", icon: "user" },
  { label: "Settings", icon: "settings" },
];

export function Sidebar({ open, onClose, name, email, onLogout }: { open: boolean; onClose: () => void; name: string; email: string; onLogout: () => void }) {
  const initials = name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
  return (
    <>
      <button className={`sidebar-backdrop ${open ? "is-visible" : ""}`} aria-label="Close navigation" onClick={onClose} />
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark"><Icon name="sparkles" /></div>
          <span className="brand-name">AstroLive</span>
          <button className="sidebar-close" aria-label="Close navigation" onClick={onClose}><Icon name="x" /></button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          <p className="nav-eyebrow">Your space</p>
          {navigation.map((item) => (
            <a className={`nav-link ${item.active ? "is-active" : ""}`} href={item.active ? "/dashboard" : "#"} key={item.label}>
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>

        <div className="sidebar-profile">
          <div className="avatar">{initials}</div>
          <div className="profile-copy">
            <strong>{name}</strong>
            <span>{email}</span>
          </div>
          <button className="profile-logout" aria-label="Sign out" title="Sign out" onClick={onLogout}><Icon name="logout" /></button>
        </div>
      </aside>
    </>
  );
}
