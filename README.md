# 📈 Quant System Setup Guide (Windows Native Edition)

## 💻 Hardware Specs
- **CPU:** Intel i9-14900K (AMD64)
- **RAM:** 64GB DDR5 @ 6000MHz
- **Storage:** Samsung 990 Pro 1TB (NVMe)
- **GPU:** RTX 3060 Ti (CUDA enabled)

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
- **App server (`Scripts/Quant.bat`):** runs `python -m Library.Web.Serve`, a **waitress** WSGI server binding the app to `127.0.0.1:8050` (loopback only — never exposed directly). `Library/Web/Serve.py` is the production entry point; `python -m Library.Web.App` is the dev/`debug` entry point.
- **Tunnel (`Scripts/Tunnel.bat`):** runs `cloudflared --config C:\Users\Admin\.cloudflared\config.yml tunnel run Quant`. The named tunnel **`Quant`** (`config.yml` → `ingress: quantcognition.com → http://127.0.0.1:8050`, fallback `http_status:404`) authenticates with its credentials JSON in `~/.cloudflared`. The Cloudflare dashboard holds the DNS record routing `quantcognition.com` to this tunnel.
- **Auth:** the app is **private** (`access="Viewer"`) — unauthenticated visitors land on `/login`. Roles/pages are enforced server-side (see `Library/Auth`); seed/manage the admin account with `python -m Setup.Auth`. Cookies are `Secure` by default (TLS at the edge + `ProxyFix`); pass `AuthAPI(secure=False)` only for non-localhost `http` development. The session secret is generated per process (restart ⇒ re-login); pass `AuthAPI(secret=...)` if you want a stable one.

### 7.2 Auto-Start on Boot
Two **Task Scheduler** tasks run at system startup as user `Admin` (not SYSTEM — the tunnel config lives in the user profile):
| Task | Trigger | Runs |
| --- | --- | --- |
| `Quant Cognition` | At boot | `Scripts\Quant.bat` |
| `Cloudflare Tunnel` | At boot | `Scripts\Tunnel.bat` |

After a reboot the site is live within a few seconds — no manual steps. Do **not** install `cloudflared` as a Windows *service* (it runs as LocalSystem and cannot read the user-profile tunnel config).

### 7.3 Manual Control
```powershell
Start-ScheduledTask -TaskName "Quant Cognition"    # start app
Start-ScheduledTask -TaskName "Cloudflare Tunnel"   # start tunnel
Stop-ScheduledTask  -TaskName "Cloudflare Tunnel"   # take the site offline
cloudflared tunnel list                             # inspect tunnels + live connections
```

## ⏱️ Step 8: Job Orchestration (Quant Scheduler)
The **Quant Scheduler** (`Library/Scheduler`) replaces Windows Task Scheduler for recurring jobs with a single boot daemon that owns all scheduling. Provision the `Scheduler` schema once with `python -m Setup.Scheduler` (idempotent — creates the schema, adds the `Auth` name/`Team`/`Office` columns, and migrates the Scheduler tables in FK order).

**Model:** a **Task** is a `.bat`/`.sh`/`.py` artifact with a cron `Schedule`; each execution produces an auditable **Run** (status, duration, peak memory, exit code). Tasks are `Scheduled` (cron → run once) or `Service` (always-on, respawned on exit). Optional human gates: **Approval** on a passing run (exit 0), **Review** on a crashed run (exit ≠ 0) — Accept → Success, Reject → Failure. **Retry:** a crash retries up to `MaxAttempts` with a `RetryDelay` between attempts before Review/Failure. **Workflows** chain Tasks into a DAG (`WorkflowAPI` cron `Schedule`; a step fires only when every predecessor succeeded — a pending gate blocks all downstream). **Self-healing:** each run heartbeats; a runner killed mid-run (or a machine reboot) is detected via a stale heartbeat lease and re-dispatched/failed per the retry/review policy.

### 8.1 Components
- **Daemon (`Scripts/Scheduler.bat`):** runs `python -m Library.Scheduler.Serve` — a single-threaded control loop that evaluates cron schedules (`croniter`) and **spawns a separate `Runner` process per run** (never threads), isolating each job. It supervises `Service` tasks (respawn on death), reaps dead runs, re-dispatches retries, advances workflow DAGs, and caps concurrent active runs.
- **Runner (`python -m Library.Scheduler.Runner <TID>`):** the per-run entry point; executes one Task's artifact as a child process, samples peak RSS via `psutil`, drives the Run state machine, and records the Run.
- **CLI (`python -m Library.Scheduler.Main`):** full terminal control — `task`/`workflow`/`run` subcommands (`create`/`update`/`delete`/`list`/`show`/`enable`/`disable`/`run`, `workflow link`/`unlink`, `run approve`/`reject`) plus `serve`. Backed by `ManagerAPI`, the single operations layer the web UI also calls, so everything is doable from the terminal without the UI. Example: `python -m Library.Scheduler.Main task create --uid daily-download --name Download --owner me --type Batch --path Scripts/System.bat --schedule "0 22 * * 1-5"`.

### 8.2 Auto-Start on Boot (cutover from Task Scheduler)
End state: the **only** Windows startup task is `Quant Scheduler`; everything else becomes a Task it manages.
| Task | Trigger | Runs |
| --- | --- | --- |
| `Quant Scheduler` | At boot | `Scripts\Scheduler.bat` |

Migrate the existing jobs into it — `System.bat`/`Calendar.bat` as `Scheduled` Tasks, `Quant.bat` (app) / `Tunnel.bat` as `Service` Tasks — then disable the old `Quant Cognition` / `Cloudflare Tunnel` boot tasks once supervision is verified. Until then the Step-7 boot tasks are left untouched (working prod deployment); the cutover is deliberate, not automatic.

## 🚀 Daily Launch Sequence
1. Verify the postgresql service is running natively in Windows (set to Automatic start via services.msc).
2. Open PyCharm Professional (it will now start as Admin automatically) and verify the active interpreter is set to the Quant local environment.
3. Start cTrader and run your Python backend/DRL agents.
4. The public site (**https://quantcognition.com**) and its tunnel start automatically at boot (Step 7) — no action needed.