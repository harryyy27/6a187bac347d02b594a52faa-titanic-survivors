# Test Dependency Audit — titanic_survival_predictor

## Heavy dependency cleanup

The component originally shipped as a single exploratory script
(`titanic.py`, mirrored in `Titanic.ipynb`) with no `tests/` directory at
all. The script mixed data loading, cleaning, feature engineering,
visualization, model training (XGBoost k-fold ensemble), neural-net
definition (Keras), and artifact I/O (pickle + CSV) as one long sequence of
top-level statements that executed immediately on import — there was no
project-owned unit of behavior that could be exercised without also
running full training against `xgboost` and `keras`.

Before any test could be added, the script was refactored (no behavior
change) into named, importable functions in `titanic.py`:

- Pure data-wrangling / feature-engineering functions (`fill_missing_values`,
  `drop_unused_columns`, `add_family_features`, `extract_title`,
  `consolidate_rare_titles`, `fix_zero_fares`, `scale_fare`, `scale_age`,
  `encode_categoricals`) have **no** dependency on any heavy engine — they
  operate on plain pandas/numpy.
- `build_keras_model`, `train_xgb_ensemble`, and `predict_with_ensemble`
  import `keras` / `xgboost` **lazily, inside the function body**, instead
  of at module scope. This means importing `titanic` no longer triggers
  training, and tests can stub the heavy engines only at the point they'd
  actually be invoked.
- Module-level execution (data load → train → predict → write CSV) is now
  gated behind `if __name__ == "__main__": run_pipeline()`, so importing
  the module for testing has zero side effects (no CSV reads, no training,
  no file writes).
- The plotting/visual-exploration statements (`sns.distplot`,
  `plt.show()`, correlation heatmaps) were exploratory notebook output, not
  pipeline behavior; they were not carried into the production module and
  have no corresponding tests.

## Rewritten or deleted tests

No pre-existing tests existed to rewrite or delete. `tests/test_pipeline.py`
was written from scratch under the same policy that would otherwise govern
a rewrite:

- Tests for the pure feature-engineering functions assert directly on
  project-owned DataFrame transformations (imputation, dropped columns,
  derived columns, title consolidation, fare/age scaling, one-hot schema).
  No third-party training/inference engine is involved.
- `test_train_xgb_ensemble_trains_k_folds_without_real_xgboost` and
  `test_predict_with_ensemble_majority_votes_across_models` exercise
  `train_xgb_ensemble` / `predict_with_ensemble` against a **fake**
  `xgboost` module (see Stubbed dependencies) and assert only on
  project-owned dispatch: number of folds trained, hyperparameters passed
  through, and the majority-vote aggregation logic. No real gradient
  boosting runs.
- `test_build_keras_model_configures_layers_without_real_keras` exercises
  `build_keras_model` against a fake `keras` module and asserts on layer
  configuration (units, activation) and compile arguments the project code
  passes — not on any real neural-network computation.
- `test_run_pipeline_data_flow_shapes_and_schema` is the one integration
  test. It monkeypatches `titanic.load_data` to return small in-memory
  DataFrames and stubs `xgboost`, then asserts on schema/shape/artifact
  handoff only (submission columns, row count, file existence) — it does
  not train a real model or judge prediction quality. This satisfies the
  "verify data flow, types, shapes, schema boundaries, artifact handoffs"
  requirement without running real local training in the test image.

No test was deleted, because there was nothing to delete — but the
approach a deletion would have taken (drop tests with no project-owned
behavior left after mocking) was applied to what would have been written:
every test above still has a concrete, project-owned assertion after the
heavy engine is stubbed out.

## Stubbed dependencies

Defined in `tests/conftest.py` as pytest fixtures, installed into
`sys.modules` only for the duration of the tests that need them (via
`monkeypatch.setitem`):

- **`xgboost`** (`fake_xgboost` fixture) — real xgboost is a compiled
  gradient-boosting training/inference engine; far too heavy for a test
  image and irrelevant to validating our own wiring. The fake module
  provides `DMatrix` (records row count only) and `train()` (records the
  params/num_round it was called with and returns a fake booster with a
  canned, deterministic `.predict()`). This satisfies the import and lets
  tests assert on *how* the project calls xgboost, not on real boosting
  output.
- **`keras`** (`keras.layers`, `keras.models`) (`fake_keras` fixture) —
  real keras/TensorFlow is a large neural-network training stack requiring
  a GPU/accelerator-capable build for full functionality. The fake
  `Sequential` records `add()`/`compile()` calls without building or
  running any real computation graph.

`scipy` was removed as a project dependency entirely: the only use in the
original script beyond exploratory plotting was `scipy.stats.mode` for
majority voting, which was replaced with `collections.Counter` (stdlib) —
simpler, dependency-free, and avoids a breaking API difference between
scipy versions for `stats.mode`. `matplotlib`/`seaborn` (exploratory
plotting only, never asserted on) were likewise dropped from the pipeline
module and are not installed or stubbed for tests.

## Installed dependencies

`Dockerfile.test` installs only:

- `pandas`, `numpy` — real, lightweight-enough libraries that the
  project's own feature-engineering functions call directly and that tests
  assert against (DataFrame values, dtypes, shapes). These are exercised
  for real, not mocked, because the test value here *is* verifying our
  pandas/numpy usage.
- `pytest` — test runner.

Not installed (stubbed instead, see above): `xgboost`, `keras`,
`tensorflow`. Not installed and not stubbed (unused by the cleaned test
suite): `matplotlib`, `seaborn`, `scikit-learn`, `scipy`.
