# R2H2

R2H2 is a desktop simulation tool for renewable hydrogen systems.

---

## Install

Requires **Python 3.11+**. The recommended install method is [`pipx`](https://pipx.pypa.io), which isolates the app in its own environment and puts the `r2h2` command on your PATH automatically.

As a prerequisite, you'll need `pip` and `pipx` installed. To make sure you can get started, paste the following into a terminal:

```
pip install pipx
pipx ensurepath
```

If your using a new system that doesn't currently have access to Git or PIP, you may need to install these first. For Ubuntu, these instructions are as follow:

```
sudo apt install git
sudo apt install pip
```

### 1 — Install as a general user (pipx)

```bash
pipx install git+https://github.com/RenewableTools/R2H2_app.git
```

Open a **new terminal**, then run:

```bash
r2h2
```

To update to the latest version at any time:

```bash
pipx upgrade r2h2
```

---

### 2 — Install for development (editable)

```bash
git clone https://github.com/RenewableTools/R2H2_app.git
cd R2H2_app
pipx install -e .
```

After editing source files the running app picks up changes immediately — no reinstall needed. Use `pipx upgrade r2h2` (pointing at the local path) or simply re-run `pipx install -e .` after pulling updates.

---

## Getting started

On first launch R2H2 will ask you to choose a local folder for your application data (database, wind files, outputs). The folder will be created if it does not exist. This path is stored in `config.yaml` and you will not be prompted again.

```bash
r2h2          # starts the local server and opens the app in your browser
```

Use **Ctrl+C** in the terminal to stop the server.

---

## Notes

- Application data (database, outputs) lives in the folder you chose at first launch — **not** inside the source code directory.
- The database schema is defined entirely by `dashboard/models.py`; use Django migrations (`python manage.py makemigrations && python manage.py migrate`) if you change it.
- A useful tool for inspecting the SQLite database: <https://sqlitebrowser.org>

## Documentation

- Dynamic controller guide: [docs/dynamic_controller_user_guide.md](docs/dynamic_controller_user_guide.md)

