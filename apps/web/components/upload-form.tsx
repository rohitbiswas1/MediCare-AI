"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileText,
  ShieldCheck,
  ArrowRight,
  LoaderCircle,
  Info,
} from "lucide-react";
import { api } from "@/lib/api";
import { useUser } from "./shell";
import { useLocale } from "@/lib/i18n";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { ErrorNotice, SafetyNotice } from "./common";
export function UploadForm({
  kind = "document",
  prescription = false,
}: {
  kind?: string;
  prescription?: boolean;
}) {
  const { t } = useLocale();
  const { user } = useUser();
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [type, setType] = useState(kind);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  function select(f: File | undefined) {
    setError("");
    if (f && f.size > 15 * 1024 * 1024) {
      setError("Choose a file no larger than 15 MB.");
      return;
    }
    setFile(f || null);
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !consent) return;
    setBusy(true);
    setError("");
    const data = new FormData();
    data.append("file", file);
    data.append("consent", "true");
    data.append("report_type", type);
    try {
      const result = await api<{ id: string }>(
        prescription ? "/prescriptions/upload" : "/reports/upload",
        { method: "POST", body: data },
      );
      router.push(
        `${prescription ? "/prescriptions" : "/reports"}/${result.id}`,
      );
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }
  return (
    <div className="upload-layout">
      <Card>
        <form className="stack" onSubmit={submit}>
          <ErrorNotice message={error} />
          {!prescription && (
            <div className="field">
              <label htmlFor="report-type">{t("reportType")}</label>
              <select
                id="report-type"
                className="input"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                <option value="document">{t("document")}</option>
                <option value="blood_test">{t("blood")}</option>
                <option value="ecg">{t("ecg")}</option>
                <option value="xray">{t("xray")}</option>
                <option value="heart_rate">{t("heart")}</option>
              </select>
            </div>
          )}
          <label
            className={`dropzone ${drag ? "drag" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              select(e.dataTransfer.files[0]);
            }}
          >
            <input
              ref={input}
              type="file"
              accept={
                prescription
                  ? ".pdf,.png,.jpg,.jpeg"
                  : ".pdf,.png,.jpg,.jpeg,.dcm"
              }
              aria-label={t("choose")}
              onChange={(e) => select(e.target.files?.[0])}
            />
            <div
              className="icon-box"
              style={{ background: "var(--surface)", height: 60, width: 60 }}
            >
              <UploadCloud size={29} />
            </div>
            <h3>{t("drop")}</h3>
            <p>{t("browse")}</p>
            <span className="button button-outline button-sm">
              {t("choose")}
            </span>
            <small className="muted">
              {prescription ? "PDF, JPG, PNG · Max 15 MB" : t("uploadHint")}
            </small>
          </label>
          {file && (
            <div className="file-selected">
              <FileText color="#2563eb" />
              <div className="grow">
                <strong>{file.name}</strong>
                <div className="muted">{(file.size / 1024).toFixed(1)} KB</div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setFile(null);
                  if (input.current) input.current.value = "";
                }}
              >
                {t("cancel")}
              </Button>
            </div>
          )}
          <label className="checkbox">
            <input
              type="checkbox"
              required
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            <span>{t("uploadConsent")}</span>
          </label>
          <Button type="submit" disabled={!file || !consent || busy}>
            {busy ? (
              <>
                <LoaderCircle className="spinner" />
                {t("processing")}
              </>
            ) : (
              <>
                {t("submitUpload")}
                <ArrowRight />
              </>
            )}
          </Button>
        </form>
      </Card>
      <div className="stack">
        <Card>
          <div className="icon-box teal">
            <ShieldCheck />
          </div>
          <h3 style={{ marginTop: 20 }}>{t("privacyTitle")}</h3>
          <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>
            {t("privacyBody")}
          </p>
          <div className="steps-list">
            <div className="step">
              <span className="step-number">1</span>
              <div>
                <h4>Choose a clear document</h4>
                <p>Include the full page. Avoid glare and blur.</p>
              </div>
            </div>
            <div className="step">
              <span className="step-number">2</span>
              <div>
                <h4>Review the extracted text</h4>
                <p>Handwriting and complex layouts may need manual review.</p>
              </div>
            </div>
            <div className="step">
              <span className="step-number">3</span>
              <div>
                <h4>Keep your clinician involved</h4>
                <p>Context matters. This is not a diagnosis.</p>
              </div>
            </div>
          </div>
        </Card>
        <SafetyNotice />
        {user.mode !== "production" && (
          <div className="notice warning">
            <Info />
            <span>
              Development uploads receive structural checks. Full antivirus
              scanning is mandatory in production.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
