"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Pill, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { date } from "@/lib/utils";
import { PageTitle, ErrorNotice } from "@/components/common";
import { UploadForm } from "@/components/upload-form";
import { Card } from "@/components/ui/card";
export default function Page() {
  const { t } = useLocale();
  const [rows, setRows] = useState<
    { id: string; created_at: string; confirmed_at: string | null }[]
  >([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<typeof rows>("/prescriptions")
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <PageTitle title={t("prescriptions")} subtitle={t("rxToolSub")} />
      <div className="notice warning" style={{ marginBottom: 24 }}>
        <Pill />
        <span>{t("rxNotice")}</span>
      </div>
      <UploadForm prescription />
      {rows.length > 0 && (
        <Card style={{ marginTop: 24 }}>
          <h2>Prescription history</h2>
          {rows.map((row) => (
            <Link
              className="report-row"
              key={row.id}
              href={`/prescriptions/${row.id}`}
            >
              <div className="icon-box purple">
                <Pill />
              </div>
              <div className="grow">
                <h3 style={{ fontSize: 13 }}>
                  Prescription · {date(row.created_at)}
                </h3>
                <span className="muted" style={{ fontSize: 11 }}>
                  {row.confirmed_at ? "Confirmed by you" : "Awaiting review"}
                </span>
              </div>
              <ArrowRight size={16} />
            </Link>
          ))}
        </Card>
      )}
      <ErrorNotice message={error} />
    </>
  );
}
