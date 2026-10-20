"use client";
import { createContext, useContext, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  HeartPulse,
  ScanLine,
  Pill,
  MapPin,
  History,
  UserRound,
  ShieldCheck,
  MessageCircle,
  LogOut,
  Menu,
  ChevronRight,
  Heart,
  Stethoscope,
  LockKeyhole,
} from "lucide-react";
import { api, type User } from "@/lib/api";
import { useLocale, type Key } from "@/lib/i18n";
import {
  Brand,
  LanguageSelect,
  ThemeToggle,
  Loading,
  ErrorNotice,
} from "./common";
import { Button } from "./ui/button";
const UserContext = createContext<{
  user: User;
  refresh: () => Promise<void>;
} | null>(null);
export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("Missing user context");
  return ctx;
}
const groups: [Key, [string, Key, typeof FileText][]][] = [
  [
    "healthSpace",
    [
      ["/dashboard", "dashboard", LayoutDashboard],
      ["/reports", "reports", FileText],
      ["/ecg", "ecg", HeartPulse],
      ["/xray", "xray", ScanLine],
      ["/heart-rate", "heart", Heart],
      ["/prescriptions", "prescriptions", Pill],
    ],
  ],
  [
    "care",
    [
      ["/medicines", "medicines", Pill],
      ["/pharmacies", "pharmacies", MapPin],
    ],
  ],
  [
    "account",
    [
      ["/history", "history", History],
      ["/profile", "profile", UserRound],
      ["/privacy", "privacy", ShieldCheck],
      ["/help", "help", MessageCircle],
    ],
  ],
];
export function Shell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const path = usePathname();
  const { t } = useLocale();
  async function refresh() {
    setUser(await api<User>("/users/me"));
  }
  useEffect(() => {
    let live = true;
    api<User>("/users/me")
      .then((u) => {
        if (live) setUser(u);
      })
      .catch((err) => {
        if (err.status === 401) router.replace("/login");
        else if (live) setError(err.message);
      });
    return () => {
      live = false;
    };
  }, [router]);
  const title =
    groups.flatMap((g) => g[1]).find(([href]) => path.startsWith(href))?.[1] ||
    "upload";
  if (!user)
    return (
      <main className="main-content">
        <Brand />
        <ErrorNotice message={error} />
        {!error && <Loading />}
      </main>
    );
  return (
    <UserContext.Provider value={{ user, refresh }}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="app-layout">
        {open && (
          <div className="sidebar-overlay" onClick={() => setOpen(false)} />
        )}
        <aside
          className={`sidebar ${open ? "open" : ""}`}
          aria-label="Main navigation"
        >
          <Brand />
          <nav>
            {groups.map(([label, links]) => (
              <div className="nav-group" key={label}>
                <div className="nav-label">{t(label)}</div>
                {links.map(([href, key, Icon]) => (
                  <Link
                    className={`nav-link ${path.startsWith(href) ? "active" : ""}`}
                    href={href}
                    key={href}
                    onClick={() => setOpen(false)}
                    aria-current={path.startsWith(href) ? "page" : undefined}
                  >
                    <Icon />
                    {t(key)}
                  </Link>
                ))}
              </div>
            ))}
            {user.role === "admin" && (
              <Link className="nav-link" href="/admin">
                <Stethoscope />
                {t("admin")}
              </Link>
            )}
          </nav>
          <div className="sidebar-bottom">
            <div className="private-note">
              <div className="row">
                <LockKeyhole />
                <strong>{t("privacyTitle")}</strong>
              </div>
              <p style={{ marginTop: 7 }}>{t("privacyBody")}</p>
            </div>
            <button
              className="nav-link"
              style={{ width: "100%", border: 0, background: "transparent" }}
              onClick={async () => {
                try {
                  await api("/auth/logout", { method: "POST" });
                  router.replace("/login");
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              <LogOut />
              {t("logout")}
            </button>
          </div>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <Button
              variant="ghost"
              size="icon"
              className="mobile-menu"
              aria-label="Open navigation"
              aria-expanded={open}
              onClick={() => setOpen(!open)}
            >
              <Menu />
            </Button>
            <div className="breadcrumb">
              <span>MediCare AI</span>
              <ChevronRight size={13} />
              <span>{t(title)}</span>
            </div>
            <div className="top-actions">
              <LanguageSelect />
              <ThemeToggle />
              <span
                style={{ height: 24, borderLeft: "1px solid var(--border)" }}
              />
              <Link
                href="/profile"
                className="avatar"
                aria-label={t("profile")}
              >
                {user.name.charAt(0).toUpperCase() || "M"}
              </Link>
            </div>
          </header>
          {user.mode !== "production" && (
            <div className="dev-banner">{t("development")}</div>
          )}
          <main className="main-content" id="main">
            <ErrorNotice message={error} />
            {children}
            <footer className="page-footer">
              <span className="safety-footer">
                <ShieldCheck />
                {t("disclaimer")}
              </span>
              <span>© {new Date().getFullYear()} MediCare AI</span>
            </footer>
          </main>
        </div>
      </div>
    </UserContext.Provider>
  );
}
