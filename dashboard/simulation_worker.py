"""Lightweight entry point for the spawned simulation subprocess.

This module intentionally has NO top-level Django imports.  When
multiprocessing 'spawn' creates a child process it re-imports whichever
module contains the Process target function.  Any Django model import at
module level would trigger 'Apps aren't loaded yet' before django.setup()
has been called.  By isolating the entry point here we avoid that.
"""


def _prevent_sleep():
    """Best-effort system sleep inhibitor for the duration of a simulation.

    Returns a zero-argument cleanup callable that must be called when the
    simulation finishes (or errors) to release the inhibit lock.
    """
    import sys
    if sys.platform == 'darwin':
        import subprocess
        try:
            p = subprocess.Popen(['caffeinate', '-i'])
            return p.terminate
        except FileNotFoundError:
            return lambda: None
    if sys.platform == 'win32':
        try:
            import ctypes
            ES_CONTINUOUS      = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED
            )
            return lambda: ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS
            )
        except Exception:
            return lambda: None
    # Linux / other: no-op (CPU load normally keeps the system awake)
    return lambda: None


def run(run_id: int) -> None:
    """Bootstrap Django then run the simulation worker."""
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r2h2_ui.settings')
    django.setup()

    release_sleep_inhibit = _prevent_sleep()
    try:
        # Safe to import views only after setup() has been called.
        from dashboard.views import _run_simulation_thread
        _run_simulation_thread(run_id)
    finally:
        release_sleep_inhibit()
