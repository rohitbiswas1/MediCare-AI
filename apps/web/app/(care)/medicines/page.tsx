"use client";
import { useEffect, useState } from "react";
import { Pill, Search, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { date } from "@/lib/utils";
import { useLocale } from "@/lib/i18n";
import { PageTitle, ErrorNotice, Loading } from "@/components/common";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
type Medicine = {
  id: string;
  generic_name: string;
  brand_name: string;
  strength: string;
  dosage_form: string;
  manufacturer: string | null;
  prescription_required: boolean;
  source_url: string;
  source_name: string;
  verified_at: string;
};
export default function Page() {
  const { t } = useLocale();
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<Medicine[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [searched, setSearched] = useState(false);
  useEffect(() => {
    const initial = new URLSearchParams(location.search).get("q");
    if (initial) {
      api<Medicine[]>("/medicines/search?q=" + encodeURIComponent(initial))
        .then((result) => {
          setQ(initial);
          setRows(result);
          setSearched(true);
        })
        .catch((e) => setError(e.message));
    }
  }, []);
  async function search(value = q) {
    setError("");
    setBusy(true);
    try {
      setRows(
        await api<Medicine[]>(
          "/medicines/search?q=" + encodeURIComponent(value),
        ),
      );
      setSearched(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle title={t("medicines")} subtitle={t("catalogNotice")} />
      <Card className="stack">
        <form
          className="searchbar"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <Input
            aria-label={t("searchMedicine")}
            placeholder={t("searchMedicine")}
            value={q}
            minLength={2}
            maxLength={100}
            required
            onChange={(e) => setQ(e.target.value)}
          />
          <Button disabled={busy}>
            <Search />
            {t("search")}
          </Button>
        </form>
        <ErrorNotice message={error} />
        {busy ? (
          <Loading />
        ) : rows.length ? (
          rows.map((row) => (
            <Card className="medicine-card" key={row.id}>
              <div>
                <h3>{row.brand_name || row.generic_name}</h3>
                <p>
                  {row.generic_name} · {row.strength} · {row.dosage_form}
                </p>
                {row.manufacturer && <p>{row.manufacturer}</p>}
                <p>
                  <a
                    className="source-link"
                    href={row.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {row.source_name}{" "}
                    <ExternalLink size={11} style={{ display: "inline" }} />
                  </a>{" "}
                  · Verified {date(row.verified_at)}
                </p>
              </div>
              <span
                className={`badge ${row.prescription_required ? "amber" : "teal"}`}
              >
                {row.prescription_required
                  ? "Prescription required"
                  : "Non-prescription"}
              </span>
            </Card>
          ))
        ) : (
          <div className="empty">
            <div className="icon-box purple">
              <Pill />
            </div>
            <h3>{searched ? t("noMedicines") : t("searchMedicine")}</h3>
            <p>
              Search records with traceable sources. Prices and availability are
              not estimated.
            </p>
          </div>
        )}
      </Card>
    </>
  );
}
