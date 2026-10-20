import Link from "next/link";
import { Brand } from "@/components/common";
export default function Page() {
  return (
    <main className="main-content narrow">
      <Brand />
      <article className="card stack" style={{ marginTop: 30 }}>
        <h1>Privacy & information use</h1>
        <p>Policy version 2026-01 · Development release</p>
        <h2>Your records, your choice</h2>
        <p>
          MediCare AI stores your account details and the medical documents you
          explicitly upload. Processing produces text, supported measurements,
          and informational explanations. Uploaded records are never used for
          model training.
        </p>
        <h2>Consent and third parties</h2>
        <p>
          Every upload requires consent. Optional Gemini processing is off by
          default and receives only de-identified comparison categories;
          original files and extracted text are excluded. Pharmacy search sends
          only your search location to Google Maps. You can enter an address
          without sharing device location.
        </p>
        <h2>Storage and deletion</h2>
        <p>
          Development documents are encrypted in local storage. Production
          requires private Supabase storage, secure authentication, antivirus
          scanning, HTTPS, and an encrypted managed database. Documents expire
          after the configured retention period, initially 90 days. You can
          delete an individual report or your account in privacy settings.
          Deployment operators must define backup erasure timelines before
          launch.
        </p>
        <h2>Medical limitations</h2>
        <p>
          OCR can misread text. No diagnostic model is clinically approved in
          this release. This application does not diagnose, prescribe, change
          doses, or replace qualified care. Prescriptions require human
          confirmation.
        </p>
        <h2>Before real-patient use</h2>
        <p>
          This is a development application. The deployment operator must supply
          a privacy contact and grievance process, assess applicable DPDP and
          CDSCO obligations, document data processors and transfer safeguards,
          validate clinical capabilities, and publish the final privacy notice.
          Do not upload real patient information to this development workspace.
        </p>
        <Link className="source-link" href="/register">
          Back to registration →
        </Link>
      </article>
    </main>
  );
}
