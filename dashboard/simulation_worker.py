"""Lightweight entry point for the spawned simulation subprocess.

This module intentionally has NO top-level Django imports.  When
multiprocessing 'spawn' creates a child process it re-imports whichever
module contains the Process target function.  Any Django model import at
module level would trigger 'Apps aren't loaded yet' before django.setup()
has been called.  By isolating the entry point here we avoid that.
"""


def run(run_id: int) -> None:
    """Bootstrap Django then run the simulation worker."""
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'r2h2_ui.settings')
    django.setup()

    # Safe to import views only after setup() has been called.
    from dashboard.views import _run_simulation_thread
    _run_simulation_thread(run_id)
