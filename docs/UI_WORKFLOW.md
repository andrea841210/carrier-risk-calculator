# v0.3 UI workflow

## Purpose

The public interface is a focused carrier-risk calculator, not a panel-review
dashboard. A customer starts with one searchable gene field and sees only the
next inputs or explanation needed for that gene.

The curated special-case boundary remains unchanged. Standard AR/XL records
open the calculator even if their dataset route is still `HOLD`; eligibility is
then evaluated from the inputs required by the customer's selected scenario.

## Single-gene flow

1. Search by gene symbol or disease name.
2. Confirm the selected gene, disease, and inheritance mode.
3. Send `DEAD_PAGE` records to the dedicated method page.
4. For a standard AR/XL record, let the person and partner independently choose
   population and test status, then calculate only if that scenario has every
   required numeric input.
5. For any other incomplete model, render a concise hold explanation.

Records sharing a non-empty `display_group_id` appear as one customer-facing
choice. This prevents duplicate alpha-thalassemia entries; it does not combine
or add their risks.

## Route behavior

| Route | Customer-facing behavior |
|---|---|
| `CALCULATE` | Show independent population and test-status choices for both partners, then update the applicable AR or XL result. |
| `HOLD` + standard AR/XL | Open the same customer calculator. `Detected` and `untested` can calculate from the master data; `not detected` requires a validated numeric detection rate. |
| `HOLD` + incomplete/non-standard model | State that a reliable number is not yet available. Keep background carrier rates in collapsed details. |
| `DEAD_PAGE` | State that a dedicated method is required, show the recommended method, and keep display-only carrier rates in collapsed details. Never return a standard AR or XL risk. |

The UI does not expose governance fields, dataset totals, manual carrier-rate
editing, or a formula sandbox.

## Calculation inputs

### Individual carrier risk

Each person independently chooses a population and one of three states:

- detected: `CR = 1`;
- not detected: `CR = CF × (1 − DR) / (1 − CF × DR)`;
- untested: `CR = CF`.

The not-detected state is calculated only when a numeric, assay-matched
detection rate has been validated. The residual-risk factor `(1 − DR)` is used
once within individual carrier risk and is not multiplied again in reproductive
risk.

### Autosomal recessive

The UI shows both partners' population and test status and returns:

```text
RR_AR = CR_mother × CR_father × 1/4
```

### X-linked

The UI asks for maternal status and one fetal scenario:

- known male fetus: affected risk;
- unknown fetal sex: affected-male-pregnancy risk;
- known female fetus: probability of inheriting the maternal variant.

The known-female result is not labeled as affected risk or universally “very
low.” Disease-specific female affected risk remains unavailable unless the
required paternal confirmation and penetrance are supplied by an approved data
workflow.

## Special-gene boundary

`AFF2`, `FMR1`, `FXN`, `SMN1`, `HBA1/HBA2`, and `MT-RNR1` remain fixed
no-calculation routes. `CYP21A2`, `DMD`, `F8`, and `GBA1` remain assay-dependent
special routes. Existing carrier rates may be displayed as context but are not
reused as WES residual-risk inputs.

SMA and fragile-X testing remain distinct standard assays; the WES-based
calculator does not replace them.

## Presentation

The interface renders percentage and `1 / N` views after calculation while the
engine retains full precision. Bounds such as `<1 / 50,000` remain bounds and
are not converted to exact values.
