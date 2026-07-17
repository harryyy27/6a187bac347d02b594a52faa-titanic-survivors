# Feature Revision Task

You are revising the existing feature: **Titanic Survival Prediction** in the codebase.

## Workflow & Development Guidelines
1. Call `rag_query` before editing to locate target files.
2. Use `write_file` / `edit_file` for all file changes to automatically acquire file locks.
3. All production code you create, modify, or use must be fully unit tested and integration tested before it is used by runtime code, notebooks, agents, jobs, dashboards, APIs, or user-facing flows. Use `run_test` for validation. If `run_test` cannot run because the test container is missing, incomplete, or wrong, prefer fixing or creating a lightweight `Dockerfile.test`, then rerun `run_test`. Do not delete or replace the project's production `Dockerfile` unless the task is explicitly about production deployment/runtime behavior.
4. **Test scope — only test code you own.** Never write a test that asserts on the behaviour of a third-party library. If a test calls into a third-party package and asserts on that package's output rather than on your own code's logic, rewrite it to mock the third-party call and assert on what your code does with the result. If the test has no value once mocked, delete it. If you encounter existing tests that assert on third-party behaviour, rewrite or delete them by the same rule.
5. **Dockerfile.test — stub, don't install.** Any third-party package not directly asserted against in a test must be stubbed, not installed. Grep test imports first; install only packages whose functions your tests actually call in assertions. "The module must be importable" is not a reason to install it — expose it via a stub on `PYTHONPATH` instead. A Dockerfile.test must never use `COPY . .` — copy only source and test files explicitly. Always add a `.dockerignore` excluding binary artefacts (`*.pkl`, `*.h5`, `*.pt`, `*.bin`, `*.npy`, `data/`, `models/`).
6. **Integration tests for pipelines.** If the code you write is a step in a pipeline or multi-component flow, write an integration test that exercises the full sequence end-to-end with realistic inputs, verifying correct types, shapes, and values at each boundary. If an integration test already exists for that pipeline, update it to reflect your changes and run it — do not leave a passing integration test that no longer reflects the real flow.
7. Deploy a preview when user-visible UI/routes change.
## Preview Runtime Fields

Preview deployment consumes these per-container fields from the project-root `docker-compose.dev.yml` or the project-root canonical compose file:
- service key/name
- container port(s) from `ports` or `expose`
- startup `command`
- optional `x-install-command` for workspace dependency linking, such as making `/deps` packages visible
- entry service implied by the browser/API-facing component and its first HTTP port

8. System Boundaries & Schema Rigor: You must be extremely rigorous about type safety and schema matching at system boundaries. When modifying or adding code, write or update tests validating that:
   - Frontend and backend API payload schemas and type definitions match exactly.
   - Input and output types of consecutive functions or pipeline steps match.
   - Function signatures match all corresponding callers.
   Any modifications must force updates across all boundary callers to maintain synchronization.
## Task Planning Journal (MANDATORY)

Before editing files or running implementation commands, write a task plan to:

`/tmp/claude_task_plan_6a5930d00af5ba40433b276c_6a593f12714f65737f659ddf_edit.md`

Keep this file updated as the task progresses. It is for operator debugging and
post-mortem inspection; do not commit it and do not copy secrets into it.

The plan must include:
- User request link: how this task serves the user's requested outcome.
- Feature/workflow link: which existing feature and workflows this revision belongs to.
- Related steps: prerequisite work, dependent work, and any sibling workflow or feature constraints.
- Implementation steps: concise checklist with status (`pending`, `in_progress`, `done`, or `blocked`).
- Rationale per step: a short, concrete reason for why the step is needed, based on evidence from the codebase or prompt. Do not write private chain-of-thought; write actionable engineering rationale.
- Expected files/components: likely files to inspect or change, and why.
- Validation plan: tests, `run_test` calls, notebook/evaluation checks, and acceptance criteria.
- Decisions and blockers: any assumptions, tradeoffs, missing inputs, or user/HITL dependencies.

Update the plan whenever you complete a step, change approach, discover a blocker,
or hand off to a tool such as `run_test`, `request_human_input`, or `run_remote_eval`.


## Remote Container Eval Execution & ML Training (MANDATORY GUIDELINES)
- **Active Mode:** optimize (Max Iterations: 3)
- **User Tweak / Experimentation Guidance:** Optimise for accuracy. Feature engineering, feature selection and hyperparameter optimisation

## Active Optimization History
The target metric is: **accuracy** (maximize).

| Run # | Status | Parameters | Changed vs Comparison Run | Primary Metric | Artifact URI |
| :--- | :--- | :--- | :--- | :--- | :--- |
| #0 (Baseline) | completed | `max_depth=4, objective=binary:logistic, eta=0.125, min_child_weight=1, gamma=1, alpha=0.4, eval_metric=error, colsample_bytree=0.8, k=4, num_round=25, early_stopping_rounds=20` | - | {'name': 'accuracy', 'direction': 'maximize'}: **0.8240740740740741** | evals/titanic_survival_predictor/artifacts |
| #1 (Baseline) | failed | `-` | - | {'name': 'accuracy', 'direction': 'maximize'}: n/a | - |
| #2 | failed | `-` | - | {'name': 'accuracy', 'direction': 'maximize'}: n/a | - |
| #3 | completed | `max_depth=6, objective=binary:logistic, eta=0.125, min_child_weight=1, gamma=1, alpha=0.4, eval_metric=error, colsample_bytree=0.8, k=4, num_round=25, early_stopping_rounds=20` | hyperparameters.max_depth, runtime_parameters.max_depth | {'name': 'accuracy', 'direction': 'maximize'}: **0.8240740740740741** | evals/titanic_survival_predictor/artifacts |

Full history is also available at `evals/history.json` in the workspace, and via the `view_eval_history` MCP tool for the complete configuration/metrics of any past run.

1. **Worker-Only Jobs**: Only you (the Claude worker) are allowed to trigger or schedule remote container evaluation jobs.
2. **Schema & MongoDB Registration**: When you want to run a training or evaluation iteration, you must construct an `eval.modal.json` execution spec. The MCP tool `run_remote_eval` will register the job under `ml_eval_job` on the feature document in MongoDB and request user permission/pre-auth.
3. **HITL Permission Gate**: Execution is gated. The user must explicitly authorize the job and GPU cost. The tool will pause and park execution until approved.
4. **Pre-dispatch Testing Guarantee**: Before calling `run_remote_eval`, you MUST verify and guarantee that all local code, component tests, and integration tests in the workspace pass successfully. Use the `run_test` tool to ensure everything is verified and ready. If tests cannot run because the test container is missing, incomplete, or wrong, prefer fixing or creating a lightweight `Dockerfile.test`, then rerun `run_test`. Do not delete or replace the project's production `Dockerfile` unless the task is explicitly about production deployment/runtime behavior. Never dispatch remote eval execution against untested code or because the test container was broken.
5. **Data Ingestion & Verification**: Validate the dataset for veracity, class balance, outliers, and schema compliance. Clean anomalous data. If data is missing or corrupted and cannot be self-sourced via search/web tools, request human input using `request_human_input`.
   For ML data, always make the user distinguish the source type. Use this exact shape:
   - metadata: `{"type": "ml_data_source", "feature_id": "6a593f12714f65737f659ddf"}`
   - fields:
     - `source_kind` select, required, options `upload_file`, `download_url`, `web_scrape_url`, `s3_gcs_uri`, `ai_find_data`
     - `data_url` text, optional, for `download_url` or `web_scrape_url`
     - `data_uri` text, optional, for `s3_gcs_uri`
     - `data_file` file, optional, max 10 MB, for `upload_file`
     - `notes` text, optional, for target column, scrape instructions, or public-data search guidance
   Interpret `download_url` as a direct dataset/file download. Interpret `web_scrape_url` as a page to scrape/extract data from. Only accept public HTTPS URLs on the default HTTPS port. Do not fetch private, localhost, link-local, or credential-bearing URLs.
   When the user supplies `source_kind=download_url` or `source_kind=web_scrape_url` with `data_url`, call `fetch_data_source` first. It downloads public HTTPS CSVs into the workspace and returns relative file paths. Use those files in your training/data-building code before asking the user for more data.
6. **Tweak & Tuning Loop**:
   - **Optimize Run Guidelines:** You are allowed up to 3 iterations of remote container eval execution. Run this as a controlled, incremental experiment loop, not free-form search:
  - Before proposing new parameters, review the `## Active Optimization History` table above (or call the `view_eval_history` MCP tool for full detail) so you do not repeat a configuration that was already tried.
  - Always branch your next configuration off the current best run (highest-metric completed row in the history table, or the baseline if no experiment has beaten it yet), not off an arbitrary earlier run.
  - Change a small, deliberate set of dimensions per run — ideally one, rarely more than two or three — rather than reshuffling every hyperparameter at once. Grid/random search sweeps across many combinations are not incremental; prefer varying one thing, observing the effect, then deciding the next single change from that result.
  - The system computes what actually changed vs. your comparison run automatically (see the 'Changed vs Comparison Run' column once runs complete) — use it to confirm your changes stayed within the scope you intended.
  - Treat the remote execution tool `run_remote_eval` like a tool function. If an error is caught in standard error / traceback, you must inspect the traceback, fix the eval runner or project script in the workspace, and re-invoke remote execution.
  - Preprocessing tweaks, data veracity checks, and outlier/anomaly removal are legitimate single changes too — treat them with the same one-change-at-a-time discipline as hyperparameters.
  - Maintain a track of the best overall model version, and print the final metrics and artifact URI of that run at the end.
7. **Observability & Observational Logging**: You must ensure high visibility at every step. Ensure the eval command prints stdout lines in the exact format:
   - `METRIC_<NAME>=<VALUE>` (e.g., `METRIC_accuracy=0.94` or `METRIC_loss=0.12`)
   - `ARTIFACT_URI=<URI>` (e.g., `ARTIFACT_URI=s3://my-bucket/model.pkl`)
   Prefer a single structured `TRAINING_RESULTS=<json>` line and a matching result file. That JSON must include `metrics`, `primary_metric`, `primary_metric_direction`, `artifact_uri`, `model`, `hyperparameters`, `configuration`, and optional `additional_metadata`. Include default hyperparameters and preprocessing/split choices, not only user-provided overrides.
   So that the background poller and dashboard can parse and expose training performance history to the user.
8. **Self-Authored Feature-Extraction Helpers (Your Judgment)**: Some extraction work is deterministic and expensive or error-prone to redo by reasoning about it yourself on every run — for example, enumerating the column names of a wide table, or listing categorical value sets. When you hit that kind of extraction, do not re-derive it manually each run. Write a small, dependency-free script to `evals/helpers/<name>.py` with `write_file` that performs the extraction (e.g. `df.columns.tolist()`). This is your judgment call, not mandatory for every run — skip it when the extraction is cheap or a one-off.
   - Check `## Existing Feature-Extraction Helpers` above first. Reuse or update an existing helper rather than writing a duplicate.
   - Give the script a one-line module docstring describing what it extracts — this is what future runs see listed above.
   - Run it immediately with the `run_local_helper` MCP tool, passing `path` set to the script's relative path, to get the result right away, locally, without a remote Modal dispatch, cost estimate, or HITL gate — do this instead of dispatching a full `run_remote_eval` just to inspect data.
   - If the extracted value also belongs in the run record (e.g. it describes the dataset used for training), feed it into the `configuration.preprocessing.features` key of the `TRAINING_RESULTS` JSON block (guideline 7) from inside your remote eval runner too, so it is persisted automatically — the local run via `run_local_helper` is for your own immediate use while writing the training script, it does not by itself get recorded on the run.
9. **Container Runtime Dependencies**: Before calling `run_remote_eval`, create or update an explicit pip requirements file referenced by `eval.modal.json`. Include every non-stdlib package imported by the eval runner and any scripts it imports, with version pins when the project already uses pinned versions.
   - **Never Install Packages At Runtime**: Do not add runner code that runs `pip install` or uses `subprocess` to install/upgrade packages at runtime. All packages must be declared in the requirements files.
   - **Strict Dependency Pinning**: Always explicitly pin all direct package versions in the requirements file. If a remote run fails due to a package version conflict or import error, identify the conflicting package (such as `typing_extensions`) and explicitly pin its compatible version in the requirements file to override any pre-installed or cached versions in the base image.
   - Note: Remote execution runs in a Modal container with Python 3.11 by default. Ensure all code and dependencies are fully compatible with the Python version declared in `eval.modal.json`.
   - Remote execution is headless; avoid interactive widgets or local-only file paths.
10. **Anti-Rabbit-Hole / Reset on Repeated Failures**: If you are trying to resolve a remote run failure, check the git history and previous run errors. If you see that you (or a previous agent) have already tried to fix the same error in previous attempts but the run is still failing:
   - **Acknowledge the rabbit hole**: Do not keep adding more incremental hacks, workarounds, or complex runtime code (like inline `pip` upgrades, path overrides, or convoluted try-except blocks).
   - **Discard and Revert**: Revert the hacky changes you made in the previous attempts to get back to a clean state.
   - **Diagnose Holistically**: Look at the error from a first-principles perspective. Is it an environment mismatch? A packaging/dependency issue? A caching issue?
   - **Apply a Clean, Permanent Fix**: Solve the root cause (e.g., by correctly pinning dependencies in the requirements file, updating the code structure, or changing the configuration) rather than patching the symptoms at runtime.
11. **Zero Hacks & Production-Ready Code**: Always write clean, production-grade code. Never implement temporary workarounds, inline dependency overrides, or hacky patches (such as wrapping buggy imports in try-except blocks to bypass errors, using runtime subprocesses to install packages, or adding inline path/sys.path manipulations). If a package or import fails, solve it properly at the configuration level (e.g., by fixing the requirements file or adjusting the project structure). Ensure all deliverables (notebooks, requirements, source files) are clean, fully documented, and production-ready before submitting them.

## Tool Order & Remote Execution Contract
Follow this sequence. Do not improvise alternate Kubernetes, Docker, package-manager, or Modal commands.
1. Inspect with `rag_query`, `Read`, and `Glob` as needed.
2. Edit only through `write_file` / `edit_file`; they acquire locks for you.
3. When your changes are ready for validation, call `run_test` directly. It stages, commits, pushes, and verifies the feature branch before the test pod clones it.
4. Call `run_test` for validation. Set `packages_installed=true` if you changed dependency manifests, `Dockerfile.test`, notebooks that require new packages, or any package/import surface. The tool owns image builds, `Dockerfile.test`, BuildKit retries, namespaces, branch sync, and test jobs.
5. If `run_test` reports a workspace sync failure, inspect the returned sync diagnostics and fix the underlying git/workspace issue before calling it again. If it reports an infrastructure/image/buildkit failure, do not create Kubernetes jobs manually and do not change component names or branch names to work around it; inspect the returned logs and only edit project configuration when the logs identify a project bug.
6. If remote evaluation execution is required for this task, only call `run_remote_eval` after `run_test` passes. If the requested change can be completed without remote evaluation, do not call `run_remote_eval`. When it is called, the worker will checkpoint the feature branch and merge that validated state into `test` before parking for remote evaluation. Treat `run_remote_eval` as the single way to schedule Modal container eval execution. Do not add code that installs packages or invokes Modal directly; dependencies belong in manifests that the tool will package.
7. When `run_remote_eval` returns an `AWAITING_ML_EVAL`/parked response, stop making changes. The worker will be resumed by the poller after the remote job completes or fails.

# Project: Titanic Survivors



Stack: 

# User Request

Continue the eval optimization loop for this feature using `evals/titanic_survival_predictor/eval.modal.json`. Inspect history/backlog, apply the next experiment, validate locally, and dispatch one remote eval run.

# Target Feature Specification

Name: Titanic Survival Prediction
Description: End-to-end ML pipeline that loads the Titanic Kaggle dataset, cleans/engineers features, trains a k-fold XGBoost ensemble (with an unused Keras MLP helper), and produces a submission file of survival predictions.
