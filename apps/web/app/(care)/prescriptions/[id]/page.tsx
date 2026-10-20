"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Trash2, Check, MapPin, Search } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { PageTitle, ErrorNotice, Loading } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
const item = z.object({
  name: z.string().min(1).max(200),
  strength: z.string().max(100),
  dosage_form: z.string().max(100),
  instructions: z.string().max(1000),
});
const schema = z.object({
  items: z.array(item).min(1).max(30),
  confirmed: z.literal(true),
});
type Values = z.infer<typeof schema>;
type Detail = {
  id: string;
  report_id: string;
  status: string;
  error: string | null;
  confirmed_at: string | null;
  extracted_text: string;
  items: z.infer<typeof item>[];
  candidates: z.infer<typeof item>[];
};
const blank = { name: "", strength: "", dosage_form: "", instructions: "" };
export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { t } = useLocale();
  const [data, setData] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { items: [blank] },
  });
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "items",
  });
  const { reset } = form;
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const result = await api<Detail>(`/prescriptions/${id}`);
        if (!active) return;
        setData(result);
        if (result.candidates?.length && !result.items.length)
          reset({ items: result.candidates });
        if (result.items.length)
          reset({ items: result.items, confirmed: true });
        if (["queued", "processing"].includes(result.status))
          timer = setTimeout(load, 2500);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    void load();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id, reset]);
  async function submit(values: Values) {
    setError("");
    try {
      await api(`/prescriptions/${id}/confirm`, {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle title={t("confirmRx")} subtitle={t("rxNotice")} />
      <ErrorNotice message={error} />
      {!data && <Loading />}
      {data && (
        <div className="stack">
          {data.error && <ErrorNotice message={data.error} />}
          <div className="two-grid">
            <Card>
              <div className="between">
                <h2>{t("originalText")}</h2>
                <Link
                  className="source-link"
                  href={`/reports/${data.report_id}`}
                >
                  View report
                </Link>
              </div>
              {["queued", "processing"].includes(data.status) ? (
                <Loading />
              ) : (
                <pre className="raw-text" style={{ marginTop: 20 }}>
                  {data.extracted_text ||
                    "No legible text found. Confirm directly with the prescriber."}
                </pre>
              )}
              <p className="muted" style={{ fontSize: 11, marginTop: 15 }}>
                Text is preserved verbatim. No unreadable medicine name or dose
                is guessed.
              </p>
            </Card>
            <Card>
              <form className="stack" onSubmit={form.handleSubmit(submit)}>
                {fields.map((field, i) => (
                  <div
                    className="stack"
                    style={{
                      gap: 14,
                      borderBottom: "1px solid var(--border)",
                      paddingBottom: 20,
                    }}
                    key={field.id}
                  >
                    <div className="between">
                      <h3>Medicine {i + 1}</h3>
                      {fields.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          aria-label={`Remove medicine ${i + 1}`}
                          onClick={() => remove(i)}
                        >
                          <Trash2 />
                        </Button>
                      )}
                    </div>
                    <div className="field">
                      <label htmlFor={`name-${i}`}>{t("medicineName")}</label>
                      <Input
                        id={`name-${i}`}
                        required
                        {...form.register(`items.${i}.name`)}
                      />
                    </div>
                    <div className="two-grid">
                      <div className="field">
                        <label htmlFor={`strength-${i}`}>{t("strength")}</label>
                        <Input
                          id={`strength-${i}`}
                          {...form.register(`items.${i}.strength`)}
                        />
                      </div>
                      <div className="field">
                        <label htmlFor={`form-${i}`}>{t("form")}</label>
                        <Input
                          id={`form-${i}`}
                          {...form.register(`items.${i}.dosage_form`)}
                        />
                      </div>
                    </div>
                    <div className="field">
                      <label htmlFor={`instructions-${i}`}>
                        {t("instructions")}
                      </label>
                      <textarea
                        id={`instructions-${i}`}
                        className="input"
                        {...form.register(`items.${i}.instructions`)}
                      />
                    </div>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => append(blank)}
                  disabled={fields.length >= 30}
                >
                  <Plus />
                  {t("addMedicine")}
                </Button>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    required
                    {...form.register("confirmed")}
                  />
                  <span>{t("rxConsent")}</span>
                </label>
                {form.formState.errors.confirmed && (
                  <ErrorNotice message="Please confirm the details before saving." />
                )}
                <Button
                  type="submit"
                  disabled={
                    form.formState.isSubmitting || data.status !== "completed"
                  }
                >
                  <Check />
                  {t("confirm")}
                </Button>
                {saved && (
                  <div role="status" className="notice">
                    <Check />
                    <span>{t("saved")}</span>
                  </div>
                )}
              </form>
            </Card>
          </div>
          {(saved || data.confirmed_at) && (
            <Card>
              <h3>Continue with your confirmed details</h3>
              <div className="row wrap" style={{ marginTop: 16 }}>
                {form.getValues("items").map(
                  (item, i) =>
                    item.name && (
                      <Button key={i} asChild variant="outline">
                        <Link
                          href={`/medicines?q=${encodeURIComponent(item.name)}`}
                        >
                          <Search />
                          {item.name}
                        </Link>
                      </Button>
                    ),
                )}
                <Button asChild>
                  <Link href="/pharmacies">
                    <MapPin />
                    {t("pharmacies")}
                  </Link>
                </Button>
              </div>
            </Card>
          )}
        </div>
      )}
    </>
  );
}
