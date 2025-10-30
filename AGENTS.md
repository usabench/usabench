# Repository Guidelines

## Project Structure & Directory Map
- `USABench/` is the Python package; `core/` defines shared dataclasses, enums, and evaluator templates (`base.py`, `loader.py`, `production_client.py`) that every workflow reuses.
- `USABench/evaluators/` hosts three parallel stacks: production Text2SQL (`production_sql.py`), production function calling with real BLS/BEA APIs (`berkeley_function.py`), and legacy/lightweight variants (`sql.py`, `function.py`, `berkeley_fcl.py`, `enhanced_sql.py`).
- `USABench/sdk/` exposes contributor entrypoints: `api.py` orchestrates evaluators, `config.py` bridges CLI flags to `EvaluationConfig`, and `results.py` performs pandas-based analysis and report generation.
- `USABench/metrics/` contains `binary_sql_metrics.py`, the deterministic execution/result checker that `ProductionSQLEvaluator` relies on; update here if you touch scoring thresholds or similarity logic.
- `USABench/data/` stores immutable assets: `usafacts.db` (SQLite with 2014–2024 coverage), `text2sql_ground_truth.json`, `enhanced_function_calling_ground_truth.json`, and `fcl_ground_truth.json` with rich metadata blocks; regenerate datasets elsewhere and drop new versions in-place only after validation.
- Repository root keeps operational scripts (`run_baseline.sh`, `test_prompt_improvements.py`), marketing collateral (`usabench-landing-page.html`, `package.json`), and knowledge docs (`README.md`, `USABench_Technical_Documentation.md`, `PROMPT_IMPROVEMENTS_SUMMARY.md`).
- Empty helper directories (`USABench/cli/`, `USABench/pipeline/`, `USABench/compat/`) are placeholders for future expansion—do not remove; populate them when adding new command modules or migration utilities.

## Environment Setup & Dependencies
- Python 3.8+ is required; install editable with extras via `pip install -e .[dev]` to pick up `pytest`, `pytest-cov`, `pytest-asyncio`, and `ruff` from `USABench/pyproject.toml`.
- USABench calls out to LiteLLM (`litellm`), so export `OPENAI_API_KEY` (and optionally `ANTHROPIC_API_KEY`, `COHERE_API_KEY`) before running evaluators; prefer a local `.env` loaded via `python-dotenv` instead of hardcoding.
- Function-call evaluations execute live BLS and BEA requests; set `BLS_API_KEY` and `BEA_API_KEY` (or override defaults) in the shell so `APIExecutor` inside `berkeley_function.py` can authenticate without editing source.
- Node 18+ is expected for the static site; `npm install` installs `http-server` and `htmlhint`, after which `npm run dev` launches a local preview and `npm run lint` validates markup.
- Respect the `.gitignore` rules for `results/` and large artifacts; generated CSV/JSON reports go under `USABench/results/` by default and should not be committed.
- When touching SQLite or JSON datasets use deterministic tooling (e.g., `sqlite3`, `jq`) to avoid timestamp churn; the metadata headers in the JSON files document provenance and should only change when datasets are re-issued.

## Evaluation Workflow (SQL & Function Calling)
- Run the CLI with `python -m USABench ...`; `USABench/cli.py` parses `--evaluation-type` (`sql`, `function`, `mixed`, `full`), difficulty filters, output destinations, and toggles for `--save-results` / `--generate-report`.
- `USABench/sdk/api.USABench` lazily constructs `ProductionSQLEvaluator` and `FunctionCallEvaluator`; call `.run_sql_evaluation`, `.run_function_evaluation`, or `.run_mixed_evaluation` when orchestrating evaluations programmatically.
- Text2SQL flow: `QuestionClassifier` narrows tables, `ProductionSchemaProvider` emits a targeted schema block, `ProductionLLMClient` prompts the model, and `Text2SQLEvaluator` checks execution accuracy and result correctness against `usafacts.db` and optional `expected_result` payloads.
- Function-calling flow: `FunctionCallEvaluator` issues strict prompts that demand the `Function:`/`Parameters:` format, parses responses, and scores them with four components (selection, parameters, execution, results) while optionally hitting live APIs through `APIExecutor`.
- Legacy evaluators (`sql.py`, `function.py`, `berkeley_fcl.py`) still backstop older datasets and parsing strategies; preserve them for regression comparisons and update them in lockstep if you change prompt constraints.
- `run_baseline.sh` demonstrates a mixed benchmark using `sdk.api.USABench`; replace the in-script `OPENAI_API_KEY` export with your own secret or source an env file before invoking.
- `test_prompt_improvements.py` is the quick guardrail for prompt regressions: it scans evaluator files for the 2014–2024 constraint string and can be extended with additional static lint checks.

## Data Assets & Schemas
- `text2sql_ground_truth.json` enumerates 293 questions with `question_text`, `reference_sql`, optional `expected_result`, and difficulty—augmenting it requires preserving metadata keys consumed by `DataLoader.load_sql_samples`.
- `enhanced_function_calling_ground_truth.json` carries 166 higher-level workflow questions referencing abstract tools like `query_budget_data`; additions must keep `function_sequence` arrays so they translate into `ground_truth_functions`.
- `fcl_ground_truth.json` powers the Berkeley-style evaluator with 167 real API calls; each entry exposes `expected_functions` that map directly to `APIExecutor` endpoints (BLS vs BEA) and includes difficulty and category stats used in reports.
- `usafacts.db` holds primary tables `budget_outlays`, `time_series_data`, `industry_gdp`, `regional_data`, and `gdp_by_industry`; schema documentation lives inside `ProductionSchemaProvider`—update both the DB and schema strings together to stay in sync.
- Keep datasets under version control but immutable; if you must regenerate, produce a fresh file, run the full evaluation suite, and document provenance changes in `PROMPT_IMPROVEMENTS_SUMMARY.md` or an equivalent changelog.
- When introducing new sources, extend `DataLoader` methods to surface them and expose `available_functions` updates so evaluators receive the new capabilities.

## Coding Style & Prompt Authoring
- Adhere to `ruff` settings: 88-char lines, four spaces, double quotes, sorted imports with `known-first-party = ["USABench"]`; run `ruff check USABench` and `ruff format` (if installed) before submitting.
- Use `snake_case` for functions/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants, and annotate new public functions with type hints to match existing signatures in `core/base.py` and `sdk/api.py`.
- When editing prompts, keep critical constraints (2014–2024 availability, function lists, response format) co-located with execution code so reviewers can verify diffs quickly; document rationale in commit messages and update `test_prompt_improvements.py` if new invariants are required.
- Avoid embedding secrets or runnable shell commands inside prompts; if a prompt must mention API usage, keep it descriptive and reference the documented functions only.
- Logging uses the standard `logging` module (see `production_sql.py` and `berkeley_function.py`); prefer structured messages that include table names or function identifiers to simplify downstream analysis.

## Testing & QA Expectations
- Primary automation lives in `pytest`; place new suites under `tests/` (create the directory if absent) using `test_*.py` or `*_test.py` naming so the `pyproject` discovery rules apply.
- Target high-value coverage by mocking external services; isolate LiteLLM calls by injecting stub clients or using `monkeypatch` to avoid hitting external APIs during unit tests.
- Run `pytest --cov=USABench --cov-report=term-missing` before opening a PR; HTML coverage is emitted to `htmlcov/` by default—review hotspots and avoid committing the folder.
- For prompt edits or evaluator changes, execute `python test_prompt_improvements.py` and a focused CLI command (e.g., `python -m USABench --model gpt-4o --evaluation-type sql --sql-samples 5`) to validate end-to-end behavior.
- Document any skipped or slow tests with markers defined in `pyproject.toml` (`@pytest.mark.slow`, `@pytest.mark.integration`) and justify them in the PR body.

## Static Site & Frontend Assets
- The marketing page is a standalone HTML file with inline CSS (`usabench-landing-page.html`); keep styles organized by section headers already present and test in modern browsers using `npm run dev`.
- HTML linting is handled via `npm run lint` (`htmlhint`); update `.htmlhintrc` if new rules become necessary and include before/after screenshots in PRs touching the page.
- Static assets belong beside the HTML file; avoid adding large media directly—link to CDN-hosted resources or optimize images aggressively.
- Keep the Node toolchain isolated from the Python virtualenv; if you script deployments, add them as new npm scripts inside `package.json` rather than ad-hoc shell snippets.

## Baseline, Logging & Troubleshooting
- Use `run_baseline.sh` to reproduce the pre-prompt-improvement benchmark; it writes `baseline_results.json` in `USABench/` and expects network access—capture logs for regression tracking.
- `ProductionLLMClient` aggregates token usage in `total_usage`; dump or log this structure when diagnosing cost regressions or API anomalies.
- When API calls fail, `FunctionCallEvaluator` surfaces errors via `execution_details`; include these payloads in bug reports to expedite triage.
- For SQLite debugging, run ad-hoc queries with `sqlite3 USABench/data/usafacts.db 'SELECT ...'` and verify schema updates before committing code changes that rely on them.
- Keep an eye on network timeouts—`EvaluationConfig.timeout` defaults to 30 seconds; adjust via CLI or `BenchmarkConfig` when testing high-latency models and capture the configuration in your PR notes.

## Commit, PR & Release Practices
- Match the existing `type: summary` commit style seen in `git log` (`fix: ...`, `chore: ...`, `feat: ...`); keep subjects under 72 characters and describe intent.
- Break large changes into logical commits: schema migrations, prompt edits, and evaluator logic should land separately to simplify review and rollback.
- Pull requests must summarise scope, list commands run (pytest, CLI invocations, npm lint), call out dataset or prompt updates explicitly, and link issues when applicable.
- Never commit API keys or `.env` files; if a script needs credentials (e.g., `run_baseline.sh`), instruct users to export them locally and document the requirement.
- Tag releases only after recreating baseline runs and archiving generated reports; include both Python and web assets in release notes so downstream consumers know what changed.
