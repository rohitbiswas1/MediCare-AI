"use client";
import { Info } from "lucide-react";
import { PageTitle } from "./common";
import { UploadForm } from "./upload-form";
import { useLocale } from "@/lib/i18n";
export function Specialized({ kind }: { kind: "ecg" | "xray" | "heart_rate" }) {
  const { t } = useLocale();
  return (
    <>
      <PageTitle
        title={t(kind === "heart_rate" ? "heart" : kind)}
        subtitle={t("reportToolSub")}
      />
      {kind !== "heart_rate" && (
        <div className="notice warning" style={{ marginBottom: 24 }}>
          <Info />
          <div>
            <strong>{t("unavailable")}</strong>
            <p>{t("unavailableBody")}</p>
            {kind === "ecg" && (
              <p>
                Paper ECG photographs are not raw waveforms. Research waveform
                formats are handled by the separate ML pipeline.
              </p>
            )}
          </div>
        </div>
      )}
      <UploadForm kind={kind} />
    </>
  );
}
