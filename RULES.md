# Quant Trading Framework Project Guidelines

## PROJECT OVERVIEW
This is a **multi-purpose Quant Trading Framework** designed to work with **cTrader**.
- **Root Folder:** `cAlgo` (located in Documents for cTrader compatibility).
- **`Library/` (Python):** Core logic, AI models, trading systems, persistence, and Dash-based frontend.
- **`Sources/` (C#):** cAlgo Robots, Indicators, and Plugins that interface with cTrader and bridge to the Python backend via shared memory (Windows named shared-memory `mmap` + auto-reset Event signaling, single-slot request/response lockstep).
- **`Tests/` (Python):** Pytest suite mirroring the `Library/` folder structure.
- **`Setup/` (Python):** One-shot scripts for database universe population.

## TOOL-SPECIFIC COMMANDS
For all shell executions, use the following patterns:
- **Environment:** Use the `Quant` conda environment for all Python scripts (`conda run -n Quant <command>`).
- **Testing:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware`.
- **C# Build:** `dotnet build Sources/`.
- **Git Repository:** The project root (`cAlgo`) is a dedicated Git repository.
- **File Staging:** Any tool-driven operation that creates a new file must be immediately followed by `git add <file_path>` to automate the staging process.
- **Git Commits:** **NEVER commit changes.** You may stage files using `git add`, but leave the final `git commit` to the user so they always have the final word.

## CODING PHILOSOPHY
1. **Precision & Accuracy:** Prioritize correct, working code over speed.
2. **Simplicity & Optimization:** Do **not** overthink or over-engineer.
    - Solutions should be as simple and optimized as possible.
    - Avoid unnecessary abstraction or complexity.
    - Prefer concise, readable, and performant code.
3. **Measure, Don't Guess:** For performance work, profile before optimizing (`cProfile` sorted by cumulative + tottime, targeted micro-benchmarks). Validate bottleneck hypotheses with data, not intuition.

## RESPONSE STYLE
Keep answers concise and scannable: lead with the conclusion, prefer **bullet points and tables** over prose, and omit filler. Reserve long-form paragraphs for when they are explicitly requested.

## CODING STYLE & ORGANIZATION
1. **Language:** All written content (code, identifiers, comments, markdown, docs) must use **English (US)** spelling (e.g., `Optimization`, not `Optimisation`; `Initialization`, not `Initialisation`; `behavior`, not `behaviour`). The only exception is identifiers that mirror an external API verbatim (e.g., cTrader's `Cancelled`), which keep the upstream spelling to preserve alignment.
2. **General:** No docstrings or comments. Maintain tidy files (no trailing spaces). One blank line after `class` and between methods.
3. **Naming:** `CamelCase` for public members; `_naming_` (snake_case with leading/trailing underscores) for private ones; `UPPER_SNAKE` for public constants and `_UPPER_` for private class constants. Use lowercase for `__post_init__` arguments.
4. **Typing:** Use `Self` from `typing_extensions` for instance returns to maintain Python 3.10 compatibility. Use `from __future__ import annotations` as the first line only if required for forward references. Avoid using typing classes where built-in types suffice.
5. **Imports:** Organized in a sorted ladder-style block. Separate external and project (`Library.*`) imports with one blank line. Use **explicit imports** for internal library modules. Always import `np`/`pd`/`pl` from `Library.Database.Dataframe` (never directly from `numpy`/`pandas`/`polars`) so the shared print/display configuration applies; treat these as project imports. The only exceptions are `Dataframe.py` itself and any module inside its import closure (`Database.Dataclass`, `Utility.Typing`), which must import directly to avoid circular imports.
6. **Density:** Keep method bodies dense without internal blank lines (except complex `__init__`). Maintain standard spacing in signatures and assignments.
7. **Architecture:** Order methods by category (Connection → Disconnection → Business) and then by complexity (simplest first). Use `@staticmethod` for stateless logic and `InitVar` for temporary inputs.
8. **Dataframes:** Capitalize framework-level columns (e.g., "Date", "Security"). Prefer Polars (`pl`) for performance; use Pandas (`pd`) for compatibility.

## LOGGING CONVENTIONS
Logs must be short, objective, informative, and visually distinctive so a specific line is easy to find.
1. **Message Format:** Use `<Category> Operation: <Outcome> (<primary detail>)`. Join any additional fields with the middle dot ` · ` (e.g., `Phase Warmup: Completed · 1.20s · 205 Ticks · 41 Bars`).
2. **State Transitions:** Render machine moves as `[StateA] → (Reason) → [StateB]`. The arrow `→` conveys motion and is reserved for transitions. A true state change (`To` differs from the current state) logs at `Info`; a self-loop (`To` equals the current state) logs at `Debug`. Hot-path self-loops on per-bar/per-tick events keep `reason=None` so they stay silent entirely.
3. **No Commas or Periods:** Never use `,` or `.` in a log message. To separate fields or list items, use the space-padded middle dot ` · ` in place of a comma — never a literal `,` (e.g., `5137 Records · 2041 Unique Rows` not `5137 records, 2041 unique rows`). Keep everything in one sentence; use `:`, ` · `, parentheses, and symbols instead. No end-of-sentence periods.
4. **Debug vs Info:** `Info` is strictly trading/execution and periodic trader-useful information (machine state switches, orders/positions/trades opened or closed, reports, phase summaries). `Debug` is everything else (bloat): connection/handshake details, per-query execution, transaction commits, warmup internals (computed Window, Bars fetched from database, Bars received from updates, first/last warmup dates, first/last execution dates).
5. **Errors & Exceptions:** Error and exception logs share one format and text: `<Category> Operation: Failed · <Reason>`, with the reason's leading word capitalized (e.g., `Connect Operation: Failed · Due to port being in use`).
6. **Tags:** Rely on the logging module's class tags (common prefix shown before the verbose level) and instance tags (identifying the calling class/subclass). Keep tags coherent and transversal across all logs so the source is always identifiable.
7. **Capitalization:** Use Title Case for fixed labels and nouns (`Bars`, `Ticks`, `Data Points`) and capitalize the leading word of free-text reasons.

## CONTEXT AWARENESS PROTOCOL
Before answering code-related questions, execute this check:
1. **Scan References:** Identify classes/functions referenced in the request.
2. **Verify Context:** Check if definitions are present.
3. **Criticality Assessment:**
    - **Missing Core Logic:** If a missing file is *crucial* to the business logic being modified **STOP** and ask for it.
    - **Missing Utilities/Peripheral:** If the missing code is a generic utility or standard library wrapper, **PROCEED**.

## DOCUMENTATION MAINTENANCE
If structural changes (new folders or modules) are detected that are not reflected in this file:
1. **Notify the User:** Explicitly mention the discrepancy.
2. **Propose an Update:** Generate the updated markdown content for `RULES.md` to keep the prompt synchronized with the actual codebase.

## PROJECT STRUCTURE MAP

### Python (`Library/`)
- **`Library/App`**: Core Dash wrappers (`AppAPI`, `PageAPI`, `LayoutAPI`, `ComponentAPI`, `FormAPI`, `CallbackAPI`, `ChartAPI`, `NotificationAPI`, `InjectionAPI`).
- **`Library/Bloomberg`**: Bloomberg API integration (`HistoricalAPI`, `IntradayAPI`, `ReferenceAPI`, `StreamingAPI`, `QueryAPI`).
- **`Library/Database`**: Database abstraction layer (`DatabaseAPI`, `DataclassAPI`, `DatapointAPI`, `QueryAPI`, `EnumerationAPI`, dataframe utilities). Supports Oracle, Postgres, and SQL Server via subpackages.
- **`Library/Engine`**: Generic multi-state-machine engine (`EngineAPI`, `MachineAPI`, `StateAPI`, `TransitionAPI`). Zero trading domain knowledge.
- **`Library/Formulas`**: Financial and utility formulas (`DateTime`, `Spot`, `Historical`).
- **`Library/Indicator`**: Trading indicators split into `Technical`, `Fundamental`, `Sentimental` subpackages, plus the umbrella `IndicatorAPI`.
- **`Library/Logging`**: Python logging handlers (`HandlerLoggingAPI`, `ConsoleLoggingAPI`, `FileLoggingAPI`, `BufferLoggingAPI`, `ReportLoggingAPI`, `BucketLoggingAPI`, `WebLoggingAPI`, `EmailLoggingAPI`, `TelegramAPI`, `VerboseLevel`).
- **`Library/Market`**: Market data structures (`MarketAPI`, `BarAPI`, `TickAPI`, `PriceAPI`, `SeriesAPI`, `TimestampAPI`).
- **`Library/Model`**: AI/ML components (`AgentAPI`, `DDPG`, `Network`, `Noise`, `Memory`).
- **`Library/Parameters`**: Configuration management (`ParametersAPI`, `Parameters`) backed by YAML files; broker-specific subfolders for strategy/system parameter trees.
- **`Library/Portfolio`**: Trading portfolio entities (`PortfolioAPI`, `AccountAPI`, `OrderAPI`, `PositionAPI`, `TradeAPI`, `PnL`, `SizingAPI`, `StatisticAPI`).
- **`Library/Protocol`**: Wire protocol shared with the C# Connector. `Action/` (commands sent to cTrader) and `Update/` (events received from cTrader); `ActionID` / `UpdateID` enumerations.
- **`Library/Spotware`**: Spotware/cTrader API helpers (`SpotwareAPI`, `MarketAPI`, `PortfolioAPI`, `ExecutionAPI`, `UniverseAPI`, `StreamingAPI`). Largely a research/integration scratchpad.
- **`Library/Strategy`**: Strategy framework (`StrategyAPI`, `StrategyType`). Strategy implementations split into `Rule/` (e.g., `Download`, `NNFX`), `Model/` (e.g., `DDPG`), and `Hybrid/` subpackages.
- **`Library/System`**: Python Trading Engine (`SystemAPI`, `SystemType`, `LifecycleAPI`, `RealtimeAPI`, plus legacy `BacktestingAPI`/`OptimizationAPI`/`LearningAPI` placeholders pending refactor). `Main.py` is the CLI entry point.
- **`Library/Universe`**: Tradable universe definitions (`UniverseAPI`, `ProviderAPI`, `CategoryAPI`, `TickerAPI`, `ContractAPI`, `SecurityAPI`, `TimeframeAPI`).
- **`Library/Utility`**: Helper library (`PathAPI`, `DateTimeAPI`, `IOAPI`, `HTMLAPI`, `ImageAPI`, `ChartAPI`, `RuntimeAPI`, `ServiceAPI`, `StatisticAPI` (timer/profiling), `Math` (truncation/precision helpers), `TypingAPI`, `FileAPI`, `MemoryAPI`).

### C# (`Sources/`)
- **`Sources/Robots`**: cTrader Robots — Connector cBot (Python bridge via shared memory), `Strategy`, `StrategyAPI` base.
- **`Sources/Indicators`**: cTrader Indicators — Connector indicator, `Indicator` implementations, `IndicatorAPI` base.
- **`Sources/Plugins`**: cTrader Plugins and Extensions — `Plugin`, `PluginAPI` base.
- **`Sources/Export`**: Build artifacts and deployment exports.

### Testing (`Tests/`)
- **Layout:** Mirrors `Library/` (`Tests/Database`, `Tests/Engine`, `Tests/Market`, `Tests/Portfolio`, `Tests/Protocol`, `Tests/Strategy`, `Tests/System`, `Tests/Universe`, `Tests/Utility`, `Tests/App`, `Tests/Indicator`).
- **Naming:** `test_<Subject>.py` (e.g., `test_Realtime.py`, `test_Database.py`).
- **Style:** Apply the same coding rules and density as the main codebase. Do not use docstrings. Keep methods dense.
- **Exclusions:** `Tests/Spotware/` requires live broker credentials and is excluded from the standard test run (`--ignore=Tests/Spotware`).

### Setup (`Setup/`)
- One-shot scripts that populate the `Quant` database `Universe` schema (categories, providers, tickers, timeframes, contracts, securities).
- Examples: `Setup/Universe.py`, `Setup/Population.py`.
