import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
export const metadata: Metadata = {
  title: {
    default: "MediCare AI — Understand Your Health",
    template: "%s | MediCare AI",
  },
  description:
    "A private space to understand your medical reports, review prescriptions, and find care in India.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        {process.env.NEXT_PUBLIC_DEMO_MODE === "true" && (
          <aside className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm text-amber-950">
            Interactive demo · Use synthetic documents only.{" "}
            <a className="underline" href="/demo/sample-report.pdf" download>
              Download sample report
            </a>{" "}
            ·{" "}
            <a className="underline" href="/demo/sample-prescription.png" download>
              Download sample prescription
            </a>
          </aside>
        )}
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
