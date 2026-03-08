# R2H2_app

The Desktop App for R2H2.

## Installation


### Prerequisites
- Python 3.11+

### Standard install:

Run the following in your terminal:
```bash
pip install git+https://github.com/your-org/R2H2_app.git
```

Close your terminal, then run the following:
```bash
r2h2
```

N.B. If you want to install a specific version of the package, use:

```bash
pip install git+https://github.com/your-org/R2H2_app.git@v1.0.0
```

### Installation for developers:

If you are planning to install this package in a developer capacity, you can navigate to the local directory you plan to clone to, and type:

```bash
# Clone the repository
git clone https://github.com/your-org/R2H2_app.git

# Install in editable mode from local clone
cd R2H2_app
pip install -e .
```

If you are carrying out any analytical/experimental work specific to your own case studies (using ad-hoc Python scripts or notebooks), you should plan to do this **outside** the `R2H2_app` source code folder. The package is built as a generic tool and should not contain any data or hard-coded variables relating to case studies; place this in the level above (`cd ..`), an adjacent directly, or some other location on your local system.

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