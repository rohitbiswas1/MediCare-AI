"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  Trash2,
  FileText,
  Info,
  RefreshCw,
} from "lucide-react";
import { api, type Report, type Analysis } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import {
  analysisSummary,
  analysisLimitations,
  measurementExplanation,
} from "@/lib/medical-copy";
import { date } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ErrorNotice,
  SafetyNotice,
  Loading,
  PageTitle,
} from "@/components/common";
export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { t, locale } = useLocale();
  const [report, setReport] = useState<Report | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const row = await api<Report>(`/reports/${id}`);
        if (!active) return;
        setReport(row);
        if (row.status === "completed") {
          const [a, e] = await Promise.all([
            api<Analysis>(`/reports/${id}/analysis`),
            api<{ text: string }>(`/reports/${id}/extraction`),
          ]);
          if (active) {
            setAnalysis(a);
            setText(e.text);
          }
        } else if (["queued", "processing"].includes(row.status)) {
          timer = setTimeout(load, 2500);
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id]);
  async function remove() {
    setDeleting(true);
    try {
      await api(`/reports/${id}`, { method: "DELETE" });
      router.push("/reports");
    } catch (e) {
      setError((e as Error).message);
      setConfirm(false);
      setDeleting(false);
    }
  }
  function exportResult() {
    if (!analysis) return;
    const blob = new Blob(
      [JSON.stringify({ filename: report?.filename, ...analysis }, null, 2)],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "medicare-explanation.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <Link
        href="/reports"
        className="source-link row"
        style={{ marginBottom: 20 }}
      >
        <ArrowLeft size={14} />
        {t("reports")}
      </Link>
      <ErrorNotice message={error} />
      {!report && !error && <Loading />}
      {report && (
        <>
          <PageTitle
            title={report.filename}
            subtitle={`${report.report_type.replaceAll("_", " ")} · ${date(report.created_at)}`}
            action={
              <div className="row">
                <Button asChild variant="outline">
                  <a href={`/api/v1/reports/${id}/download`}>
                    <Download />
                    {t("download")}
                  </a>
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={t("delete")}
                  onClick={() => setConfirm(true)}
                >
                  <Trash2 />
                </Button>
              </div>
            }
          />
          <div className="stack">
            <SafetyNotice />
            {report.status === "failed" && (
              <div className="card stack">
                <ErrorNotice message={report.error} />
                <Button
                  onClick={async () => {
                    try {
                      await api(`/reports/${id}/analyze`, { method: "POST" });
                      location.reload();
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  <RefreshCw />
                  {t("retry")}
                </Button>
              </div>
            )}
            {["queued", "processing"].includes(report.status) && (
              <Card>
                <Loading />
                <p className="muted" style={{ textAlign: "center" }}>
                  {t("pending")}
                </p>
              </Card>
            )}
            {analysis && (
              <>
                <Card>
                  <div className="between wrap">
                    <div className="row">
                      <div className="icon-box teal">
                        <FileText />
                      </div>
                      <div>
                        <span
                          className={`badge ${analysis.status === "informational" ? "teal" : "amber"}`}
                        >
                          {analysis.status === "unavailable"
                            ? t("unavailable")
                            : t("checked")}
                        </span>
                        <h2 style={{ marginTop: 8 }}>Your report, explained</h2>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={exportResult}>
                      <Download />
                      {t("downloadResult")}
                    </Button>
                  </div>
                  <p style={{ marginTop: 20, fontSize: 13 }}>
                    {analysisSummary(locale, analysis)}
                  </p>
                  {locale !== "en" && (
                    <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                      Original report text and numerical values are preserved.
                      Review the original with a qualified professional.
                    </p>
                  )}
                </Card>
                <div className="two-grid">
                  <Card>
                    <h2>{t("measurements")}</h2>
                    {analysis.measurements.length ? (
                      analysis.measurements.map((m, i) => (
                        <div className="measurement" key={i}>
                          <div className="between">
                            <h3>{m.name}</h3>
                            <span
                              className={`badge ${m.comparison === "within_reported_range" ? "teal" : "amber"}`}
                            >
                              {t(
                                m.comparison === "above_reported_range"
                                  ? "above"
                                  : m.comparison === "below_reported_range"
                                    ? "below"
                                    : m.comparison === "within_reported_range"
                                      ? "within"
                                      : "noReference",
                              )}
                            </span>
                          </div>
                          <div className="measurement-value">
                            {m.value} <small>{m.unit}</small>
                          </div>
                          <p>{measurementExplanation(locale, m)}</p>
                          <blockquote className="source-quote">
                            {m.source_quote}
                          </blockquote>
                        </div>
                      ))
                    ) : (
                      <div className="empty">
                        <Info size={25} />
                        <p>
                          No supported measurements found. Nothing has been
                          estimated.
                        </p>
                      </div>
                    )}
                  </Card>
                  <Card>
                    <h2>{t("originalText")}</h2>
                    <p
                      className="muted"
                      style={{ fontSize: 11, margin: "10px 0 15px" }}
                    >
                      Compare this transcription with the original document.
                    </p>
                    <pre className="raw-text">
                      {text || "No readable text was extracted."}
                    </pre>
                    <small className="muted">
                      Extraction is unverified until reviewed.
                    </small>
                  </Card>
                </div>
                <Card>
                  <h3>What this result can and cannot tell you</h3>
                  <ul
                    className="muted"
                    style={{
                      fontSize: 12,
                      lineHeight: 1.9,
                      paddingLeft: 18,
                      marginTop: 12,
                    }}
                  >
                    {analysisLimitations(locale, analysis).map((l) => (
                      <li key={l}>{l}</li>
                    ))}
                  </ul>
                  <div className="badge grey" style={{ marginTop: 12 }}>
                    Model status: {analysis.model.validation}
                  </div>
                </Card>
                <div className="notice warning">
                  <Info />
                  <span>{t("emergency")}</span>
                </div>
              </>
            )}
          </div>
        </>
      )}
      {confirm && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-title"
            className="modal"
          >
            <h2 id="delete-title">{t("deleteConfirm")}</h2>
            <p>
              This also removes extraction, explanations, and any linked
              prescription. This cannot be undone.
            </p>
            <div className="row">
              <Button
                variant="outline"
                autoFocus
                onClick={() => setConfirm(false)}
              >
                {t("cancel")}
              </Button>
              <Button
                variant="destructive"
                disabled={deleting}
                onClick={remove}
              >
                {t("delete")}
              </Button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
