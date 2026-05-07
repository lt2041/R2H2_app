#!/usr/bin/env python3

"""
R2H2 post-install setup: ensures the `r2h2` console-script installed by pip
is reachable on the user's PATH.

When pip installs this package it creates a `r2h2` script in the environment's
scripts directory (e.g. ~/.local/bin or <venv>/bin).  This helper finds that
directory and wires it into the user's shell config so it is available in every
new terminal session.

Run with:  r2h2-setup   (after pip install)
       or:  python -m setup_launcher
"""

import os
import sys
import shutil
import sysconfig
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scripts_dir() -> Path:
    """Return the directory where pip installs console-scripts for the active
    Python environment (works for venvs, user installs and system installs)."""
    return Path(sysconfig.get_path('scripts'))


def _r2h2_script() -> Path | None:
    """Return the absolute path of the installed `r2h2` script, or None."""
    # sysconfig scripts dir is the canonical location
    candidate = _scripts_dir() / ('r2h2.exe' if os.name == 'nt' else 'r2h2')
    if candidate.exists():
        return candidate
    # Fall back to shutil.which (covers edge cases like conda envs)
    found = shutil.which('r2h2')
    return Path(found) if found else None


def get_shell_config_file() -> Path:
    shell = os.environ.get('SHELL', '')
    if 'zsh' in shell:
        return Path.home() / '.zshrc'
    if 'bash' in shell:
        bp = Path.home() / '.bash_profile'
        return bp if bp.exists() or sys.platform == 'darwin' else Path.home() / '.bashrc'
    return Path.home() / '.profile'


def _ensure_path(directory: Path) -> bool:
    """Add *directory* to PATH in the user's shell config if not already there.
    Returns True if a change was made."""
    config = get_shell_config_file()
    dir_str = str(directory)
    if config.exists() and dir_str in config.read_text():
        return False  # already present
    with config.open('a') as fh:
        fh.write(f'\n# Added by r2h2-setup\nexport PATH="{dir_str}:$PATH"\n')
    return True


# ---------------------------------------------------------------------------
# Windows: write a .bat shim on the Desktop for double-click launching
# ---------------------------------------------------------------------------

def _setup_windows(script: Path) -> None:
    # Scripts-dir shim (for users who run from Anaconda Prompt / CMD)
    bat_dir = Path.home() / 'AppData' / 'Local' / 'bin'
    bat_dir.mkdir(parents=True, exist_ok=True)
    shim = bat_dir / 'r2h2.bat'
    shim.write_text(f'@echo off\n"{script}" %*\n')
    print(f'  Shim : {shim}')

    # Desktop shortcut — most reliable way to launch without PATH setup
    desktop = Path.home() / 'Desktop'
    if not desktop.exists():
        # OneDrive-redirected Desktop
        desktop = Path.home() / 'OneDrive' / 'Desktop'
    shortcut = desktop / 'Launch R2H2.bat'
    shortcut.write_text(
        f'@echo off\ntitle R2H2\n"{script}"\npause\n'
    )
    print(f'  Desktop shortcut: {shortcut}')
    print()
    print('  Double-click "Launch R2H2.bat" on your Desktop to start the app.')
    print(f'  Or add {bat_dir} to your PATH to use the "r2h2" command.')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print('=== R2H2 Launcher Setup ===')

    script = _r2h2_script()
    if script is None:
        print(
            '✗  Could not find the installed `r2h2` script.\n'
            '   Make sure the package was installed correctly:\n'
            '     pip install r2h2\n'
            '   or, inside a venv:\n'
            '     pip install -e /path/to/R2H2_app'
        )
        sys.exit(1)

    print(f'  Found r2h2 at: {script}')
    scripts_dir = script.parent

    if os.name == 'nt':
        _setup_windows(script)
        return

    # Unix / macOS ────────────────────────────────────────────────────────
    # Check whether the scripts dir is already on PATH
    path_dirs = [Path(p) for p in os.environ.get('PATH', '').split(':') if p]
    already_on_path = scripts_dir in path_dirs or shutil.which('r2h2') == str(script)

    if already_on_path:
        print(f'✓  {scripts_dir} is already on PATH — nothing to do.')
        print('   Run:  r2h2')
        return

    changed = _ensure_path(scripts_dir)
    config = get_shell_config_file()

    if changed:
        print(f'✓  Added {scripts_dir} to PATH in {config}')
    else:
        print(f'  (PATH entry already present in {config})')

    print(f'\nTo apply in this session:\n  source {config}')
    print('Then run:  r2h2')


if __name__ == '__main__':
    main()
