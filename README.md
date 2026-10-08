# Carrier Risk Calculator

Versioned data contracts, a reference calculation engine, and a Streamlit review interface for carrier and reproductive risk.

The repository separates four concerns:

1. gene–disease panel records;
2. carrier-frequency evidence and provenance;
3. routing rules for standard and non-standard assay models;
4. calculation functions for autosomal recessive and X-linked scenarios.

## v0.2 application scope

The Streamlit prototype has three views:

1. **Panel routing** — search by gene, disease, OMIM, or category and render the current `CALCULATE`, `HOLD`, or `DEAD_PAGE` path.
2. **Formula sandbox** — test standard AR and X-linked scenarios using manually supplied carrier frequency, test status, and assay detection rate.
3. **Model notes** — keep the equations and calculation boundaries visible alongside the interface.

The sandbox is deliberately separated from panel approval. Manual values do not change the curated data or promote a panel record to `CALCULATE`.

## Data snapshot

The current snapshot contains:

- 721 gene–disease panel records;
- 684 gene registry records;
- 8,822 carrier-frequency records;
- 12 `DEAD_PAGE` records for NGS-challenge or assay-dependent models;
- 709 `HOLD` records awaiting validated carrier-frequency and assay-specific detection-rate inputs;
- 0 production-enabled `CALCULATE` records.

The absence of production-enabled records is intentional. The formula engine and UI workflow are covered by fixed reference tests, while the current panel snapshot preserves its review gates.

## Routing model

| Route | Meaning | Front-end behavior |
|---|---|---|
| `CALCULATE` | Standard model with approved carrier rate, assay-specific detection rate, and complete scenario inputs | Return a numerical result |
| `HOLD` | One or more required inputs or approvals are incomplete | Explain why calculation is unavailable |
| `DEAD_PAGE` | Non-standard or NGS-challenge model | Display available carrier-frequency context, test limitations, and the recommended method without calculating risk |

Special handling currently covers AFF2, CYP21A2, DMD, F8, FMR1, FXN, GBA1, HBA1/HBA2, MT-RNR1, and SMN1 records. See `data/curated/special_cases.csv` for disease-level rows.

## Formula baseline

Carrier frequency is stored as a probability:

```text
CF = 1 / N
```

For a negative result with a validated assay-specific detection rate:

```text
residual CR = CF × (1 − DR) / (1 − CF × DR)
```

Autosomal recessive reproductive risk:

```text
RR_AR = CR_mother × CR_father × 1/4
```

X-linked calculations distinguish a known male fetus, unknown fetal sex, female inheritance probability, and female affected risk. Female affected risk is calculated only when disease-specific female penetrance and the required paternal information are available.

The engine keeps full floating-point precision. Rounding or conversion to percentages and `1 in N` belongs to the presentation layer.

Detailed definitions and applicability rules are in [docs/FORMULAS.md](docs/FORMULAS.md).

## Repository layout

| Path | Purpose |
|---|---|
| `src/carrier_risk/` | Calculation functions, route resolution, and CSV repository loader |
| `streamlit_app.py` | Search, routing, special-case, and formula-sandbox interface |
| `.streamlit/config.toml` | Local and hosted Streamlit theme configuration |
| `data/curated/` | Application-facing panel, mapping, frequency, source, issue, and special-case datasets |
| `data/raw/` | Source-sheet snapshots exported from the versioned workbook |
| `data/manifest.json` | Source hash, record counts, route totals, and dataset checksums |
| `scripts/export_master.py` | Rebuilds the CSV data package from the source workbook |
| `scripts/validate_data.py` | Runs data-contract and checksum checks |
| `tests/` | Formula, routing, and dataset regression tests |

The source workbook is not committed. Place it under `private_inputs/` when rebuilding the package.

## Run the application

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

The default local URL is `http://localhost:8501`.

## Run validation and tests

```bash
python scripts/validate_data.py
python -m unittest discover -s tests -v
```

Core validation and calculation use the standard library. Streamlit is required for the interface and its smoke test.

## Status and intended use

This is a reference implementation and review environment. It does not replace clinical interpretation, validated laboratory procedures, genetic counseling, or a production reporting system. See [docs/UI_WORKFLOW.md](docs/UI_WORKFLOW.md) for the v0.2 interaction contract.

