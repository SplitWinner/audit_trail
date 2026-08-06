# payload_schema: `classification.v1`

Registered 2026-08-06. The founding payload type: a classification pick (game winner /
favorite-underdog style markets) with conformal set disclosure.

A row declaring `"payload_schema": "classification.v1"` hashes exactly these fields, in
canonical serialization ([`../canonicalization.md`](../canonicalization.md)), plus the
`payload_schema` declaration itself:

```
sport · category · dataset · model_id · prediction_type · prediction_mode · season ·
date_event · game_time · home_team · away_team · home_team_rotation ·
away_team_rotation · home_line · away_line · home_juice · away_juice · prediction ·
confidence · bet_type · conformal_set_size · conformal_set ·
conformal_coverage_target · intelligence_category · probability · edge ·
expected_value · kelly_criterion · kelly_amount · sharp_money · line_source
```

Notes:

- **`line_source`** names the book or feed the row was priced against (`"consensus"`,
  or a specific book identifier). It binds a prediction to the exact market it called.
  Which data sources feed *training* is not part of any ledger row — the ledger records
  predictions, not lineage.
- Measurement fields (`home_line`, `away_line`, `home_juice`, `away_juice`,
  `confidence`, `probability`, `edge`, `expected_value`, `kelly_criterion`,
  `kelly_amount`, `conformal_coverage_target`) are fixed-precision decimal strings per
  the canonicalization rules. `conformal_set_size` is a JSON integer;
  `conformal_set` is a JSON array of team strings.
- Fields absent from a row serialize as `null` — absence is representable and hashed.
- Golden vector: [`../vectors/row_classification_v1.json`](../vectors/row_classification_v1.json).

Future prediction types (margin of victory, totals, spreads, per-book variants)
register sibling files — `mov.v1`, `totals.v1`, … — with their own field lists and
vectors. Registering a new payload schema never modifies this one.
