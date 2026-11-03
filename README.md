# TeoBench

**English** · [Русский](README.ru.md)

An open benchmark for evaluating model reasoning and collecting reproducible community studies.

The first tier, **[Easy-Bench](Easy-Bench/README.md)**, contains 30 tasks from a completed reasoning-effort study. Prompts, inputs and reference answers are preserved unchanged. This is a small synthetic baseline; more demanding real-world scenarios have not been added yet.

| Category | Tasks | What it tests |
|---|---:|---|
| Reasoning | 6 | Rounding, intervals, optimization and counting |
| Python | 6 | A `solve(data)` function, checked against 300 test cases |
| SQL | 6 | SELECT queries across 72 SQLite databases |
| Data | 6 | Filters, revisions, duplicates and untrusted text |
| Tools | 6 | Sequences of actual `lookup` calls |

## Quick start

Python 3.9+ and the standard library are sufficient for the inspection and grading CLI; no packages or API keys are required. Grading Python answers requires **macOS with `/usr/bin/sandbox-exec`** and a Python interpreter installed outside `/Users` and `/Volumes`. On other operating systems, the Python grader refuses to execute code without isolation.

```bash
git clone https://github.com/teo-nex/TeoBench.git
cd TeoBench
python3 -m teobench verify
python3 -m teobench list
python3 -m teobench show R01
python3 -m unittest discover -s tests -v
```

Grade an individual answer:

```bash
python3 -m teobench grade R01 --answer answer.txt
```

Run all commands from the repository root. The grader does not call models. Use your own model or agent to complete the tasks, giving the evaluated model only the output of `show` and the permitted `lookup` tool, without access to reference answers.

## Contribute a study

1. Create a report with the exact model ID, reasoning effort and run conditions.
2. Record every answer, including failures. A complete run contains all 30 tasks for one model, effort setting and replicate number.
3. Validate the report and review the data that will become public.
4. Confirm submission: the CLI creates a pull request; it does not merge it automatically.

```bash
python3 -m teobench study create --id my-first-study --file local-runs/study.json \
  --access-route 'provider/model endpoint, no credentials' \
  --environment 'macOS arm64; Python 3.12; no extra tools'

python3 -m teobench study record --file local-runs/study.json \
  --task R01 --model exact-model-id --effort high --answer answer.txt

# Repeat record for the remaining tasks; retain failures and repeated attempts too.
python3 -m teobench study validate --file local-runs/study.json
python3 -m teobench study submit --file local-runs/study.json

# After reviewing the report and consenting to public submission:
python3 -m teobench study submit --file local-runs/study.json --publish
```

Submission requires an authenticated [GitHub CLI](https://cli.github.com/). Without `--publish`, the command only displays a local preview and does not contact GitHub. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [protocol](docs/PROTOCOL.md) for details.

## Studies and statistics

- [Accepted reports](Easy-Bench/studies): answers, scores and run conditions in a shared JSON format.
- [Aggregate statistics](Easy-Bench/statistics/summary.json): rebuilt after reports are accepted, with separate groups for each model, effort setting, access route, environment and grader version.
- [First study, November 3, 2026](Easy-Bench/research-2026-11-03/README.md): 7 models × 30 tasks × 5 effort settings = 1,050 primary answers; **991/1,050** passed after the grader correction.

GitHub validates report structure and regrades answers using trusted base-branch code. Only complete runs enter the aggregate statistics; exact duplicate response sets are excluded. Server-side model identity, tool-history authenticity and lack of access to reference answers remain claims made by the study author. These reports are neither independent provider attestations nor a representative sample of all users.

Reference answers are public for reproducibility, so Easy-Bench is no longer a hidden holdout. The original internal `easy/medium/hard` labels are retained, but the entire original set belongs to the TeoBench **Easy** tier. See [provenance and checksums](Easy-Bench/tasks/PROVENANCE.json). Licensed under [MIT](LICENSE).
