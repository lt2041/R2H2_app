# Release Notes — v1.2.8

## Update mechanism

- The in-app update action (Check for Updates) now queries the GitHub Releases API and upgrades via the appropriate package manager rather than always running `git pull`.
  - If the app is installed with **pipx**, it runs `pipx upgrade r2h2`.
  - If installed with plain **pip**, it installs directly from the tagged GitHub archive zip.
  - If a `.git` directory is present (developer / editable install), it falls back to `git pull` as before.
- The update response now reports the version transition (e.g. `Updated v1.2.7 → v1.2.8`) on success.
- The check compares version tuples so that patch and minor increments are detected correctly.
- Upgrade timeout increased from 60 s to 180 s to accommodate slower pip installs.
