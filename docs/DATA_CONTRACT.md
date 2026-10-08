# Data contract

Data package version: 0.1.0

## Curated datasets

### `panel_review.csv`

One row represents one gene–disease–OMIM panel record. `panel_row_id` is the stable key.

Fields that control runtime behavior:

| Field | Purpose |
|---|---|
| `model_type` | Selects the standard AR, standard XL, or special model family |
| `calculator_route` | Manual release gate: `CALCULATE`, `HOLD`, or `DEAD_PAGE` |
| `special_case_type` | Distinguishes fixed no-calculation records from assay-dependent holds |
| `carrier_rate_usage` | Limits frequency use to risk input, pending validation, or display only |
| `assay_dr_status` | Records whether an applicable assay-specific DR is validated |
| `display_group_id` | Collapses records that should share one front-end display group |
| `recommended_method` | Method guidance displayed on a dead page |

### `gene_registry.csv`

One row represents one panel gene string and its HGNC mapping. This table establishes gene identity only; it does not by itself validate disease or frequency applicability.

### `carrier_frequency.csv`

One row represents one source-specific population estimate or bound. Populations and sources remain separate. `frequency_id` is the stable key.

`frequency` is the numerical probability or numerical limit represented by the source row. `relation` preserves exact versus bounded values such as `=` or `<`.

### `special_cases.csv`

A filtered application-facing view of all `DEAD_PAGE` panel records. Available carrier-frequency context may be displayed, but it is not used in the standard risk equations.

### `source_registry.csv`

Source roles, versions, links, and verification notes.

### `review_issues.csv`

Open and resolved curation issues retained for traceability. This is a governance table and does not drive calculations.

## Raw snapshots

Files under `data/raw/` preserve the four source worksheets used to construct the curated layer. They are not application inputs.

## Required invariants

- `panel_row_id` and `frequency_id` are unique and non-empty.
- Every panel record has a valid `model_type` and `calculator_route`.
- All special models route to `DEAD_PAGE`.
- Every `DEAD_PAGE` record uses carrier frequency for `DISPLAY_ONLY`.
- A `CALCULATE` record must use `RISK_INPUT`, have `VALIDATED` assay DR status, and use a standard model.
- Records sharing `display_group_id` are rendered as one display group without summing duplicate risks.
- Dataset hashes and expected record counts match `data/manifest.json`.

