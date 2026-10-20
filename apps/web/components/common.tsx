"use client";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ShieldCheck,
  LoaderCircle,
  Languages,
  Moon,
  Sun,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useLocale, type Locale } from "@/lib/i18n";
import { Button } from "./ui/button";
export function Brand() {
  return (
    <Link href="/" className="brand" aria-label="MediCare AI home">
      <span className="brand-icon">
        <Activity />
      </span>
      MediCare <em>AI</em>
    </Link>
  );
}
export function LanguageSelect() {
  const { locale, setLocale, t } = useLocale();
  return (
    <div className="row" style={{ gap: 5 }}>
      <Languages size={15} className="muted" />
      <select
        aria-label={t("language")}
        className="language-select"
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
      >
        <option value="en">English</option>
        <option value="hi">हिन्दी</option>
        <option value="bn">বাংলা</option>
      </select>
    </div>
  );
}
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Toggle dark mode"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      <Sun className="dark:hidden" />
      <Moon className="hidden dark:block" />
    </Button>
  );
}
export function ErrorNotice({
  message,
}: {
  message: string | null | undefined;
}) {
  if (!message) return null;
  return (
    <div role="alert" className="notice error">
      <AlertCircle />
      <span>{message}</span>
    </div>
  );
}
export function SafetyNotice() {
  const { t } = useLocale();
  return (
    <div className="notice">
      <ShieldCheck />
      <span>{t("disclaimer")}</span>
    </div>
  );
}
export function Loading() {
  const { t } = useLocale();
  return (
    <div className="empty" role="status">
      <LoaderCircle className="spinner" size={27} />
      <p>{t("loading")}</p>
    </div>
  );
}
export function PageTitle({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading between">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
