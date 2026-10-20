"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Sparkles,
  Upload,
  ArrowRight,
  ScanText,
  MapPin,
  ShieldCheck,
  Activity,
  Heart,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api, type Report, type Analysis } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { useUser } from "@/components/shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorNotice, PageTitle } from "@/components/common";
import { ReportList } from "@/components/report-list";
export default function Dashboard() {
  const { user } = useUser();
  const { t } = useLocale();
  const [reports, setReports] = useState<Report[]>([]);
  const [points, setPoints] = useState<
    { date: string; value: number; name: string; unit: string }[]
  >([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [summary, setSummary] = useState({
    report_count: 0,
    completed_count: 0,
  });
  useEffect(() => {
    let active = true;
    Promise.all([
      api<Report[]>("/reports?limit=100"),
      api<{ report_count: number; completed_count: number }>(
        "/users/me/summary",
      ),
    ])
      .then(async ([rows, totals]) => {
        if (!active) return;
        setSummary(totals);
        setReports(rows);
        setLoaded(true);
        const done = rows.filter((r) => r.status === "completed").slice(0, 20);
        const results = await Promise.allSettled(
          done.map((r) => api<Analysis>(`/reports/${r.id}/analysis`)),
        );
        if (!active) return;
        setPoints(
          results
            .flatMap((r, i) =>
              r.status === "fulfilled"
                ? r.value.measurements.map((m) => ({
                    date: new Date(done[i].created_at).toLocaleDateString(
                      "en-IN",
                      { day: "numeric", month: "short" },
                    ),
                    value: m.value,
                    name: m.name,
                    unit: m.unit,
                  }))
                : [],
            )
            .reverse(),
        );
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);
  const options = [...new Set(points.map((p) => `${p.name} (${p.unit})`))];
  const series = selected || options[0];
  const data = points.filter((p) => `${p.name} (${p.unit})` === series);
  return (
    <>
      <div className="greeting">
        {t("hello")}, {user.name.split(" ")[0]}{" "}
        <span aria-hidden="true">☀</span>
      </div>
      <PageTitle
        title={t("welcome")}
        subtitle={t("overviewSub")}
        action={
          <Button asChild>
            <Link href="/upload">
              <Upload />
              {t("upload")}
            </Link>
          </Button>
        }
      />
      <ErrorNotice message={error} />
      <div className="dashboard-grid">
        <div className="stack">
          <div className="stats">
            <Card className="stat">
              <div className="icon-box">
                <FileText />
              </div>
              <div>
                <div className="stat-label">{t("reportCount")}</div>
                <div className="stat-number">
                  {loaded ? summary.report_count : "—"}
                </div>
              </div>
            </Card>
            <Card className="stat">
              <div className="icon-box teal">
                <Sparkles />
              </div>
              <div>
                <div className="stat-label">{t("explanationCount")}</div>
                <div className="stat-number">
                  {loaded ? summary.completed_count : "—"}
                </div>
              </div>
            </Card>
          </div>
          <div>
            <div className="section-heading">
              <h2>{t("quick")}</h2>
            </div>
            <div className="three-grid">
              {[
                {
                  href: "/upload",
                  title: "reportTool" as const,
                  sub: "reportToolSub" as const,
                  Icon: FileText,
                  color: "",
                },
                {
                  href: "/prescriptions",
                  title: "rxTool" as const,
                  sub: "rxToolSub" as const,
                  Icon: ScanText,
                  color: "purple",
                },
                {
                  href: "/pharmacies",
                  title: "pharmacyTool" as const,
                  sub: "pharmacyToolSub" as const,
                  Icon: MapPin,
                  color: "teal",
                },
              ].map(({ href, title, sub, Icon, color }) => (
                <Link href={href} key={href}>
                  <Card className="tool-card">
                    <div className={`icon-box ${color}`}>
                      <Icon />
                    </div>
                    <ArrowRight className="arrow" />
                    <h3>{t(title)}</h3>
                    <p>{t(sub)}</p>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
          <Card>
            <div className="between">
              <h2>{t("recent")}</h2>
              <Link className="source-link row" href="/reports">
                {t("viewAll")}
                <ArrowRight size={13} />
              </Link>
            </div>
            <ReportList reports={reports.slice(0, 4)} />
          </Card>
          <Card>
            <div className="between wrap">
              <div>
                <h2>{t("activity")}</h2>
                <p className="muted" style={{ fontSize: 11, marginTop: 7 }}>
                  {t("activitySub")}
                </p>
              </div>
              {options.length > 0 && (
                <select
                  aria-label="Measurement series"
                  className="input"
                  style={{ width: "auto", maxWidth: "100%" }}
                  value={series}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {options.map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              )}
            </div>
            {data.length ? (
              <div className="chart-box">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={data}
                    margin={{ top: 10, right: 15, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      vertical={false}
                      stroke="var(--border)"
                    />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 10, fill: "var(--muted)" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "var(--muted)" }}
                      axisLine={false}
                      tickLine={false}
                      domain={["auto", "auto"]}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Line
                      type="linear"
                      dataKey="value"
                      name={series}
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="empty" style={{ padding: "30px 15px" }}>
                <Activity size={30} color="#a6b8ce" />
                <p>{t("noMeasurements")}</p>
              </div>
            )}
          </Card>
        </div>
        <aside className="stack dashboard-aside">
          <Card className="privacy-card">
            <div className="privacy-shield">
              <ShieldCheck />
            </div>
            <span className="eyebrow">PRIVATE BY DESIGN</span>
            <h3>{t("privacyTitle")}</h3>
            <p>{t("privacyBody")}</p>
            <Link href="/privacy">
              {t("readPrivacy")}
              <ArrowRight size={13} />
            </Link>
          </Card>
          <Card>
            <div className="row">
              <Heart size={17} color="#0d9488" />
              <h3>A good place to start</h3>
            </div>
            <div className="steps-list">
              {[
                {
                  title: t("upload"),
                  body: "A clear, well-lit scan helps us read your report.",
                },
                {
                  title: t("source"),
                  body: "Check extracted values against the original document.",
                },
                {
                  title: "Talk to your clinician",
                  body: "Bring your report and questions to a qualified professional.",
                },
              ].map((step, i) => (
                <div className="step" key={i}>
                  <span className="step-number">{i + 1}</span>
                  <div>
                    <h4>{step.title}</h4>
                    <p>{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
          <div className="notice" style={{ fontSize: 10 }}>
            <ShieldCheck />
            <span>{t("disclaimer")}</span>
          </div>
        </aside>
      </div>
    </>
  );
}
