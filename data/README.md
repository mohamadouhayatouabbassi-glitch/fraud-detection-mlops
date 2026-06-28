# Data layout

This project does **not** ship the full training dataset. The full dataset
is generated from `fraud_detection.data.synthetic`, deterministic given a
seed, so anyone can reproduce it.

```
data/
+-- sample/       <- 5000-row sample committed to git for quick exploration
|   +-- transactions_train.parquet   (~4000 rows)
|   +-- transactions_test.parquet    (~1000 rows)
+-- processed/    <- generated locally by `make data` (.gitignored, large)
+-- raw/          <- placeholder, here in case a real ingestion pipeline lands later
```

## Sample dataset

The `sample/` parquet files are small (~250 KB total) and committed so the
project works out of the box. They contain ~2% fraud rate and the same five
attack patterns as the full dataset:

* `card_testing`
* `geo_anomaly`
* `cashout`
* `account_takeover`
* `high_risk_mcc`

Use them to:

* run the EDA notebook (`notebooks/01_eda.ipynb`) without generating data first,
* run a smoke training (results will be noisy due to small size, this is a
  reproducibility check, not a benchmark).

## Full dataset

Regenerate the full 200 000-row dataset:

```bash
make data
# or
python -m fraud_detection.cli generate-data --n-rows 200000 --fraud-rate 0.012
```

The generator is deterministic given a seed (default 42) so two runs with
the same arguments produce byte-identical parquet files.

## Schema

See `src/fraud_detection/data/schemas.py` for the canonical column list.
Headline columns:

| Column                          | Type     | Description                                |
|---------------------------------|----------|--------------------------------------------|
| transaction_id                  | string   | Unique transaction identifier              |
| timestamp                       | datetime | UTC timestamp                              |
| customer_id                     | string   | Tokenised customer reference               |
| card_id                         | string   | Tokenised card reference                   |
| amount                          | float    | Transaction amount                         |
| currency                        | string   | ISO 4217 (EUR / USD / GBP / CHF / JPY)     |
| merchant_country                | string   | ISO 3166 alpha-2                           |
| merchant_mcc                    | string   | ISO 18245 4-digit Merchant Category Code   |
| card_country                    | string   | ISO 3166 alpha-2                           |
| channel                         | enum     | POS / ECOM / ATM / MOTO                    |
| is_cnp                          | bool     | Card-Not-Present indicator                 |
| customer_age_days, card_age_days| int      | Account / card tenure                      |
| n_tx_last_1h, n_tx_last_24h     | int      | Velocity features                          |
| amount_avg_30d, amount_std_30d  | float    | Customer baseline                          |
| distinct_countries_last_24h     | int      | Geo velocity                               |
| is_fraud                        | int 0/1  | Ground-truth label                         |
| fraud_pattern                   | string   | Attack pattern (only set for fraud rows)   |
