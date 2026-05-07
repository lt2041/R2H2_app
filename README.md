# R2H2_app

The Desktop App for R2H2.

## Quick Install

| Platform | Method | Command |
|---|---|---|
| **Any** (recommended) | `pipx` | `pipx install git+https://github.com/RenewableTools/R2H2_app.git` |
| **Any** | plain `pip` | `pip install git+https://github.com/RenewableTools/R2H2_app.git` |
| **Windows — Anaconda Prompt** | conda env | see [Windows (Conda)](#windows--anaconda--miniconda) below |
| **Windows — PyCharm Terminal** | pip | see [Windows (PyCharm)](#windows--pycharm) below |

After install, run `r2h2` to launch.  
If `r2h2` is not found, run `python -m setup_launcher` once to fix PATH.  
Windows: a **"Launch R2H2.bat"** shortcut is created on your Desktop automatically.

> First launch will prompt you for a data folder — it will be created if it doesn't exist.

---

### Windows — Anaconda / Miniconda

Open **Anaconda Prompt** from the Start menu and paste these lines one at a time:

```bat
conda create -n r2h2 python=3.11 -y
conda run -n r2h2 python -m pip install git+https://github.com/RenewableTools/R2H2_app.git
conda run -n r2h2 python -m setup_launcher
```

A **"Launch R2H2.bat"** shortcut will appear on your Desktop.  
To launch manually from Anaconda Prompt in future:

```bat
conda activate r2h2
r2h2
```

---

### Windows — PyCharm

Open PyCharm, then open the **Terminal** panel (`Alt+F12`) and paste:

```bat
python -m pip install git+https://github.com/RenewableTools/R2H2_app.git
python -m setup_launcher
```

A **"Launch R2H2.bat"** shortcut will appear on your Desktop.

---

## Installation

### Prerequisites
- Python 3.11+

---

### Recommended — install with `pipx` (handles PATH automatically)

[`pipx`](https://pipx.pypa.io) installs the app into an isolated environment and puts the `r2h2` command on your PATH automatically — no extra setup step needed.

```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath          # adds ~/.local/bin to PATH (one-time)

# Install R2H2
pipx install git+https://github.com/RenewableTools/R2H2_app.git
```

Open a new terminal, then run:

```bash
r2h2
```

---

### Alternative — plain `pip`

```bash
pip install git+https://github.com/RenewableTools/R2H2_app.git
```

If opening a new terminal and typing `r2h2` gives "command not found", run the setup helper once to add the correct directory to your PATH:

```bash
python -m setup_launcher
```

Then follow the instructions it prints (usually `source ~/.zshrc` or open a new terminal).

---

### Installing a specific version:

Run the following in install a specific version; this can be used to access older versions, for example, should there be any specific reason to do so. In general, the standard installation (above) is preferred.

```bash
pip install git+https://github.com/RenewableTools/R2H2_app.git@v1.1.0
```

... then follow the remaining steps 

### Installation for developers:

If you are planning to install this package in a developer capacity, you can navigate to the local directory you plan to clone to, and type:

```bash
# Clone the repository
git clone https://github.com/RenewableTools/R2H2_app.git

# Install in editable mode from local clone
cd R2H2_app
pip install -e .
```

If you are carrying out any analytical/experimental work specific to your own case studies (using ad-hoc Python scripts or notebooks), you should plan to do this **outside** the `R2H2_app` source code folder. The package is built as a generic tool and should not contain any data or hard-coded variables relating to case studies; place this in the level above (`cd ..`), an adjacent directly, or some other location on your local system.

> **Note for developers:**
> 
> The desktop tool relies on a database file called `R2H2_DataBase.sqlite3`; this should be saved at the location you specified when running the tool for the first time. If you plan to make adaptations to the database structure, the entire schema is defined by the Django-managed `dashboard/models.py` file. All changes should be made here; changes shouldn't be made directly to the database file.
> 
> The following 3rd-party tool may be useful for exploring any changes you make to the database schema: https://sqlitebrowser.org. Whilst you shouldn't change the database structure using this tool, you can safely edit data without affecting R2H2 at runtime.

**`config.yaml`**

Your `config.yaml` file is saved at one of the two locations below:

- Windows: `C:\Users\<username>\AppData\Local\r2h2\config.yaml`
- Unix: `/Users/<username>/Library/Application Support/r2h2/`

You can ignore this file, but may want to be aware that it to understand the launch process at runtime. Other data realting to the application (such as the database and case study data) shouldn't be saved here; rather, the `config.yaml` file stored here specifies where the user has chosen to save their application data.


---

---


### Features:

- **Cross-platform:** Works on Windows, macOS, and Linux
- **Smart path detection:** Uses r2h2.config or falls back to current directory
- **Virtual environment support:** Automatically detects and uses venv
- **Dependency checking:** Verifies Django and r2h2 are installed
- **Port checking:** Ensures port availability
- **Auto-migration:** Runs database migrations automatically
- **Browser integration:** Opens app in default browser
- **Graceful shutdown:** Handles Ctrl+C properly
- **Colored output:** User-friendly terminal messages

This Python-based launcher provides the same functionality as the shell scripts but with better cross-platform compatibility and Python integration.