#!/usr/bin/env python3
"""
R2H2 Desktop App Launcher
Python-based launcher for the R2H2 Django application
"""

import os
import sys
import time
import socket
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path


# ── Terminal colours (disabled on Windows if no ANSI support) ──────────────
class Colors:
    if sys.platform == 'win32':
        # Enable ANSI on Windows 10+
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    GREEN  = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED    = '\033[0;31m'
    CYAN   = '\033[0;36m'
    NC     = '\033[0m'


def print_colored(message, color=Colors.NC):
    print(f"{color}{message}{Colors.NC}", flush=True)


# ── Port utilities ──────────────────────────────────────────────────────────
def is_port_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) != 0


def find_available_port(start_port=8030, max_attempts=50):
    for port in range(start_port, start_port + max_attempts):
        if is_port_available('127.0.0.1', port):
            return port
    raise RuntimeError(f"No available port found in range {start_port}–{start_port + max_attempts}")


def kill_process_on_port(port):
    """Cross-platform: kill whatever is listening on *port*."""
    try:
        if sys.platform == 'win32':
            # netstat -ano | findstr :<port>  then taskkill
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(['taskkill', '/F', '/PID', pid],
                                   capture_output=True)
                    return True
        else:
            result = subprocess.run(
                ['lsof', '-ti', f'tcp:{port}'],
                capture_output=True, text=True
            )
            pid = result.stdout.strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                return True
    except Exception as e:
        print_colored(f"  Could not kill process on port {port}: {e}", Colors.YELLOW)
    return False


# ── Project / venv resolution ───────────────────────────────────────────────
def get_project_directory():
    """Return the directory containing manage.py."""
    # When installed as a package, manage.py lives next to launch_r2h2.py
    here = Path(__file__).resolve().parent
    if (here / 'manage.py').exists():
        return here
    # Fallback: cwd
    cwd = Path.cwd()
    if (cwd / 'manage.py').exists():
        return cwd
    print_colored("✗ Cannot locate manage.py", Colors.RED)
    sys.exit(1)


def get_python_executable(project_dir: Path):
    """
    Return the best Python executable to use:
    1. The venv inside the project directory (venv / .venv)
    2. The currently running interpreter (handles pipx / pip install)
    """
    for venv_name in ('venv', '.venv', 'env', '.env'):
        venv = project_dir / venv_name
        if sys.platform == 'win32':
            candidate = venv / 'Scripts' / 'python.exe'
        else:
            candidate = venv / 'bin' / 'python'
        if candidate.exists():
            return candidate

    # Already inside a venv (pipx, pip install --user, etc.)
    return Path(sys.executable)


def get_manage_py(project_dir: Path):
    """Return manage.py as a Path; exit if missing."""
    manage = project_dir / 'manage.py'
    if not manage.exists():
        print_colored(f"✗ manage.py not found in {project_dir}", Colors.RED)
        sys.exit(1)
    return manage


# ── Browser opener ──────────────────────────────────────────────────────────
def open_browser_delayed(url: str, delay: float = 2.5):
    def _open():
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


# ── Django server ───────────────────────────────────────────────────────────
def start_django_server(project_dir: Path, host='127.0.0.1', preferred_port=8030):
    python_exe = get_python_executable(project_dir)
    manage_py  = get_manage_py(project_dir)

    # ── Choose port ────────────────────────────────────────────────────────
    if is_port_available(host, preferred_port):
        port = preferred_port
        print_colored(f"✓ Using port {port}", Colors.GREEN)
    else:
        print_colored(f"  Port {preferred_port} is in use.", Colors.YELLOW)
        choice = input("  Kill existing process? (y/N): ").strip().lower()
        if choice == 'y' and kill_process_on_port(preferred_port):
            time.sleep(1)
            port = preferred_port if is_port_available(host, preferred_port) \
                   else find_available_port(preferred_port + 1)
        else:
            port = find_available_port(preferred_port + 1)
        print_colored(f"✓ Using port {port}", Colors.GREEN)

    url = f"http://{host}:{port}"

    # ── Build command ───────────────────────────────────────────────────────
    cmd = [
        str(python_exe),
        str(manage_py),
        'runserver',
        f'{host}:{port}',
        '--noreload',
    ]

    print_colored(f"Starting R2H2 at {url}", Colors.CYAN)
    print_colored("Press Ctrl+C to stop.", Colors.YELLOW)

    # ── Platform-specific Popen flags ──────────────────────────────────────
    popen_kwargs = dict(
        cwd=str(project_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    if sys.platform == 'win32':
        # Prevent a second console window from appearing
        popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    open_browser_delayed(url)

    try:
        server = subprocess.Popen(cmd, **popen_kwargs)
    except FileNotFoundError:
        print_colored(f"✗ Python executable not found: {python_exe}", Colors.RED)
        sys.exit(1)

    # ── Wait up to 5 s for the server to bind ──────────────────────────────
    for _ in range(10):
        time.sleep(0.5)
        if server.poll() is not None:
            # Process already exited — grab stderr
            err = server.stderr.read().decode(errors='replace').strip()
            print_colored("✗ Django server failed to start.", Colors.RED)
            if err:
                print_colored(f"  {err}", Colors.RED)
            sys.exit(1)
        if not is_port_available(host, port):
            print_colored(f"✓ Server is up (PID {server.pid})", Colors.GREEN)
            break
    else:
        print_colored("⚠ Server did not bind within 5 s — continuing anyway.", Colors.YELLOW)

    # ── Keep alive until Ctrl+C ────────────────────────────────────────────
    try:
        server.wait()
    except KeyboardInterrupt:
        server.terminate()
        print_colored("\nShutting down R2H2…", Colors.YELLOW)
        print_colored("Thank you for using R2H2! 🚀", Colors.GREEN)


# ── Entry point ─────────────────────────────────────────────────────────────
def main():
    print_colored("=" * 48, Colors.CYAN)
    print_colored("   R2H2 — Renewable to Hydrogen", Colors.GREEN)
    print_colored("=" * 48, Colors.CYAN)

    project_dir = get_project_directory()
    print_colored(f"  Project : {project_dir}", Colors.NC)
    print_colored(f"  Python  : {get_python_executable(project_dir)}", Colors.NC)

    start_django_server(project_dir)


if __name__ == '__main__':
    main()