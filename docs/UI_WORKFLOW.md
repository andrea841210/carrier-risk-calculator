# v0.2 UI workflow

## Purpose

The interface separates two activities that must not be conflated:

- reviewing whether a panel record is eligible for calculation;
- exercising the approved formulas with explicit scenario inputs.

Manual inputs in the formula sandbox are transient. They do not update the curated CSV files or change a record's release gate.

## Panel routing

The panel explorer searches `gene`, `omim_id`, Chinese and English disease names, and the Chinese category. The selected record is evaluated through the same routing function used by the core package.

| Route | UI contract |
|---|---|
| `CALCULATE` | Confirm that the data-layer gates are satisfied and allow a complete scenario to calculate |
| `HOLD` | List unresolved carrier-rate, assay-DR, or manual-release gates; evidence remains viewable |
| `DEAD_PAGE` | Show frequency context, limitation rationale, and the recommended method; never return a standard numerical risk |

Records sharing a non-empty `display_group_id` can share display-only frequency context. They do not sum or merge reproductive risks. This currently supports the alpha-thalassemia display group.

## Formula sandbox

### Individual carrier risk

Each person has three possible states:

- detected: `CR = 1`;
- not detected: `CR = CF × (1 − DR) / (1 − CF × DR)`;
- untested: `CR = CF`.

The residual-risk factor `(1 − DR)` is applied within individual carrier risk and is not multiplied again in reproductive risk.

### AR outputs

The interface returns maternal carrier risk, paternal carrier risk, and:

```text
RR_AR = CR_mother × CR_father × 1/4
```

### X-linked outputs

The user chooses one explicit output:

- known male fetal affected risk;
- affected-male-pregnancy risk when fetal sex is unknown;
- known female inheritance probability;
- known female affected risk when paternal confirmation and a disease-specific female penetrance are supplied.

Known female fetuses are not assigned a universal "very low" label.

## Presentation

Calculations retain full floating-point precision. The interface renders percentage, decimal, and `1 in N` views after calculation. Evidence-table bounds such as `<1 in 50,000` remain bounds and are not silently converted to exact values.
