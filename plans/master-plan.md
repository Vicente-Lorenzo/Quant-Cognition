# Master Plan: Core Wrappers Refactor

## ~~Phase 1: Market Sub-Plan (Database Alignment & Unified Series)~~ [COMPLETED]
- Database structure mapped directly to `TickAPI` and `BarAPI` using Foreign Keys and `.ID`/`.OID`.
- Replaced `TickSeriesAPI` with a highly recursive `SeriesAPI`.
- Eliminated circular imports, fixed IDE warnings, and achieved full test parity.

## ~~Phase 2: Indicator Sub-Plan (Scalable Info Analysis)~~ [COMPLETED]
- Dropped all external TA-lib dependencies.
- Implemented modular directory structure: e.g., `Technical/Baseline/SMA.py` and `Technical/Momentum/MACD.py`.
- Established `TechnicalAPI`, `FundamentalAPI`, and `SentimentalAPI` that act directly as containers in `Protocol/Update.py` (flattened structure, dropped `IndicatorAPI` and `ContainerAPI`).
- All technical indicators use `SeriesAPI` for granular attribute-based access (e.g., `Update.Technical.MACD.Signal.last()`).
- **High-Performance Streaming**: Implemented incremental calculation formulas for SMA and MACD (O(1) execution instead of O(N)).
- **Safety**: Built-in `None` padding for insufficient window data to prevent live trading anomalies.
- Verified architecture with a new `Tests/Indicator/` test suite ensuring dual-mode (batch/stream) consistency.

## Phase 3: Portfolio Sub-Plan
*Objective: Establish exact symmetry between Backtesting and Live trading states for portfolio management.*

**1. Sizing & Statistics Extraction**
- Extract sizing logic into a standalone `SizingAPI`.
- Refactor statistics into a pure, static `StatisticsAPI` that can be applied to both backtesting deal frames and live execution logs.

**2. Symmetric Data Structures**
- Ensure `AccountAPI`, `PositionAPI`, `OrderAPI`, and `TradeAPI` operate identically regardless of the execution provider.
- Implement unified serialization (`.dict()`) for all portfolio components.

**3. Execution & Strategy Integration**
- Refactor the `Manager` module to use the new symmetric structures.
- Streamline the `Portfolio` update logic within the Protocol sequencing (`Market` -> `Technical` -> `Portfolio`).

**4. Performance Optimization**
- Optimize position tracking using vectorized operations where possible.
- Ensure O(1) lookups for active positions and orders.