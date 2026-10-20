# Security, privacy, and medical safety

This repository provides controls and operating guidance, not a certification of compliance. Development mode is restricted to synthetic data. The public privacy page is a development notice that must be replaced with the deploying operator's final notice and contact details.

## Implemented controls

Explicit registration/upload/third-party consent; private document access; encrypted local blobs; mandatory private Supabase storage in production; UUID ownership checks; PostgreSQL row policies and revoked browser grants; Argon2id development passwords; HttpOnly sessions, Secure production cookies, CSRF, origin validation, and logout revocation; Redis rate limits; bounded upload types/sizes/pages/pixels; no active/attached PDF content; optional development/required production ClamAV; sanitized error responses; audit/access events; report/account deletion; hourly document retention; no training on uploaded records.

Production startup rejects local auth/storage, missing credentials/scanner, non-HTTPS origins/Supabase, weak session secrets, non-verifying PostgreSQL TLS, non-TLS Redis, a public document bucket, and a superuser/RLS-bypass API database role. Never supply the API's runtime role with migration or retention privileges just to make these checks pass.

The clinical application returns only literal measurements and bounded informational comparisons. It keeps OCR source lines and explicitly reports unsupported or uncertain data. Gemini cannot add clinical text. A paper ECG is not accepted by the research waveform endpoint. Unvalidated artifacts cannot enter production. A model without a positive finding does not establish normality. Prescription confirmation is not prescribing permission. Catalog and stock claims require traceable evidence.

## Threat and operational boundaries

- Authenticate and authorize every identifier lookup, download, signed URL, mutation, and admin route. Client-side route visibility is not authorization.
- Do not expose Supabase service-role or inference-service credentials to browsers. Do not log cookies, keys, request bodies, medical text, coordinates, or temporary download URLs.
- Encrypt production database disks, object storage, backups, and transport. Restrict support/admin access; use just-in-time audited access for any patient inspection outside this interface.
- Test scanner signatures and failures. Restrict worker CPU/memory and outbound network; do not use OCR subprocesses as a sandbox for arbitrary executables.
- The source-grounded parser handles only a documented small set of measurements. It is not a general clinical document interpreter. Reference intervals and translations require expert review.
- The local session secret and encryption key live under ignored `.local/` with restricted permissions. Cloud snapshots containing them must remain private. No real patient documents should enter this snapshot.
- Define retention for user profiles, consent records, audit logs, provider caches, and backups, in addition to the implemented report expiry. Set up a dedicated restricted retention queue/identity before production.
- Production needs actual penetration testing, threat modeling, provider-account verification, dependency review, monitoring, recovery tests, and operational ownership. An automated passing suite does not establish these.

## India launch review

Document applicable DPDP roles, purpose and consent notices in understandable languages, data minimization, withdrawal/access/correction/erasure procedures, grievance contact and response process, processor/subprocessor arrangements, cross-border transfers and residency, children's-data handling, security safeguards, and breach obligations. Obtain qualified legal and clinical advice for the actual intended use. Assess applicable CDSCO obligations before any diagnostic claims or clinical model enablement. No legal or regulatory approval is claimed here.

## Incident response runbook

1. Triage the alert using request IDs and aggregate logs without copying medical content into tickets.
2. Contain affected ingress, workers, accounts, or provider keys. Preserve minimal encrypted evidence with authorized access and retention.
3. Revoke sessions and rotate credentials through the secret manager. Keep unaffected care access available where feasible.
4. Establish affected data, identities, time window, and processors; notify the responsible operator and designated security/privacy contact.
5. Have the operator assess applicable regulator/user/contractual notifications and deadlines with qualified advisers. Do not assume a generic deadline fits every incident.
6. Remediate, verify the fix and restored access boundaries, test backups, and document a review and prevention actions. Delete investigation copies according to the approved schedule.

No staffed support/security address is invented in this repository. The deployment operator must supply and test these channels before launch.
