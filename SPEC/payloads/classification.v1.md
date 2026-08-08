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

- **`line_source`** classifies the *kind* of market the row was priced against, from a
  closed vocabulary: `"single_book"` (one book's posted price), `"consensus"` (an
  aggregate across books), or `"exchange"` (a peer-to-peer venue). It is deliberately a
  market type and not a vendor name. What a reader needs in order to interpret the entry
  price — and to compute closing-line value against a market of their own choosing — is
  whether that price was one book's or an average; which supplier provided it is not
  part of the claim, and naming it would publish a data source. Which data sources feed
  *training* is likewise not part of any ledger row — the ledger records predictions,
  not lineage.
- **Computing closing-line value from a row.** The fields above commit the complete
  entry — side (`prediction`), line (`home_line` / `away_line`), price
  (`home_juice` / `away_juice`, or `home_line` / `away_line` themselves for moneyline
  markets, where the line *is* the price), the market type (`line_source`), and the
  event (`game_time`, `home_team`, `away_team`) — as of the row's `recorded_at`, before
  the event began. Nothing about the closing market is recorded, deliberately: a reader
  supplies their own closing odds, from whatever feed they trade on, and computes CLV
  themselves. The ledger's role is to make the entry unforgeable and prior; the
  comparison is the reader's. A CLV figure derived this way depends on no number
  published by the operator.
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
