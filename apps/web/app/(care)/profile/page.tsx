"use client";
import { useState } from "react";
import { Check, UserRound } from "lucide-react";
import { useUser } from "@/components/shell";
import { api } from "@/lib/api";
import { useLocale, type Locale } from "@/lib/i18n";
import { PageTitle, ErrorNotice } from "@/components/common";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
export default function Page() {
  const { user, refresh } = useUser();
  const { t, setLocale } = useLocale();
  const [name, setName] = useState(user.name);
  const [language, setLanguage] = useState(user.language);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/users/me", {
        method: "PATCH",
        body: JSON.stringify({ name, language }),
      });
      setLocale(language);
      await refresh();
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        title={t("profile")}
        subtitle="Only the information needed for your account."
      />
      <Card className="narrow">
        <form className="stack" onSubmit={submit}>
          <div className="row">
            <div className="icon-box">
              <UserRound />
            </div>
            <h3>{user.name}</h3>
          </div>
          <ErrorNotice message={error} />
          <div className="field">
            <label htmlFor="profile-name">{t("name")}</label>
            <Input
              id="profile-name"
              value={name}
              required
              maxLength={100}
              onChange={(e) => {
                setName(e.target.value);
                setSaved(false);
              }}
            />
          </div>
          <div className="field">
            <label htmlFor="profile-email">{t("email")}</label>
            <Input id="profile-email" value={user.email} disabled />
            <small>
              Contact your authentication administrator to change your email.
            </small>
          </div>
          <div className="field">
            <label htmlFor="profile-language">{t("language")}</label>
            <select
              id="profile-language"
              className="input"
              value={language}
              onChange={(e) => setLanguage(e.target.value as Locale)}
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="bn">বাংলা</option>
            </select>
          </div>
          <div className="row">
            <Button disabled={busy}>{t("save")}</Button>
            {saved && (
              <span role="status" className="badge teal">
                <Check size={13} />
                {t("saved")}
              </span>
            )}
          </div>
        </form>
      </Card>
    </>
  );
}
