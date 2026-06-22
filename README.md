# R2H2

R2H2 is a desktop simulation tool for renewable hydrogen systems.

---

## Install

Please ensure you have **Python 3.11+** to avoid any issues running this app. We highly recommended installing using [`pipx`](https://pipx.pypa.io), which isolates the app in its own environment and puts the `r2h2` command on your PATH automatically. Even if you habitually manage your own environments (as is best practice!), you'll find `pipx` extremely useful here, for launching the app and keeping it up-to-date, with minimal CLI instructions.

As a prerequisite, you'll need `pip` on your path (i.e. typing `pip` in your terminal/powershell returns a list of pip reference commands). 

Next, you should ensure that `pipx` is installed, by pasting the following into your terminal:

```
pip install pipx
pipx ensurepath
```

> [!WARNING]
> Please be sure to close and restart a fresh terminal before installing the app!

### 1 — Install R2H2

Paste the following into a fresh terminal:
```bash
pipx install r2h2
```

Once this finishes, type:

```bash
r2h2
```

The first time you use the app, you'll be asked where you want to save all the associated data (an SQlite database, and various files for storing wind data, and controller code). When prompted, type a location on your local system, in a directory that you have full access rights.  

We recommend checking for upgrades periodically; to do this type:

```bash
pipx upgrade r2h2
```

---


## Documentation

- Dynamic controller guide: [docs/dynamic_controller_user_guide.md](docs/dynamic_controller_user_guide.md)

