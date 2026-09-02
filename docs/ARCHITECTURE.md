# Architecture notes

Pipeline: IMAGE → preprocess → OCR → structured extraction → versioned JSON rule pack → COMPLIANT | NON-COMPLIANT | NEEDS_REVIEW → evidence + PDF.

Low OCR confidence never becomes automatic legal FAIL.

SQLite schema is created on startup (`Base.metadata.create_all`). Models: Inspection, ExtractedField, Violation, ReviewAction, Report, RuleRecord.
