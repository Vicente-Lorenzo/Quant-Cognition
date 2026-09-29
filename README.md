# 📈 Quant System Setup Guide (Windows Native Edition)

## 💻 Hardware Specs
- **CPU:** Intel i9-14900K (AMD64)
- **RAM:** 64GB DDR5 @ 6000MHz
- **Storage:** Samsung 990 Pro 1TB (NVMe)
- **GPU:** RTX 3060 Ti (CUDA enabled)

## 🔁 Rebuilding This Machine From Scratch
Everything the machine needs is in this repository or created by it; nothing is configured by hand outside this list. In order:

1. **Windows** — Step 2 (no WSL, no Docker). The IDEs of Step 1 are optional.
2. **Miniforge** (Step 3) — install for all users (`C:\ProgramData\miniforge3`). Its **base** Python runs the logon launcher with the standard library only: never install packages into base.
3. **The repository** — clone it to `C:\Users\<you>\OneDrive\Documents\cAlgo` (cTrader requires `Documents\cAlgo`).
4. **The `Quant` environment** — from a base prompt, in the repository:
   ```powershell
   mamba env create -n Quant -f Quant.yml
   conda run -n Quant python -m pytest Tests/ --ignore=Tests/Bloomberg
   ```
   `Future` and `Exotics` are optional (`python Script\Python\Conda.py`).
5. **PostgreSQL 18 + TimescaleDB** (Steps 4 and 5). The drivers connect to `localhost:5432` with the defaults in `Library/Database/Postgres/Postgres.py`; the installer creates the databases and every schema.
6. **Install** — provisions every schema, seeds the administrator, registers the four workflows and creates the logon task:
   ```powershell
   conda run -n Quant python -m Script.Install --boot
   ```
   The logon task is **`Quant Scheduler`**: at logon, as you, with highest privileges, it runs `"<Miniforge>\pythonw.exe" "<repository>\Script\Scheduler.py"`. It is defined in code (`Script/Install.py`, `schedule_orchestrator`), so `conda run -n Quant python -m Script.Install --register --boot` re-creates it at any time — nothing to export or back up.
7. **Cloudflare tunnel** — install `cloudflared`, run `cloudflared tunnel login`, and put the tunnel `Quant` in `%USERPROFILE%\.cloudflared\config.yml` with its credentials JSON beside it (Step 7): restore both from a backup, or create a new tunnel and point the `quantcognition.com` DNS record at it.
8. **Credentials** — sign cTrader in once: `conda run -n Quant python -m Script.Setup.Spotware` (browser consent; the Spotware application's client id and secret come from openapi.ctrader.com). Everything else goes in through the Credential page or `python -m Library.Credential.Main`.
9. **cTrader** — install it, open `Sources/Robots/Connector` and build the Connector with cTrader's own Build button (`RULES.md`, "C# Build").
10. **Start** — log off and on, or `schtasks /Run /TN "Quant Scheduler"`. The launcher writes `%LOCALAPPDATA%\cAlgo\Temp\Logs\Launcher.log`; the site is up within seconds and the Scheduler page lists `Setup`, `Environment`, `Web Application` and `Data Intelligence`.
11. **Market data** — the tick tape comes back from the data services' backfill (`PLAN.md`, Phase 5), or from a `Market.Tick` dump.

**How the environment stays current afterwards:** at 04:00, `Environment.Update` builds `envs\Quant.next` from `Quant.yml` when anything newer exists and runs the suite on it; at the next logon, before anything starts, the launcher swaps it in (`Quant` becomes `Quant.previous`) — or leaves everything as it is when the suite failed. To roll back by hand: quit the Scheduler from its tray icon, rename `envs\Quant.previous` back to `envs\Quant`, and start it again.

## 🛠️ Step 1: Core Software Installation (IDEs)
Install the JetBrains suite (using the JetBrains Toolbox is recommended) as these will be your primary development tools.

### 1.1 IDE Setup
1. **PyCharm Professional:** For the Python backend, AI modeling, and backtesting systems. Ensure the interpreter is set to the local Conda environment once created.
2. **JetBrains Rider:** For C# development (`Sources/`) and compiling legacy cTrader Robots/Indicators.
3. **DataGrip:** For database management, querying, tuning, and verifying schemas.

### 1.2 Force IDEs to Run as Administrator
To ensure your trading scripts and database connections have unrestricted network and file access:
1. Locate the executable or shortcut for each IDE (PyCharm, Rider, DataGrip).
2. Right-click the icon and select **Properties**.
3. Go to the **Compatibility** tab.
4. Check the box that says **"Run this program as an administrator"**.
5. Click **Apply** and **OK**.

### 1.3 Increase PyCharm Memory (Prevent AI Crashes)
To prevent Gemini Code Assist and indexing from crashing PyCharm, increase the Java Heap size to utilize your 64GB of RAM:
1. Open PyCharm.
2. Go to **Help > Change Memory Settings**.
3. Change the Maximum Heap Size to `8192` MB (8 GB).
4. Click **Save and Restart**.

## ⚙️ Step 2: System Preparation (Clean Windows Environment)
To ensure maximum native performance and avoid virtualization overhead, this setup explicitly avoids WSL and Docker.
1. **Uninstall WSL and Docker:** Ensure Windows Subsystem for Linux and Docker Desktop are completely removed from the system.
2. **Disable Virtualization Features:**
   - Press `Win + R`, type `optionalfeatures.exe`, and press Enter.
   - Uncheck **Windows Subsystem for Linux** and **Virtual Machine Platform**.
   - Restart the computer.
3. **Clear Resource Limits:** Ensure any `.wslconfig` files in `C:\Users\<YourUsername>\` are deleted to release all 64GB of RAM back to Windows.

## 🐍 Step 3: Python Environment Setup
We use Miniforge to handle the environment creation, as it includes the Mamba solver natively and prioritizes the `conda-forge` channel for optimized Windows binaries.
1. **Install Miniforge:** Download and install the [Miniforge3 Windows Installer](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe).
2. **Initialize Shell:** Open the **Miniforge Prompt** from the Start Menu and run:
   ```powershell
   mamba init powershell
   mamba init cmd.exe
3. Restart Terminal: Close the Miniforge Prompt and open your standard PowerShell.
4. Create the Project Environment: Navigate to your project directory and run:
   ```powerShell
   cd C:\Users\Admin\OneDrive\Documents\cAlgo
   mamba env create --file Quant.yml
   mamba env create --file Future.yml
## 🗄️ Step 4: Native QuantDB Setup (PostgreSQL 18 + TimescaleDB)
1. Install PostgreSQL: Download and install the PostgreSQL 18 MSI for Windows.
2. Install TimescaleDB: Download the TimescaleDB Windows binaries, extract them, and run setup.exe to attach the extension to your native PostgreSQL installation.

## ⚡ Step 5: Database Hardware Auto-Tuning
1. Instead of hardcoding memory limits, use Timescale's built-in tuning utility to analyze your i9-14900K and 64GB of RAM.
2. Open PowerShell as Administrator and navigate to your Timescale download folder.
3. Run the tuning tool, pointing it to your PG 18 installation:
   ```powerShell
   .\timescaledb-tune.exe --pg-version=18 --conf-path="C:\Program Files\PostgreSQL\18\data\postgresql.conf"
4. Type y to accept the recommended changes for shared_buffers, worker processes, and memory limits.
5. Restart the PostgreSQL service in Windows (services.msc) to apply the changes.

## 🌉 Step 6: cTrader Integration
1. Since both the Python backend and cTrader are running natively on Windows, complex bridging is no longer required.
2. Direct Communication: Use standard Localhost TCP (127.0.0.1) or Windows Named Pipes directly within your Python scripts to communicate with cTrader.
3. Native Python in cTrader: If using cTrader 5.4 or later, you can leverage their native Python integration to run algorithms directly without an external bridge.

## 🌐 Step 7: Production Web Deployment (Cloudflare Tunnel)
The **Quant Cognition** web app (Dash, `Library/Web`) is published to the public internet at **https://quantcognition.com** with no open inbound ports — a Cloudflare Tunnel dials out from this machine, and Cloudflare's edge terminates TLS.

**Topology:** `Browser → https://quantcognition.com → Cloudflare edge → cloudflared tunnel (Quant) → http://127.0.0.1:8050 → waitress → Dash app`

### 7.1 Components
- **App server (`Web.Server` task → `Script/Web/Server.py` → `Library/Web/Service/Tray.py`):** runs a **waitress** WSGI server binding the app to `127.0.0.1:8050` (loopback only — never exposed directly). Supervised always-on by the orchestrator (Step 8). `Tray.py` runs the server in-process behind a system-tray menu and falls back to headless `Service/Serve.py` if the tray cannot start; `python -m Library.Web.App` is the dev/`debug` entry point.
- **Tunnel (`Web.Tunnel` task → `Script/Web/Tunnel.py`):** runs `cloudflared --config ~/.cloudflared/config.yml tunnel run Quant`. The named tunnel **`Quant`** (`config.yml` → `ingress: quantcognition.com → http://127.0.0.1:8050`, fallback `http_status:404`) authenticates with its credentials JSON in `~/.cloudflared`. The Cloudflare dashboard holds the DNS record routing `quantcognition.com` to this tunnel.
- **Auth:** the app is **private** (`access="Viewer"`) — unauthenticated visitors land on `/login`. Roles/pages are enforced server-side (see `Library/Auth`); seed/manage the admin account with `python -m Setup.Auth`. Cookies are `Secure` by default (TLS at the edge + `ProxyFix`); pass `AuthAPI(secure=False)` only for non-localhost `http` development. The session secret is generated per process (restart ⇒ re-login); pass `AuthAPI(secret=...)` if you want a stable one.

### 7.2 Auto-Start on Boot
The app and tunnel are the **`Web`** ("Web Application") workflow's two `Service` tasks (`Web.Server` / `Web.Tunnel`), supervised by the single **`Quant Scheduler`** orchestrator (Step 8) — there are no longer separate `Quant Cognition` / `Cloudflare Tunnel` startup tasks. The orchestrator runs at logon as the user (not SYSTEM — the tunnel config lives in the user profile), **silently in the system tray** (§8.1), and brings the site up within a few seconds. Each day the workflow's `Web.Version` check runs first and the tunnel and app wait for it — a few seconds. Do **not** install `cloudflared` as a Windows *service* (it runs as LocalSystem and cannot read the user-profile tunnel config).

### 7.3 Manual Control
Manage the app + tunnel through the orchestrator's `Web` Service tasks — via the Scheduler UI or the CLI:
```powershell
python -m Library.Scheduler.Main task disable --uid Web.Tunnel   # stop supervising the tunnel
python -m Library.Scheduler.Main task enable  --uid Web.Tunnel   # resume (orchestrator respawns it)
cloudflared tunnel list                                                  # inspect tunnels + live connections
```

## ⏱️ Step 8: Job Orchestration (Quant Scheduler)
The **Quant Scheduler** (`Library/Scheduler`) replaces Windows Task Scheduler for recurring jobs with a single boot daemon that owns all scheduling. Provision the `Scheduler` schema once with `python -m Setup.Scheduler` (idempotent — creates the schema, adds the `Auth` name/`Team`/`Office` columns, and migrates the Scheduler tables in FK order).

**Model:** a **Task** is a `.bat`/`.sh`/`.py` artifact with a cron `Schedule`; each execution produces an auditable **Run** (status, duration, peak memory, exit code). Tasks are `Scheduled` (cron → run once) or `Service` (always-on, respawned on exit). Optional human gates: **Approval** on a passing run (exit 0), **Review** on a crashed run (exit ≠ 0) — Accept → Success, Reject → Failure. **Retry:** a crash retries up to `MaxRetry` with a `RetryDelay` between attempts before Review/Failure. **Workflows** chain Tasks into a DAG (`WorkflowAPI` cron `Schedule`; a step fires only when every predecessor succeeded — a pending gate blocks all downstream). **Maintenance:** a `Service` task waits for the `Scheduled` tasks upstream of it in its workflow's DAG — while one of them has not yet run in the open cycle, the service is suspended (process-tree terminate) and relaunched after. **Workflows after workflows:** a workflow may name another as `After`; its cycles then open **Waiting** while the upstream runs and its services start only once it finishes (Scheduler page, or `workflow update --uid X --after Y`). **Self-healing:** each run heartbeats; a runner killed mid-run (or a machine reboot) is detected via a stale heartbeat lease and re-dispatched/failed per the retry/review policy.

### 8.1 Components
- **Daemon (`Script/Scheduler.py` → `Library.Scheduler.Tray`):** a single-threaded control loop that evaluates cron schedules (`croniter`) and **spawns a separate `Runner` process per run** (never threads), isolating each job. It supervises `Service` tasks (respawn on death, suspend during a workflow's maintenance run), reaps dead runs, re-dispatches retries, advances workflow DAGs (including manual, no-schedule workflows once launched), and caps concurrent active runs. At boot it runs **silently under `pythonw`** inside a **system-tray app** (`pystray`): the daemon loops on a background thread while the tray icon sits by the clock (next to OneDrive/NVIDIA). Its stdout is redirected to `Logs/Scheduler.log`; **left-click the icon (or right-click → Terminal)** opens a live console tailing that log, **Open Dashboard** launches the site, **Quit** stops the daemon and its services. If `pystray` is unavailable the launcher falls back to headless so the site still comes up. Headless-only entry: `python -m Library.Scheduler.Serve`.
- **Runner (`python -m Library.Scheduler.Runner <TID>`):** the per-run entry point; executes one Task's artifact as a child process, samples peak RSS via `psutil`, drives the Run state machine, and records the Run.
- **CLI (`python -m Library.Scheduler.Main`):** full terminal control — `task`/`workflow`/`run` subcommands (`create`/`update`/`delete`/`list`/`show`/`enable`/`disable`/`run`, `workflow link`/`unlink`, `run approve`/`reject`) plus `serve`. Backed by `ManagerAPI`, the single operations layer the web UI also calls, so everything is doable from the terminal without the UI. Example: `python -m Library.Scheduler.Main task create --uid daily-download --name Download --owner <owner-email> --type Python --path Library/Indicator/Fundamental/Calendar.py --schedule "0 22 * * 1-5"`.

### 8.2 Auto-Start on Boot (cutover from Task Scheduler)
End state: the **only** Windows startup task is `Quant Scheduler`; everything else is a Task it manages. The legacy `Quant Cognition` / `Cloudflare Tunnel` / `Python Environment Updater` startup tasks have been **deleted** — the orchestrator supervises the app, tunnel, and environment refresh from the standard workflows (§8.3).
| Task | Trigger | Runs |
| --- | --- | --- |
| `Quant Scheduler` | At logon | `"<base pythonw>" Script\Scheduler.py` — the launcher: applies a validated `Quant.next`, starts the tray daemon from `Quant`, exits |

### 8.3 The orchestrator model & standard workflows
Windows Task Scheduler runs exactly **one** thing: the **master orchestrator** (`Script\Scheduler.py` → `python -m Library.Scheduler.Serve`). Once running, the daemon launches everything else as **Scheduler workflows** — it supervises `Service` tasks always-on, cron-launches scheduled workflows, and advances manual workflows once triggered. All workflows and tasks are owned by the real administrator account. The three standard workflows (all registered by `python -m Setup.Install`):

| Workflow | Schedule | Tasks | The daemon… |
| --- | --- | --- | --- |
| **`Setup`** | none | 7 DB-provisioning tasks (`Scheduled`) | never auto-launches — **run manually** (UI Run button or `Library.Scheduler.Main workflow run --uid Setup`) |
| **`Environment`** | `0 4 * * *` | `Environment.Update` (builds and validates `Quant.next` when anything newer exists — applied at the next logon) → `Environment.Cache` (cache cleanup) → `Environment.Retention` (prunes logs past the 30-day horizon) | never touches the running environment |
| **`Web`** (Web Application) | `0 4 * * *` | `Web.Version` (reports newer vendored frontend releases) → `Web.Tunnel` → `Web.Server` (both `Service`) | keeps the tunnel + app always-on |
| **`Data`** (Data Intelligence) | `0 6 * * *` | `Data.Credential` (refreshes the data services' tokens) → `Data.Calendar` (economic calendar; every data service joins here) | fresh-launches daily |

**New machine, from scratch** — the full checklist is *Rebuilding This Machine From Scratch* at the top; the Scheduler part of it:
1. **`conda run -n Quant python -m Script.Install --boot`** — creates + populates every schema, seeds the administrator, registers the four workflows, and schedules the orchestrator (`Quant Scheduler`) at logon in Windows Task Scheduler (the boot task runs base Python's `pythonw` on the launcher `Script\Scheduler.py`). Drop `--boot` to skip the Task-Scheduler step and register it yourself.
2. **Launch the orchestrator** (log off and on, or `schtasks /Run /TN "Quant Scheduler"`). It boot-launches the `Web` workflow — the version check, then tunnel + web app in strict order.
3. **Open the app → Scheduler.** The three workflows are listed and the DB is already populated. Run `Setup` from the UI whenever you need to re-provision.

`Setup.Install` provisions **in-process** (no daemon needed) so the DB is fully populated *before* the orchestrator launches. The `Setup` workflow is that same provisioning exposed as a re-runnable, UI-visible DAG — a manual DAG of idempotent Python tasks (`Enums` · `Auth`→`Scheduler` · `Universe`→(`Market`, `Portfolio`) · `Indicator`), each a `.py` with a uniform entry, RULES logging, and an exit code, so failures surface in the app's **Runs** section. **Env-free** — no `QUANT_*`; the admin password is generated on first seed and logged. These Python tasks, along with the essential helpers in `Script/` (`Scheduler` boot launcher · `System`/`Conda`/`UV` environment updaters · `Cache` cleanup), replace the old `Script/*.bat` files.

## 🚀 Daily Launch Sequence
1. Verify the postgresql service is running natively in Windows (set to Automatic start via services.msc).
2. Open PyCharm Professional (it will now start as Admin automatically) and verify the active interpreter is set to the Quant local environment.
3. Start cTrader and run your Python backend/DRL agents.
4. The public site (**https://quantcognition.com**) and its tunnel start automatically at boot (Step 7) — no action needed.