# Quant Trading Framework Project Guidelines

## PROJECT OVERVIEW
This is a **multi-purpose Quant Trading Framework** designed to work with **cTrader**.
- **Root Folder:** `cAlgo` (located in Documents for cTrader compatibility).
- **`Library/` (Python):** Contains the core logic, AI models, Backtesting systems, and a Dash-based Frontend.
- **`Sources/` (C#):** Contains cAlgo Robots and Indicators that interface with cTrader and communicate with the Python backend.

## TOOL-SPECIFIC COMMANDS
For all shell executions, use the following patterns:
- **Environment:** Use the `Quant` conda environment for all Python scripts (`conda run -n Quant <command>`).
- **Testing:** `conda run -n Quant python -m pytest Tests/`.
- **C# Build:** `dotnet build Sources/`.
- **Git Repository:** The project root (`cAlgo`) is a dedicated Git repository.
- **File Staging:** Any tool-driven operation that creates a new file must be immediately followed by `git add <file_path>` to automate the staging process.

## CODING PHILOSOPHY
1. **Precision & Accuracy:** Prioritize correct, working code over speed.
2. **Simplicity & Optimization:** Do **not** overthink or over-engineer.
    - Solutions should be as simple and optimized as possible.
    - Avoid unnecessary abstraction or complexity.
    - Prefer concise, readable, and performant code.

## CODING STYLE & ORGANIZATION
1. **Language:** All written content (code, identifiers, comments, markdown, docs) must use **English (US)** spelling (e.g., `Optimization`, not `Optimisation`; `behavior`, not `behaviour`).
2. **General:** No docstrings or comments. Maintain tidy files (no trailing spaces). One blank line after `class` and between methods.
3. **Naming:** `CamelCase` for public members; `_naming_` (snake_case with leading/trailing underscores) for private ones. Use lowercase for `__post_init__` arguments.
4. Typing: Use Self from typing_extensions for instance returns to maintain Python 3.10 compatibility. Use from __future__ import annotations as the first line only if required for forward references. Avoid using typing classes where built-in types suffice.
5. **Imports:** Organized in a sorted ladder-style block. Separate external and project (`Library.*`) imports with one blank line. Use **explicit imports** for internal library modules.
6. **Density:** Keep method bodies dense without internal blank lines (except complex `__init__`). Maintain standard spacing in signatures and assignments.
7. **Architecture:** Order methods by category (Connection → Disconnection → Business) and then by complexity (simplest first). Use `@staticmethod` for stateless logic and `InitVar` for temporary inputs.
8. **Dataframes:** Capitalize framework-level columns (e.g., "Date", "Security"). Prefer Polars (`pl`) for performance; use Pandas (`pd`) for compatibility.

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
- **`Library/App`**: Core Dash wrappers (`AppAPI`, `PageAPI`, `ComponentAPI`).
- **`Library/Bloomberg`**: Bloomberg API integration (Historical, Intraday, Reference, Streaming).
- **`Library/Database`**: Database abstraction layer supporting Oracle, Postgres, and SQL Server.
- **`Library/Dataclass`**: Data structures (`BarAPI`, `TickAPI`, `TradeAPI`, `SymbolAPI`).
- **`Library/Dataframe`**: Pandas/Polars/Numpy configuration and wrappers.
- **`Library/Formulas`**: Financial and utility formulas (`DateTime`, `Spot`, `Historical`).
- **`Library/Indicators`**: Python implementation of Trading Indicators.
- **`Library/Logging`**: Python logging handlers (Console, Telegram, File, Web).
- **`Library/Models`**: AI/ML Agents (`AgentAPI`, `DDPG`, `Network`, `Noise`, `Memory`).
- **`Library/Parameters`**: Configuration management and Broker-specific settings.
- **`Library/Robots`**: Python Trading Engine (System, Strategy, Analyst, Manager, Engine, Protocol).
- **`Library/Security`**: Security and Asset Class definitions.
- **`Library/Service`**: System services and background processes.
- **`Library/Statistics`**: Performance profiling and timing utilities.
- **`Library/Utility`**: Extensive helper library (IO, Path, HTML, DateTime, Typing, etc.).
- **`Library/Warehouse`**: Data storage and retrieval layer for market data.
- **`Library/Workflow`**: Business logic and frontend pages implementation.

### C# (`Sources/`)
- **`Sources/Robots`**: cTrader Robots (inherit `RobotAPI`). Bridge to Python via Pipes.
- **`Sources/Indicators`**: cTrader Indicators (inherit `IndicatorAPI`).
- **`Sources/Plugins`**: cTrader Plugins and Extensions.
- **`Sources/Logging`**: C# logging bridge.
- **`Sources/Export`**: Build artifacts and deployment exports.

### Testing (`Tests/`)
- **Naming**: Test files should be named following the pytest convention (e.g., `test_Query.py`).
- **Style:** Apply the exact same coding rules and density as the main codebase. Do not use docstrings. Keep methods dense.
