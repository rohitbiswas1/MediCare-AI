"use client";
import Link from "next/link";
import { FileText, ArrowUpRight, Upload } from "lucide-react";
import type { Report } from "@/lib/api";
import { date } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";
import { Button } from "./ui/button";
export function ReportList({ reports }: { reports: Report[] }) {
  const { t } = useLocale();
  if (!reports.length)
    return (
      <div className="empty">
        <div className="icon-box">
          <FileText />
        </div>
        <h3>{t("emptyTitle")}</h3>
        <p>{t("emptyBody")}</p>
        <Button asChild variant="outline" size="sm">
          <Link href="/upload">
            <Upload />
            {t("upload")}
          </Link>
        </Button>
      </div>
    );
  return (
    <div className="report-list">
      {reports.map((report) => (
        <Link
          className="report-row"
          href={"/reports/" + report.id}
          key={report.id}
        >
          <div className="icon-box">
            <FileText />
          </div>
          <div className="grow">
            <div className="report-name">{report.filename}</div>
            <div className="report-meta">
              {report.report_type.replaceAll("_", " ")} &nbsp; · &nbsp;{" "}
              {date(report.created_at)}
            </div>
          </div>
          <span
            className={`badge ${report.status === "completed" ? "teal" : report.status === "failed" ? "amber" : "grey"}`}
          >
            {report.status === "completed" ? "Ready to review" : report.status}
          </span>
          <ArrowUpRight size={15} className="muted" />
        </Link>
      ))}
    </div>
  );
}
