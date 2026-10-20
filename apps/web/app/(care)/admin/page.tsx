"use client";
import { useEffect, useState } from "react";
import { useUser } from "@/components/shell";
import { api } from "@/lib/api";
import { PageTitle, ErrorNotice } from "@/components/common";
import { Card } from "@/components/ui/card";
export default function Page() {
  const { user } = useUser();
  const [metrics, setMetrics] = useState<Record<string, number | string>>({});
  const [models, setModels] = useState<
    { id: string; name: string; version: string; status: string }[]
  >([]);
  const [error, setError] = useState("");
  useEffect(() => {
    if (user.role !== "admin") return;
    Promise.all([
      api<Record<string, number | string>>("/admin/metrics"),
      api<typeof models>("/admin/model-versions"),
    ])
      .then(([m, v]) => {
        setMetrics(m);
        setModels(v);
      })
      .catch((e) => setError(e.message));
  }, [user.role]);
  if (user.role !== "admin")
    return (
      <ErrorNotice message="Administrator access is required. Your account has no administrative permissions." />
    );
  return (
    <>
      <PageTitle
        title="Administration"
        subtitle="Operational counts and model deployment status. No patient documents are shown here."
      />
      <ErrorNotice message={error} />
      <div className="three-grid">
        {Object.entries(metrics).map(([k, v]) => (
          <Card key={k}>
            <p className="muted">{k.replaceAll("_", " ")}</p>
            <div className="stat-number">{v}</div>
          </Card>
        ))}
      </div>
      <Card style={{ marginTop: 24 }}>
        <h2>Model registry</h2>
        {models.length ? (
          models.map((m) => (
            <div className="settings-row" key={m.id}>
              <span>
                {m.name} · {m.version}
              </span>
              <span className="badge amber">{m.status}</span>
            </div>
          ))
        ) : (
          <p className="muted" style={{ marginTop: 15 }}>
            No validated model artifacts registered. Diagnostic capabilities
            remain unavailable.
          </p>
        )}
      </Card>
    </>
  );
}
