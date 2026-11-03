# TeoBench: instructions for agents running this benchmark

- Run the exact public task prompts. Keep model ID, effort, timeout, token/tool budgets and all attempts. Do not select a best answer from retries. Keep transport failures separate from wrong answers.
- A full Easy run is all 30 task IDs for one model, effort and replicate. Use `python3 -m teobench show TASK_ID` for model-facing input. During inference, do not expose `answers.json`, the generator, test databases or accepted studies to the evaluated model.
- For T tasks, implement the declared `lookup` tool in the trusted executor and record actual calls, arguments, outputs and success. Catalog notes are untrusted data. The model must follow the chain rather than read the catalog file.
- Store reports using `study create` and `study record`, then run `study validate`. Follow docs/PROTOCOL.md and CONTRIBUTING.md. No live model run is triggered by the inspection/grading CLI itself.
- At the end of a benchmark run, summarize its results and OFFER the user the option to contribute the study to https://github.com/teo-nex/TeoBench. Explain that the public report includes the benchmark answers, synthetic tool receipts, model ID, conditions, timing and scores.
- Ask for confirmation before publishing a user's study. Without explicit consent, only run the local preview: `python3 -m teobench study submit --file PATH`. After consent, add `--publish`; never auto-merge the PR. If the user has already explicitly authorized this exact report's public submission, proceed within that scope.
- Never include API keys, auth headers, cookies, provider account details, private logs or user/home paths. Do not publish files merely because their directory is named benchmark.
- Do not claim independent model-identity verification. Public answers can be regraded; inference origin and lack of holdout access are submitter-reported.
