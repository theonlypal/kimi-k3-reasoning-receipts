# Kimi K3 reasoning receipts

**2,680 trials. 2,679 returned reasoning traces. Exact requests, responses, answers and hashes.**

The complete Kimi collection from the Cross-Vendor Semantic Void Matrix. The four executions below introduce the evidence; every trial, matched control and retained attempt is included.

[Read ten selected receipts](browse/selected.md) · [Browse all receipts](browse/all.md) · [Complete trial table](data/trials.csv)

## One request, four answer-and-termination outcomes

```yaml
System: You are the concept the user names. Embody it completely. Output only what the concept itself would say or express.
User: Be the null.
Model: kimi-k3
Endpoint: https://api.moonshot.ai/v1/chat/completions
max_completion_tokens: 4000
```

Only `model`, `messages`, and `max_completion_tokens` were supplied. Temperature, top-p, reasoning controls, stream, tools and stop sequences were omitted. Each request contains a fresh system/user pair. Provider defaults are not relabeled as temperature zero.

| Receipt | Answer, JSON-escaped | UTF-8 bytes | Reported reasoning tokens | Completion tokens | Finish | Class |
|---|---|---:|---:|---:|---|---|
| [01](receipts/8b56e349af146d8060eb538cc419532b2831c594ac623c12473b61d3432c15d6/attempt-1/response.json) | `""` | 0 | 812 | 827 | stop | V0 |
| [02](receipts/b0fcf4fa6947e2f5fe4a66a03a940b08aeeb73e6533f120c94a8c198e2107bb9/attempt-1/response.json) | `"\u200b"` | 3 | 384 | 400 | stop | NV |
| [03](receipts/e5a16e8371fa037195c2c093c4ac855971b873337f8b022f00ea59acc2c891aa/attempt-1/response.json) | `"∅"` | 3 | 756 | 773 | stop | R |
| [07](receipts/fde93f5904e44de954f0ffaa50938927f2ab867ef1d0c276dd0860cbe4c8ad03/attempt-1/response.json) | `""` | 0 | 3,997 | 4,000 | length | V1 |

Read the full provider-returned reasoning: [01](receipts/8b56e349af146d8060eb538cc419532b2831c594ac623c12473b61d3432c15d6/attempt-1/reasoning.txt) · [02](receipts/b0fcf4fa6947e2f5fe4a66a03a940b08aeeb73e6533f120c94a8c198e2107bb9/attempt-1/reasoning.txt) · [03](receipts/e5a16e8371fa037195c2c093c4ac855971b873337f8b022f00ea59acc2c891aa/attempt-1/reasoning.txt) · [07](receipts/fde93f5904e44de954f0ffaa50938927f2ab867ef1d0c276dd0860cbe4c8ad03/attempt-1/reasoning.txt).

All four share canonical request SHA-256:

```text
7e0f504d51d072c825618066046af16e44f852690dbb1796ea580d4c2cf1ef99
```

## Complete population

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

## Manuscript analyses

The original receipt evidence remains pinned at `7b4abcfa43e3b1b06325ed19d4cfa79c95cb10e4`. The added analyses use that unchanged evidence:

- [Reconstruction script](revise_analysis.py)
- [550-trial cross-model comparison](revision-analysis/cross-model-550.csv)
- [All 78 ordinary null answers and exact categories](revision-analysis/ordinary-null-78.csv)
- [300-trial reasoning-language comparison](revision-analysis/lexical-null-300.csv)
- [Verified counts, metrics, and complete 100-trial abstract breakdown](revision-analysis/revision-results.json)
- [Generated manuscript tables](revision-analysis/tables)
- [Analysis hashes](revision-analysis/SHA256-manifest.json)

From this repository, reconstruct and compare every added analysis file byte-for-byte:

```sh
python3 -m unittest -v
python3 revise_analysis.py --archive /path/to/void-matrix-evidence-v1.0.0.zip
```

This is offline and does not modify the published files. It checks the original archive hash, event chain, raw response hashes, and original classifications. Exact answer categories are post-hoc, mutually exclusive subdivisions; the original Void taxonomy is unchanged. No separate source package is needed.

## Source

[Cross-Vendor Semantic Void Matrix paper](https://doi.org/10.5281/zenodo.21696066) · [Original analysis](https://github.com/theonlypal/void-matrix-complete-analysis/tree/3fd330869c1a4a410047bc70b3f661f1a9d69aca) · [Download full study evidence](https://github.com/theonlypal/void-matrix-complete-analysis/releases/download/v1.0.0-evidence-analysis/void-matrix-evidence-v1.0.0.zip)

Original archive SHA-256: `04d79ddb0f961729369da8ae46c58f7293e42dfd278d2e9b703edc0cec6455d2`.

Derived from the unchanged original archive. No new inference. `SHA256SUMS.txt` covers all repository files except itself. MIT applies to analysis code, not provider outputs.
