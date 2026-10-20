"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Upload, Search } from "lucide-react";
import { api, type Report } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { PageTitle, ErrorNotice, Loading } from "./common";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ReportList } from "./report-list";
export function ReportsPage({ history = false }: { history?: boolean }) {
  const { t } = useLocale();
  const [rows, setRows] = useState<Report[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [hasMore, setHasMore] = useState(false);
  async function load(offset = 0) {
    try {
      const result = await api<Report[]>(`/reports?limit=50&offset=${offset}`);
      setRows((prev) => (offset ? [...(prev || []), ...result] : result));
      setHasMore(result.length === 50);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    api<Report[]>("/reports?limit=50")
      .then((result) => {
        setRows(result);
        setHasMore(result.length === 50);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <PageTitle
        title={t(history ? "history" : "reports")}
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
      <Card>
        <div className="row" style={{ marginBottom: 20 }}>
          <Search size={18} className="muted" />
          <Input
            aria-label="Filter reports"
            placeholder="Search your reports…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <ErrorNotice message={error} />
        {rows ? (
          <ReportList
            reports={rows.filter((r) =>
              r.filename.toLowerCase().includes(query.toLowerCase()),
            )}
          />
        ) : (
          <Loading />
        )}
        {hasMore && (
          <Button variant="outline" onClick={() => load(rows?.length || 0)}>
            Load more
          </Button>
        )}
      </Card>
    </>
  );
}
