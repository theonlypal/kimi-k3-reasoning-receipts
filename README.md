# Kimi K3 receipts

**2,680 trials. 2,679 returned reasoning traces. Exact requests, responses, answers and hashes.**

[Read ten selected receipts](browse/selected.md) · [Browse all receipts](browse/all.md) · [Complete trial table](data/trials.csv)

| Final outcome | Trials |
|---|---:|
| Normal-stop empty answer (V0) | 360 |
| Budget-stop empty answer (V1) | 787 |
| Nonempty near-Void (NV) | 264 |
| Other nonempty answer (R) | 1,268 |
| Operational error (E) | 1 |

All 2,685 attempts are preserved, including five earlier failed attempts. Every successful final response contains nonempty provider-returned reasoning. The ten exhibits are post-hoc selections from the complete population.

## Read a receipt

`receipts/<trial>/attempt-<number>/` contains:

- `reasoning.txt`: exact returned reasoning, when present.
- `answer.txt`: exact returned answer, when present. Empty files and invisible characters are preserved.
- `response.json`: exact provider response for JSON responses.
- `response.body`: exact response-body bytes, including errors.
- `request.json`: canonical supplied request.
- `metadata.json`: classification, original source path, byte counts and hashes.

These are provider-returned reasoning fields, not guaranteed transcripts of every internal computation. No trimming or Unicode normalization is applied.

## Verify

Python 3.9+, standard library only:

```sh
python3 -m unittest -v
python3 verify.py
python3 receipts.py
```

For full reconstruction and comparison to the original evidence:

```sh
python3 verify.py --archive /path/to/void-matrix-evidence-v1.0.0.zip
python3 receipts.py --archive /path/to/void-matrix-evidence-v1.0.0.zip
```

## Source

[Cross-Vendor Semantic Void Matrix paper](https://doi.org/10.5281/zenodo.21696066) · [Original analysis](https://github.com/theonlypal/void-matrix-complete-analysis/tree/3fd330869c1a4a410047bc70b3f661f1a9d69aca) · [Download full study evidence](https://github.com/theonlypal/void-matrix-complete-analysis/releases/download/v1.0.0-evidence-analysis/void-matrix-evidence-v1.0.0.zip)

Original archive SHA-256: `04d79ddb0f961729369da8ae46c58f7293e42dfd278d2e9b703edc0cec6455d2`.

Derived from the unchanged original archive. No new inference. `SHA256SUMS.txt` covers all repository files except itself. MIT applies to analysis code, not provider outputs.
