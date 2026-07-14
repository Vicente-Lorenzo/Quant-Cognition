# Quant Trading Framework — Handoff

Single source of truth for the `cAlgo` repo: orientation, current state, and the active backlog. Read this first, then `RULES.md` for conventions and the module map.

---

## 1. Orientation

- **Root:** `C:\Users\Admin\OneDrive\Documents\cAlgo`
- **`Library/`** Python core (engine, persistence, AI, Dash UI) · **`Sources/`** C# cTrader Robots/Indicators/Plugins (shared-memory bridge + binary protocol) · **`Tests/`** pytest mirror · **`Setup/`** provisioning + workflow registrar · **`Scripts/`** all-Python launchers.
- **Env:** `conda run -n Quant --no-capture-output ...` (`--no-capture-output` avoids a charmap crash on log `·`/`→` glyphs; also `PYTHONIOENCODING=utf-8`).
- **Test:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware --ignore=Tests/Bloomberg` — currently **543 green**.
- **Build C#:** `dotnet build Sources/` (the user builds/runs the Connector — the agent cannot).
- **Git:** stage with `git add`, **never commit** (the user commits).

---

## 2. Current state — all major systems built and validated

| System | Status |
|---|---|
| **Download + Realtime** (`RealtimeAPI`) | Done — batch/delay protocol, Subscription trimming; NNFX online = target-driven (`Stream.All & ~Stream.Tick`, bit-exact) |
| **Offline Backtesting** (`BacktestingAPI`) | Done — reproduces all 6 goldens at the data-bound floor; frozen `DatasetAPI` tape (`extract()`/`inject()`) for multi-run reuse |
| **Learning** (`LearningAPI`) | Done — full WF DRL trainer: episodes, greedy validation, early stop, multi-seed mean±std, ProcessPool `--workers`, `--fitness` report metrics, checkpoint + JSON manifest |
| **Strategies** | Four: `Download`, `NNFX` (money/risk base), `Trend` (+signal machine), `DDPG` (DRL signals wrapped by NNFX money/risk; `ActorRegularization` >0 = RDDPG) |
| **Auth** (`Library/Auth`) | Done — Postgres RBAC + Argon2 + Flask-Login + SSO provider seam (Cloudflare/OIDC JIT-provisioning); env-free (`AuthAPI(secure, secret)`) |
| **App V2** (`Library/App/V2`) | Done — injection-decorator Dash framework, auth-gated router, `/login` page, live tables (`ViewTableAPI`/`EditTableAPI`, fingerprint-gated polling) |
| **Scheduler** (`Library/Scheduler`) | Done — DB-backed orchestrator (Workflow→Task→Run + DAG), gates/retry/heartbeat-reap, service supervision + maintenance pause; Python-console API (`ManagerAPI`), CLI (`Main.py`), web UI, silent tray daemon (`Tray.py`) |
| **Setup** (`Setup/`) | Done — `python -m Setup.Install [--boot]`: in-process provisioning, registers the 3 standard workflows (`Setup` manual · `Environment` weekly · `Market` daily), creates the single `Quant Scheduler` logon task (`pythonw Scripts/Scheduler.py`) |

Strategy/engine/indicator/portfolio/reporting code is byte-shared between realtime and offline paths — a cTrader online report is a valid oracle for the offline engine.

**DRL research verdict (thesis):** DDPG/SAC/TD3 paper-fidelity certified (Lillicrap/Haarnoja/Fujimoto, documented deviations only); D1 and H1 net-size sweeps found **no robust alpha** (holdout ≈ 0/negative) — a thesis result, not a bug.

---

## 3. Pinned goldens (2026-06-26, EUR 10k, conversion option ON, tick data)

Any engine change must keep reproducing all 6 (counts bit-exact, Net at the documented floor). Folders under `Reports/`.

| # | Symbol | TF | Window | Folder | Net |
|---|---|---|---|---|---|
| 1 | EURUSD | D1 | 2023 → 24 | `2026-06-26 00-47-01` | 75.55 |
| 2 | EURUSD | D1 | 2022 → 25 | `2026-06-26 00-48-48` | −127.33 |
| 3 | EURUSD | H1 | 2023 → 24 | `2026-06-26 00-53-28` | −2936.65 |
| 4 | USDJPY | D1 | 2023 → 24 | `2026-06-26 00-56-52` | 47.13 |
| 5 | USDJPY | H1 | 2023 → 24 | `2026-06-26 01-03-54` | −61.04 |
| 6 | USDJPY | D1 | 2022 → 25 | `2026-06-26 01-01-56` | 76.74 |

**Data state:** `Market.Tick`/`Market.Bar` complete 2012-11 → 2026-06 for EURUSD (259M ticks) and USDJPY (300M ticks); EURJPY ticks partial (validation reference only). Known gap: MN1 stops at 2026-03 (unused by goldens).

**Accuracy floor (data-bound, NOT engine bugs):** sub-pip intrabar exit residual (bar data cannot recover ms-precise SL/TP prices; tick resolution closes it) · swap residual ~0.5%/y (historical swap-rate schedule unavailable; contract's current rates applied).

---

## 4. Performance (measured)

- **Warm per-pass:** NNFX H1 year ≈ **1.5s** (2× deep-dive batch: numpy feed descent, precomputed market rows, composite-indicator skip); D1 10y ≈ 3.2s · H1 10y ≈ 25s.
- **Learning replay:** frozen indicator/market tape (Learning-only, bit-exact) ≈ **3.12×** per-pass; goldens byte-identical with the feature off/on.
- **Cold setup (once per window):** ~12–15 min preload for 10y dense ticks, then warm Parquet cache (`~/.cache/cAlgo/preload`), invalidated by `last_tick_uid`.
- **Rejected optimizations (measured, closed):** numpy ring-buffer for `SeriesAPI` (walk is already O(N), ~10-15% upside not worth bit-exactness risk) · mypyc/Cython (hot loops already sit on polars/numpy).

---

## 5. Operational notes

- **Torch env:** torch **2.12.1 CPU** (24 threads). `Library/__init__.py` preloads `libiomp5md.dll` before MKL and sets `KMP_DUPLICATE_LIB_OK` — **do not delete**. Torch is pinned in the pip section of `Quant.yml` so `--prune` refreshes cannot clobber it.
- **Learning CLI trap:** `--timeframe Hour` (parameter folder key), never `H1` — a missing key auto-vivifies an empty parameter node.
- **Learning worker logs:** spawn workers set console `Warning` (flood control); `LearningAPI._export_` has a known signature collision — run with `export=False`.
- **Custom logging:** stdlib `logging.disable()` does nothing; silence via handler levels (`log.console.set_verbose_level(...)`).
- **Scheduler:** daemon ticks every 30s (`SchedulerAPI(interval=...)`); everything (workflows/tasks/runs/DAG edges) persists in the Postgres `Scheduler` schema; a boot/logon replays `Environment.Update → Tunnel → Server` in strict order; per-run logs land in `Runs/<uid>.log`, daemon log in `Logs/Scheduler.log` (tray → Terminal live-tails it).
- **No `QUANT_*` environment variables anywhere** — configuration is constructor arguments only (per user directive).
- **Report folders** are named at seconds granularity — two exports in the same second collide (needs a uniqueness suffix before fleet-scale exporting).

---

## 6. Backlog

- **Realtime hardening (audited 2026-07-02, deferred to a cTrader session):** warmup bars double-added to the market buffer · `BufferAPI._worker_` flush deadlock on connect failure · transport hardening (handle validation, length bounds, batch offset guards) · unused universe buffer · watchdog only armed on `Init`.
- **Optimization refactor:** rebuild `OptimizationAPI` on the tape seam (`extract()` once → `inject()` across N param runs/workers).
- **Strategy state recovery:** persist Signal/Risk machine state on Live restart (`SessionAPI.State` bytes, load at `deploy()`, save on `Shutdown`).
- **`receive_update_security`:** parse the C# security payload to enrich `SecurityAPI` (pip size, commission).
- **Hung-peer timeout watchdog** (current watchdog only detects peer death by PID).
- **Database `Dataframe.frame` dtype preservation + FK-aware `reorder`:** blocked — `reorder` must become FK-aware before the per-fetch `shrink_dtype` can be removed (removes the latent Float64→Float32 price downcast).
- **C# warnings (non-breaking):** 2× `CA1416`, 3× `CS0618` deprecated order APIs; `--profile` wraps only the Python side.
