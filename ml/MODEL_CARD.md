# Model release evidence template

No released clinical model is included. Complete this record separately for each candidate artifact.

- Intended use, non-use, target population, modality, supported devices/views/leads/sampling rates, acquisition exclusions.
- Architecture, exact code commit, dependencies, hardware/seed, artifact SHA-256, training run ID, preprocessing and label definitions.
- Dataset sources, release versions, access/license authority, consent/data provenance, patient linkage and split manifests; leakage/deduplication evidence.
- Training/validation/test and independent external cohorts; patient counts, disease prevalence, age/sex and other relevant subgroups, site/device coverage.
- Sensitivity, specificity, AUROC, confidence intervals, calibration/ECE/Brier scores, operating thresholds chosen before test evaluation, missing-label strategy, and subgroup uncertainty.
- Clinical error review: false positives/negatives, quality failures, out-of-distribution behavior, abstention, workflow and human-factors assessment.
- Limitations, known biases, contraindications, no-finding wording, clinician review and emergency guidance.
- Security/privacy evaluation, artifact integrity, access restrictions, model drift monitoring, rollback, incident plan, retention, and version audit trail.
- Clinical and regulatory review evidence, accountable reviewers and dates, approved deployment scope, release authorization and follow-up obligations.

A `status` field or a passing unit test is not clinical approval. Do not use arbitrary confidence percentages or claim normality solely because no supported finding is identified.
