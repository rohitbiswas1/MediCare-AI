"use client";
import Link from "next/link";
import { HeartPulse, MessageCircle, ArrowRight } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import { PageTitle } from "@/components/common";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
export default function Page() {
  const { t } = useLocale();
  const questions = [
    [
      "Is this a medical diagnosis?",
      "No. MediCare AI extracts supported values from documents and offers informational explanations. A qualified clinician must interpret results in the context of your symptoms, history, and examination.",
    ],
    [
      "Which documents can I upload?",
      "PDF, PNG, JPG, and supported single-frame CR/DX DICOM containers up to 15 MB. PDFs are limited to 20 pages. English OCR is currently enabled. Handwriting, Hindi/Bengali OCR, compressed DICOM pixels, and complex layouts may require manual review.",
    ],
    [
      "What if a prescription is unclear?",
      "Do not guess a medicine name, dose, or frequency. Ask the prescribing clinician or pharmacist. The confirmation form lets you record only details you have verified.",
    ],
    [
      "Does a map result mean my medicine is in stock?",
      "No. Google Maps discovers businesses. Only a current pharmacy-partner inventory record can confirm medicine stock. Contact the pharmacy before travelling.",
    ],
    [
      "How do I delete a report or my account?",
      "Open a report and choose the delete icon. To delete your account and its associated records, go to Privacy & consent. Deletion is permanent in the active application; backup retention is governed by the deployment operator.",
    ],
    [
      "Are ECG and chest X-ray models clinically validated?",
      "No model weights or external clinical validation are bundled. Specialized inference remains unavailable. The separate research training pipelines must not be used for patient care.",
    ],
    [
      "How do I get support?",
      "This development release has no staffed support service. File a software issue in the repository without attaching medical records, names, identifying screenshots, passwords, or keys. For care decisions, contact a qualified healthcare professional.",
    ],
  ];
  return (
    <>
      <PageTitle title={t("supportTitle")} subtitle={t("supportBody")} />
      <div className="stack narrow">
        <div className="notice warning">
          <HeartPulse />
          <span>{t("emergency")}</span>
        </div>
        <Card>
          <h2>Common questions</h2>
          {questions.map(([q, a]) => (
            <details className="faq" key={q}>
              <summary>{q}</summary>
              <p>{a}</p>
            </details>
          ))}
        </Card>
        <Card>
          <div className="row">
            <MessageCircle color="#2563eb" />
            <h3>Bring good questions to your clinician</h3>
          </div>
          <p className="muted" style={{ fontSize: 12, margin: "15px 0" }}>
            What does this measurement mean in my context? Does it need to be
            repeated? What symptoms should prompt urgent help?
          </p>
          <Button asChild variant="outline">
            <Link href="/reports">
              {t("reports")}
              <ArrowRight />
            </Link>
          </Button>
        </Card>
      </div>
    </>
  );
}
