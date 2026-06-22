#!/usr/bin/env python3
"""
R2H2 Desktop App Launcher
Python-based launcher for the R2H2 Django application.

Server  : waitress (multi-threaded WSGI) → fallback: Django runserver
Window  : pywebview native window (WebView2 on Windows) → fallback: system browser
"""

import atexit
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


# ── Clean shutdown ──────────────────────────────────────────────────────────
# Registry of Popen objects to kill on exit (runserver fallback subprocess).
_child_processes: list = []


def _kill_children():
    """Kill all registered child processes (called by atexit)."""
    for proc in _child_processes:
        try:
            if proc.poll() is None:
                if sys.platform == 'win32':
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                        capture_output=True,
                    )
                else:
                    proc.terminate()
        except Exception:
            pass


atexit.register(_kill_children)


def _setup_windows_ctrl_c():
    """On Windows, intercept Ctrl+C so PowerShell actually exits cleanly.

    PowerShell sends CTRL_C_EVENT to the console's process group.  Python
    receives it as a KeyboardInterrupt on the main thread, but any subprocess
    created with CREATE_NO_WINDOW (detached from the console) does NOT receive
    it — those become ghost processes.

    This handler:
      1. Kills all registered child processes via taskkill /F /T (force, tree).
      2. Then uses taskkill /F /T on our own PID so the entire process tree
         (including simulation worker subprocesses spawned by Django) is torn
         down, even if they were created by other threads.
    """
    if sys.platform != 'win32':
        return

    import ctypes

    CTRL_C_EVENT = 0

    def _handler(ctrl_type):
        if ctrl_type == CTRL_C_EVENT:
            print_colored("\nShutting down R2H2…", Colors.YELLOW)
            _kill_children()
            # Kill our own process tree (catches simulation worker spawns).
            subprocess.run(
                ['taskkill', '/F', '/T', '/PID', str(os.getpid())],
                capture_output=True,
            )
            return True   # True = we handled it; don't pass to next handler
        return False

    HandlerRoutine = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    _handler_ref = HandlerRoutine(_handler)   # must stay alive
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler_ref, True)
    # Stash ref so it isn't GC'd
    _setup_windows_ctrl_c._handler_ref = _handler_ref


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
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True)
                    return True
        else:
            result = subprocess.run(['lsof', '-ti', f'tcp:{port}'], capture_output=True, text=True)
            pid = result.stdout.strip()
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                return True
    except Exception as e:
        print_colored(f"  Could not kill process on port {port}: {e}", Colors.YELLOW)
    return False


# ── Project / venv resolution ───────────────────────────────────────────────
def get_python_executable():
    """Return the Python executable that has the r2h2 package installed."""
    cwd = Path.cwd()
    for venv_name in ('venv', '.venv', 'env', '.env'):
        venv = cwd / venv_name
        candidate = venv / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _django_manage(*args):
    """Run a Django management command in-process."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r2h2_ui.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage'] + list(args))


def run_migrate():
    """Run migrations in-process."""
    _django_manage('migrate', '--noinput')


# ── Port selection ──────────────────────────────────────────────────────────
def choose_port(host='127.0.0.1', preferred_port=8030):
    if is_port_available(host, preferred_port):
        print_colored(f"✓ Using port {preferred_port}", Colors.GREEN)
        return preferred_port
    print_colored(f"  Port {preferred_port} is in use.", Colors.YELLOW)
    choice = input("  Kill existing process? (y/N): ").strip().lower()
    if choice == 'y' and kill_process_on_port(preferred_port):
        time.sleep(1)
        port = preferred_port if is_port_available(host, preferred_port) \
               else find_available_port(preferred_port + 1)
    else:
        port = find_available_port(preferred_port + 1)
    print_colored(f"✓ Using port {port}", Colors.GREEN)
    return port


# ── WSGI server: waitress (primary) ────────────────────────────────────────
def _serve_waitress(host, port):
    """Serve the Django WSGI app via waitress (blocking)."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r2h2_ui.settings')
    import django
    django.setup()
    from waitress import serve
    from r2h2_ui.wsgi import application
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    wsgi_app = StaticFilesHandler(application)
    # 8 threads handles concurrent browser tabs + simulation poll traffic
    # without any request-queue stalling.
    serve(wsgi_app, host=host, port=port, threads=8,
          # Increase connection backlog for burst traffic during simulation.
          backlog=64,
          # Tune for desktop use: long keepalive reduces reconnect overhead.
          channel_timeout=120,
          # Log to stderr so errors are visible in the launcher console.
          _quiet=False)


def _serve_runserver_fallback(host, port, python_exe):
    """Fall back to Django runserver in a subprocess if waitress is unavailable."""
    cmd = [str(python_exe), '-m', 'django', 'runserver', f'{host}:{port}', '--noreload']
    popen_kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if sys.platform == 'win32':
        popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(cmd, **popen_kwargs)
    _child_processes.append(proc)
    return proc


# ── Window: pywebview (primary) ─────────────────────────────────────────────
def _open_pywebview(url, title='R2H2'):
    """Open a native desktop window using pywebview (blocking until closed)."""
    import webview
    window = webview.create_window(
        title, url,
        width=1440, height=900,
        min_size=(1000, 700),
        # Allow JS → Python bridge if needed in future; harmless when unused.
        js_api=None,
        # Confirm before closing to avoid accidental shutdown mid-simulation.
        confirm_close=True,
        # Keep background transparent during load so the splash isn't jarring.
        background_color='#f0fafb',
    )
    # pywebview.start() blocks until the window is closed.
    # Use EdgeChromium (WebView2) on Windows for best performance.
    gui = 'edgechromium' if sys.platform == 'win32' else None

    def _maximise():
        try:
            window.maximize()
        except Exception:
            pass

    try:
        webview.start(gui=gui, debug=False, func=_maximise)
    except Exception:
        webview.start(debug=False, func=_maximise)


# ── Entry point ─────────────────────────────────────────────────────────────
def main():
    print_colored("=" * 48, Colors.CYAN)
    print_colored("   R2H2 — Renewable to Hydrogen", Colors.GREEN)
    print_colored("=" * 48, Colors.CYAN)

    # Install Windows Ctrl+C handler immediately so PowerShell Ctrl+C always
    # does a full process-tree kill — no ghost Python/simulation processes left.
    _setup_windows_ctrl_c()

    # Set the console window title so it shows "R2H2" instead of "python"
    # in the taskbar and Task Manager.
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW('R2H2')

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r2h2_ui.settings')
    print_colored(f"  Python  : {get_python_executable()}", Colors.NC)

    # Detect capabilities before choosing strategy
    try:
        import waitress  # noqa: F401
        _has_waitress = True
    except ImportError:
        _has_waitress = False

    try:
        import webview  # noqa: F401
        _has_webview = True
    except ImportError:
        _has_webview = False

    host = '127.0.0.1'
    port = choose_port(host)
    url  = f"http://{host}:{port}"

    # Run migrations before starting the server
    try:
        run_migrate()
    except SystemExit:
        pass  # migrate --noinput exits 0; ignore

    if _has_waitress:
        # ── Waitress path ───────────────────────────────────────────────────
        # waitress must run in a daemon thread; pywebview (or webbrowser)
        # runs in the main thread.
        print_colored("✓ Using waitress server (multi-threaded)", Colors.GREEN)
        server_thread = threading.Thread(
            target=_serve_waitress, args=(host, port), daemon=True
        )
        server_thread.start()

        # Wait until the port is bound before opening the window
        for _ in range(20):
            time.sleep(0.5)
            if not is_port_available(host, port):
                print_colored(f"✓ Server is up at {url}", Colors.GREEN)
                break
        else:
            print_colored("⚠ Server did not bind within 10 s — opening window anyway.", Colors.YELLOW)

        if _has_webview:
            print_colored("✓ Opening native window (pywebview)", Colors.GREEN)
            print_colored("  Close the R2H2 window to stop the server.", Colors.YELLOW)
            try:
                _open_pywebview(url)
            except Exception as exc:
                print_colored(f"⚠ pywebview failed ({exc}); falling back to browser.", Colors.YELLOW)
                webbrowser.open(url)
                # Keep the process alive until Ctrl+C
                try:
                    while True:
                        time.sleep(3600)
                except KeyboardInterrupt:
                    pass
        else:
            print_colored("  pywebview not available — opening in system browser.", Colors.YELLOW)
            webbrowser.open(url)
            print_colored("Press Ctrl+C to stop.", Colors.YELLOW)
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                pass

    else:
        # ── runserver fallback (no waitress installed) ──────────────────────
        print_colored("⚠ waitress not found — using Django runserver (install waitress for better performance).", Colors.YELLOW)
        python_exe = get_python_executable()
        server = _serve_runserver_fallback(host, port, python_exe)
        for _ in range(10):
            time.sleep(0.5)
            if server.poll() is not None:
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

        if _has_webview:
            print_colored("✓ Opening native window (pywebview)", Colors.GREEN)
            try:
                _open_pywebview(url)
            except Exception as exc:
                print_colored(f"⚠ pywebview failed ({exc}); falling back to browser.", Colors.YELLOW)
                webbrowser.open(url)
                try:
                    server.wait()
                except KeyboardInterrupt:
                    pass
        else:
            webbrowser.open(url)
            print_colored("Press Ctrl+C to stop.", Colors.YELLOW)
            try:
                server.wait()
            except KeyboardInterrupt:
                server.terminate()

    print_colored("\nShutting down R2H2…", Colors.YELLOW)
    print_colored("Thank you for using R2H2! 🚀", Colors.GREEN)


if __name__ == '__main__':
    main()
