# Formula specification

Baseline date: 2026-09-29

## Inputs

### Carrier frequency

For a source expressed as `1 in N`:

```text
CF = 1 / N
```

The selected frequency must match the population, sex, and gene–disease definition used by the calculation.

### Detection rate

```text
0 ≤ DR ≤ 1
```

The detection rate must apply to the same gene–disease–variant-class definition and the assay being modeled. A rate from another platform or laboratory is not substituted automatically.

## Individual carrier risk

### Confirmed pathogenic or likely pathogenic result

```text
CR = 1
```

VUS results do not enter this state.

### Tested and not detected

```text
CR = CF × (1 − DR) / (1 − CF × DR)
```

This is the post-test residual carrier risk under the specified assumptions. A validated assay-specific DR is required.

### Untested

```text
CR = CF
```

## Autosomal recessive reproductive risk

For the same autosomal recessive disease under the standard Mendelian, fully penetrant model:

```text
RR_AR = CR_mother × CR_father × 1/4
```

Useful boundary cases:

```text
one confirmed carrier: RR_AR = CR_other × 1/4
two confirmed carriers: RR_AR = 1/4
```

The residual-risk factor `(1 − DR)` is already included in the individual CR. It must not be multiplied again in the reproductive-risk formula.

## X-linked reproductive risk

Only maternal carrier risk enters the following baseline equations.

### Known male fetus

```text
RR_male = CR_mother × 1/2
```

This assumes complete male penetrance for the modeled condition.

### Fetal sex unknown

Risk of an affected male pregnancy:

```text
RR_unknown = CR_mother × 1/2 × 1/2 = CR_mother / 4
```

The first `1/2` is maternal transmission and the second is the probability of a male fetus.

### Known female fetus

Probability of inheriting the maternal variant:

```text
P_female,inherit = CR_mother × 1/2
```

This is an inheritance or carrier-risk output. It must not be labeled as a universal female affected risk.

Female affected risk may be calculated only when the father is confirmed not to carry the modeled variant and a reliable disease-specific female penetrance is available:

```text
RR_female = CR_mother × 1/2 × Pen_female
```

Otherwise, female affected risk is unavailable rather than “very low.”

## Calculation gates

No numerical carrier or reproductive risk is returned when:

- the record is routed to `DEAD_PAGE`;
- the record has not been promoted to `CALCULATE`;
- the selected carrier frequency is not approved for risk input;
- an assay-specific DR is required but not validated;
- scenario inputs are incomplete;
- a known female fetus lacks the inputs required for the requested output.

All intermediate calculations retain full precision. Rounding is applied only in the presentation layer.

