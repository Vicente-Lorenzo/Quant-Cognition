# Schedule Project - Implementation Plan

This document outlines the architecture for the `Schedule` project, a custom task orchestrator (Prefect-style) integrated into the Quant Trading Framework.

---

## 1. Schema: `Schedule` (Database Design)

### Core Tables

#### `Workflow`
Defines the high-level grouping of automated processes.
- **UID**: UUID (Primary Key)
- **Name**: String (Unique)
- **Owner**: String
- **Description**: Text
- **UpdatedAt**: Timestamp
- **UpdatedBy**: String

#### `Task`
Atomic units of work defined by Python scripts.
- **UID**: UUID (Primary Key)
- **Name**: String
- **Owner**: String
- **Description**: Text
- **Python**: Path (Path to the execution script)
- **Schedule**: String (Cron expression)
- **UpdatedAt**: Timestamp
- **UpdatedBy**: String

#### `Run`
Execution instances for individual tasks.
- **UID**: UUID (Primary Key)
- **TID**: UUID (Foreign Key -> `Task.UID`)
- **Status**: Enum (Resting, Waiting, Approving, Running, Reviewing, Success, Failure)
- **StartedAt**: Timestamp
- **StartedBy**: String (System or User ID)
- **StoppedAt**: Timestamp
- **StoppedBy**: String
- **Duration**: Interval (Computed: StoppedAt - StartedAt)
- **Memory**: Float (Peak memory usage in MB)
- **Message**: Text (Error message or success summary)

### Proposed Missing Tables

To support the transition logic (specifically `Waiting`) and complex orchestrations, the following are required:

#### `WorkflowTask` (Mapping)
Links tasks to workflows and defines execution order.
- **WID**: UUID (Foreign Key -> `Workflow.UID`)
- **TID**: UUID (Foreign Key -> `Task.UID`)
- **Sequence**: Integer (Order within the workflow)
- **AutoApprove**: Boolean (Default: True)

#### `Dependency` (Task Graph)
Explicitly defines which tasks must finish before others start.
- **TaskID**: UUID (The dependent task)
- **DependsOn**: UUID (The prerequisite task)
- **Type**: Enum (Finish-to-Start, Success-to-Start)

#### `Parameter`
Dynamic inputs for runs (e.g., date ranges, ticker symbols).
- **RunID**: UUID (Foreign Key -> `Run.UID`)
- **Payload**: JSONB (Key-value pairs for the Python script)

---

## 2. Transition Logic (Status Machine)

The orchestrator transitions tasks through these states:

| Status | Definition | Trigger / Condition |
| :--- | :--- | :--- |
| **1. Resting** | Idle state. | Schedule (Cron) has not yet been matched. |
| **2. Waiting** | Queue state. | Schedule matched, but prerequisites in `Dependency` are incomplete. |
| **3. Approving** | Pre-run gate. | Prerequisites met. Waiting for `AutoApprove` or manual user intervention. |
| **4. Running** | Active state. | Accepted to start; Python process is spawned and monitored. |
| **5. Reviewing** | Post-run gate. | Finished with success but requires manual sign-off before downstream tasks. |
| **6. Success** | Terminal (Good). | Transitioned from `Reviewing` (Approved) or `Approving` (Skipped). |
| **7. Failure** | Terminal (Bad). | Transitioned from `Running` (Crash), `Reviewing` (Rejected), or `Approving` (Aborted). |

---

## 3. Implementation Phases

- [ ] **Phase 1: Database Migration**
  - Create the `Schedule` schema in PostgreSQL.
  - Implement the `ScheduleDatabaseAPI` in `Library/Database/`.
- [ ] **Phase 2: Core Orchestrator**
  - Implement a `SchedulerService` that monitors Cron expressions.
  - Implement a `WorkerService` that executes Python scripts via subprocesses.
- [ ] **Phase 3: Transition Engine**
  - Logic to resolve `Dependency` trees and update `Run` status.
- [ ] **Phase 4: Dash Dashboard**
  - Visualize current `Run` statuses and manual `Approving`/`Reviewing` buttons.
