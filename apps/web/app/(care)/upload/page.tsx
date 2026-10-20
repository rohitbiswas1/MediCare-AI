"use client";
import { UploadForm } from "@/components/upload-form";
import { PageTitle } from "@/components/common";
import { useLocale } from "@/lib/i18n";
export default function Page() {
  const { t } = useLocale();
  return (
    <>
      <PageTitle title={t("upload")} subtitle={t("reportToolSub")} />
      <UploadForm />
    </>
  );
}
