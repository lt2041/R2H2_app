# R2H2_app

The Desktop App for R2H2.

## Installation


### Prerequisites
- Python 3.11+

### Standard install:

Run the following in your terminal:
```bash
pip install git+https://github.com/RenewableTools/R2H2_app.git
```

Close your terminal, then run the following:
```bash
r2h2
```

You may be prompted to specify where you want to save data for the application on your local system. Once your app is configured, you shouldn't need to specify this again.


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