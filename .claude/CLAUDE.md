# Integration Test Phase

You just finished implementing a workflow. Now run integration tests through the test runner.

## Project: Titanic Survivors
Stack: **Proposed Architecture - brief summary**

Titanic Survivors Web App

Adds a browser UI and a thin prediction API around the existing titanic_survival_predictor training pipeline so users can enter passenger details on a website and receive a survival/death result with themed animations.

Architecture_components:

0. api (fastapi)

Programming Language:

python

Technology:

fastapi, uvicorn, pydantic, pandas, numpy, scikit-learn, xgboost, joblib, python-dotenv, orjson, starlette, aiofiles, requests, typing-extensions

Responsibilities:

Exposes an HTTP prediction API that wraps the existing titanic_survival_predictor model. On startup, attempts to load serialized artifacts produced by the existing pipeline from ./artifacts (e.g., ./artifacts/titanic_ensemble.pkl and ./artifacts/feature_pipeline.pkl). If artifacts are missing, optionally invokes the existing titanic_survival_predictor module (as a Python import or subprocess) to run its training routine to generate them, without modifying that code. For request handling, validates incoming passenger fields with Pydantic (fields like Pclass, Sex, Age, SibSp, Parch, Fare, Embarked, Cabin, Ticket, Name if required by the existing feature engineering). To ensure feature parity, first tries to import and call any feature engineering utilities from titanic_survival_predictor (e.g., titanic_survival_predictor.features.transform(df)); if unavailable, falls back to loading a serialized preprocessing pipeline saved by the training run. Applies the ensemble model to the engineered features and returns a JSON response containing: prediction (0/1), probability, and a friendly label ('survived'/'did_not_survive'). Provides endpoints: GET /health (service health), GET /model/info (artifact metadata such as model version timestamp, hash), POST /predict (single passenger), POST /predict/batch (bulk), and POST /model/reload (reload artifacts without restart). Enables CORS for the web component origin so the website can call the API directly. Uses orjson for fast JSON and returns deterministic schemas so the web form can map fields unambiguously.

Rationale:

FastAPI provides a lean, typed, and performant Python API that can co-reside in the same Python environment as titanic_survival_predictor, letting us import its feature engineering or run its training routine. Keeping the prediction adapter in Python avoids cross-language serialization issues with XGBoost/sklearn artifacts. We include both import-and-call and artifact-load paths to integrate cleanly with the existing pipeline regardless of how it currently persists models. The explicit endpoints and CORS configuration make it straightforward for a browser SPA to consume.

1. web (react)

Programming Language:

typescript

Technology:

react, react-dom, axios, zustand, react-hook-form, zod, @hookform/resolvers, lottie-web, clsx

Responsibilities:

Browser SPA that renders a quaint, Titanic-themed form for entering passenger details used by the existing model (Pclass, Sex, Age, SibSp, Parch, Fare, Embarked; optionally Cabin/Ticket if the existing feature engineering expects them). Validates inputs client-side with react-hook-form and zod before sending to the API. Calls the api POST /predict endpoint via axios and displays the prediction: plays a survival animation if predicted to survive, or a death animation otherwise, using lottie-web assets stored under public/animations (e.g., public/animations/survive.json and public/animations/not_survive.json). Provides basic UX flows: reset form, try another passenger, and shows probability/confidence. Includes environment-based configuration (e.g., VITE_API_BASE_URL) to target the api component. Sets CORS-friendly headers only on the client side (actual policy is enforced server-side by api). Ships a minimal Titanic-themed style (colors, typography) with TailwindCSS utility classes.

Rationale:

React with Vite offers a fast, lightweight SPA suitable for a single-page form-and-result workflow. TypeScript ensures typed request/response parity with the API. Lottie provides high-quality, easily swappable animations without heavy assets. Using small libraries (react-hook-form, zod) keeps the codebase simple while delivering robust validation and state management.


## What you built
Feature: API Service Foundation (FastAPI + CORS + Config)
Workflow: Health Check (Liveness/Readiness) — A user or monitoring system retrieves health status to verify service availability and basic readiness.

Steps implemented:
  1. 1) User navigates in a browser or monitoring tool to GET http://<host>:<port>/api/v1/health; feature is visible via health route [Container: user browser/monitor] Deps: []
  2. 2) Request hits uvicorn, passed to FastAPI router /api/v1/health; request start time recorded (Server-Timing middleware if enabled) [Container: backend/api process] Deps: [1]
  3. 3) Handler reads app.state (process_start, settings, readiness, version) and builds response payload with status, service, env, time (UTC ISO8601), version, uptime_ms, dependencies {'model_artifacts':'unknown'} [Container: backend/api process] Deps: [2]
  4. 4) Response returned as ORJSONResponse with 200 and Cache-Control: no-store; Server-Timing header included if enabled [Container: backend/api process] Deps: [3]
  5. 5) Per-request logger writes structured access log with method, path, status_code, duration_ms, client_ip, user_agent [Container: backend/api process] Deps: [4]
  6. 6) Browser/monitor displays JSON payload and confirms 200 status [Container: user browser/monitor] Deps: [4]

## Your task

1. Identify which files changed in the implementation session.
2. Identify which components those files belong to (e.g. `backend/`, `frontend/`).
3. For each changed component call `run_test`:
   - `root_directory`: the component folder relative to workspace root (e.g. `"backend"`)
   - `packages_installed`: `true` if dependency manifests changed (requirements.txt, package.json, Pipfile, pyproject.toml, etc.), otherwise `false`
   - `command`: only set this if you need a narrower test path than the component default
4. If tests fail, diagnose the root cause, fix the code, then call `run_test` again. Keep iterating until tests pass or you are certain further attempts will not help.
   If tests cannot run because the test container is missing, incomplete, or wrong, prefer fixing or creating a lightweight `Dockerfile.test`, then rerun `run_test`. Do not delete or replace the project's production `Dockerfile` unless the task is explicitly about production deployment/runtime behavior.
5. When all tests pass, end your response with exactly: `INTEGRATION TESTS: ALL PASSED`
6. If you exhaust your attempts without passing, end with: `INTEGRATION TESTS: FAILED` followed by a description of what is still failing and why.

Use `run_test` only — do not run test commands directly in bash. The test runner provisions a Kubernetes pod with the correct environment.
