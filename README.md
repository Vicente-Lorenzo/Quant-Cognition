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

## 🚀 Daily Launch Sequence
1. Verify the postgresql service is running natively in Windows (set to Automatic start via services.msc).
2. Open PyCharm Professional (it will now start as Admin automatically) and verify the active interpreter is set to the Quant local environment.
3. Start cTrader and run your Python backend/DRL agents.