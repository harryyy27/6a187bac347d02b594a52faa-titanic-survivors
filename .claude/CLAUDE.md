# Production Deploy Failure Investigation

A production deployment for this project failed during Terraform apply. Your task prompt
contains the specific failure diagnosis for this run.

Rules:
1. Read the diagnosis carefully and locate the actual root cause. Cloud provider wrapper
   error text (e.g. a generic "container failed to start" or "timeout" message) often masks
   the real cause -- look for any embedded application traceback or exit message first.
2. If the failure is caused by the project's own code, dependencies, Dockerfile, or
   configuration, fix it. Use `write_file` / `edit_file` for all file changes so locks are
   acquired. Run `run_test` if relevant tests exist for the code you changed.
3. If the failure is a genuine platform/infrastructure issue (cloud credentials, quota,
   network, a transient provider outage) that cannot be fixed by changing project code,
   make NO file changes and clearly state in your final summary that this needs human
   investigation, and why.
4. Do not touch Terraform files, Helm charts, or any app_builder platform infrastructure --
   only the generated project's own application code is in scope.
5. End your final response with exactly one line: `FIX_APPLIED: yes` or `FIX_APPLIED: no`.

# Project

Name: Titanic Survivors


