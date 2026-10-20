"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Trash2, Check, LockKeyhole } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { PageTitle, ErrorNotice } from "@/components/common";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
type Consent = {
  third_party_ai: boolean;
  training: boolean;
  retention_days: number;
  records: {
    purpose: string;
    granted: boolean;
    created_at: string;
    policy_version: string;
  }[];
};
export default function Page() {
  const { t } = useLocale();
  const router = useRouter();
  const [data, setData] = useState<Consent | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saved, setSaved] = useState(false);
  async function load() {
    setData(await api<Consent>("/users/me/consent"));
  }
  useEffect(() => {
    api<Consent>("/users/me/consent")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  async function change(value: boolean) {
    const previous = data;
    setData((current) =>
      current ? { ...current, third_party_ai: value } : current,
    );
    setSaved(false);
    setBusy(true);
    setError("");
    try {
      await api("/users/me/consent", {
        method: "PATCH",
        body: JSON.stringify({ third_party_ai: value }),
      });
      await load();
      setSaved(true);
    } catch (e) {
      setData(previous);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setBusy(true);
    setError("");
    try {
      await api("/users/me", {
        method: "DELETE",
        body: JSON.stringify({ confirmation: confirm }),
      });
      router.replace("/");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle title={t("privacy")} subtitle={t("privacyBody")} />
      <div className="stack narrow">
        <ErrorNotice message={error} />
        <Card>
          <div className="row">
            <div className="icon-box teal">
              <ShieldCheck />
            </div>
            <h2>{t("privacyTitle")}</h2>
          </div>
          <div className="settings-row">
            <div>
              <h3>{t("aiConsent")}</h3>
              <p>{t("aiConsentBody")}</p>
            </div>
            <input
              type="checkbox"
              aria-label={t("aiConsent")}
              checked={data?.third_party_ai || false}
              disabled={!data || busy}
              onChange={(e) => change(e.target.checked)}
            />
          </div>
          <div className="settings-row">
            <div>
              <h3>{t("training")}</h3>
              <p>Uploaded records are excluded from training datasets.</p>
            </div>
            <span className="badge teal">{t("disabled")}</span>
          </div>
          <div className="settings-row">
            <div>
              <h3>{t("retention")}</h3>
              <p>
                Documents and their extracted information expire automatically.
                You can delete them sooner.
              </p>
            </div>
            <span className="badge grey">
              {data ? `${data.retention_days} days` : "—"}
            </span>
          </div>
          {saved && (
            <div className="badge teal" role="status">
              <Check size={12} />
              {t("saved")}
            </div>
          )}
        </Card>
        <div className="notice">
          <LockKeyhole />
          <span>
            Access requires your session. Downloads use authorization or
            short-lived links. Your account data is not shared with medicine
            catalog or map searches.
          </span>
        </div>
        <Card>
          <h3>Consent history</h3>
          {data?.records.length ? (
            data.records.slice(0, 10).map((r, i) => (
              <div className="settings-row" key={i}>
                <div>
                  <p>
                    {r.purpose.replaceAll("_", " ")} · policy {r.policy_version}
                  </p>
                  <small className="muted">
                    {new Date(r.created_at).toLocaleString()}
                  </small>
                </div>
                <span className={`badge ${r.granted ? "teal" : "grey"}`}>
                  {r.granted ? "Granted" : "Withdrawn"}
                </span>
              </div>
            ))
          ) : (
            <p className="muted" style={{ marginTop: 15 }}>
              No recorded choices yet.
            </p>
          )}
        </Card>
        <Card>
          <h3>{t("deleteAccount")}</h3>
          <p className="muted" style={{ fontSize: 12, margin: "12px 0 20px" }}>
            {t("deleteAccountBody")}
          </p>
          {show ? (
            <div className="stack">
              <label className="field">
                Type DELETE MY ACCOUNT to confirm
                <Input
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  autoComplete="off"
                />
              </label>
              <div className="row">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShow(false);
                    setConfirm("");
                  }}
                >
                  {t("cancel")}
                </Button>
                <Button
                  variant="destructive"
                  disabled={confirm !== "DELETE MY ACCOUNT" || busy}
                  onClick={remove}
                >
                  <Trash2 />
                  {t("deleteAccount")}
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="destructive" onClick={() => setShow(true)}>
              <Trash2 />
              {t("deleteAccount")}
            </Button>
          )}
        </Card>
      </div>
    </>
  );
}
