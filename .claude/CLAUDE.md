# Eval Container Bundle Build Task

You are preparing a reusable container-based evaluation bundle for the existing feature:
**Titanic Survival Prediction**.

This is an eval-owned preparation step, not a normal feature edit and not a remote execution step.
Do not create notebooks. Do not use Papermill or Jupyter as the runtime boundary.

Required files:
1. A JSON execution spec, conventionally `evals/<feature-slug>/eval.modal.json`.
2. A script or module invoked by that spec, for example `evals/<feature-slug>/run_eval.py`.
3. A pip requirements file referenced by the spec, for example `evals/<feature-slug>/requirements.txt`.

Execution spec schema:
```json
{
  "backend": "modal_container",
  "version": 1,
  "python_version": "3.11",
  "working_dir": ".",
  "command": ["python", "evals/<feature-slug>/run_eval.py"],
  "requirements_files": ["evals/<feature-slug>/requirements.txt"],
  "result_files": ["evals/<feature-slug>/eval_results.json"],
  "timeout_seconds": 1800,
  "gpu_tier": "none",
  "env": {}
}
```

Rules:
1. Call `rag_query` before editing to locate the feature implementation and any existing eval assets.
2. Use `write_file` / `edit_file` for all file changes so locks are acquired.
3. Reuse an existing valid eval bundle when possible. Otherwise create the smallest reusable container eval needed for the feature.
4. Keep dependencies in the requirements file only. Do not install packages at runtime from Python code or shell commands.
5. The eval command must emit a complete, parseable run record. Prefer writing `eval_results.json` and also print one line beginning with `TRAINING_RESULTS=` containing JSON. The JSON must include:
   - `metrics`: numeric metric values, for example `{"accuracy": 0.82, "mean_cv_error": 0.18}`
   - `primary_metric`: the metric name used to compare/best-select runs, for example `"accuracy"`
   - `primary_metric_direction`: `"maximize"` or `"minimize"`
   - `artifact_uri`: URI/path for the trained model or evaluation artifact
   - `model`: a JSON object naming the estimator/model family and implementation, for example `{"name": "RandomForestClassifier", "type": "sklearn.ensemble.RandomForestClassifier"}`
   - `hyperparameters`: every model/training hyperparameter that affects results, including defaults chosen by the eval runner
   - `configuration`: preprocessing, feature engineering, split/CV, dataset, seed, and other non-model settings that affect comparability
   - `additional_metadata`: optional details such as fold metrics, warnings, or environment notes
6. The eval script must be deterministic enough for a baseline run and accept optional parameters from the `EVAL_PARAMETERS_JSON` environment variable. Merge those parameters into the emitted `hyperparameters` / `configuration` so the dashboard can show exactly what was evaluated.
7. Run relevant local tests with `run_test` when project code, helper code, dependencies, or testable evaluation code changes.
8. Do not call `run_remote_eval`, Modal, Kubernetes jobs, or any remote execution command.
9. Do not perform tuning, ablations, optimization, or repeated experiments. For run type `baseline`, prepare the baseline evaluator only.
10. End your final response with exactly one line in this format:
   `EVAL_EXECUTION_SPEC=<relative/path/to/eval.modal.json>`

# Project

Name: Titanic Survivors



Stack: 

# Target Feature

Name: Titanic Survival Prediction
Description: End-to-end ML pipeline that loads the Titanic Kaggle dataset, cleans/engineers features, trains a k-fold XGBoost ensemble (with an unused Keras MLP helper), and produces a submission file of survival predictions.
Feature kind: model_training
Primary metric: 
