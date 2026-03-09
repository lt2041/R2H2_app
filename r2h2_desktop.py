#!/usr/bin/env python3

"""
Simple R2H2 Desktop App Launcher
One-command launcher for R2H2 Django application
"""

def launch():
    """Launch R2H2 desktop application"""
    try:
        from launch_r2h2 import main
        main()
    except ImportError:
        import subprocess
        import sys
        from pathlib import Path
        
        # Try to run launch_r2h2.py from the same directory
        script_path = Path(__file__).parent / 'launch_r2h2.py'
        if script_path.exists():
            subprocess.run([sys.executable, str(script_path)])
        else:
            print("Error: launch_r2h2.py not found")
            sys.exit(1)

if __name__ == '__main__':
    launch()