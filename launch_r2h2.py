#!/usr/bin/env python3

"""
R2H2 Desktop App Launcher
Python-based launcher for the R2H2 Django application
"""

import os
import sys
import time
import subprocess
import webbrowser
import socket
from pathlib import Path
import signal
import threading

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message, color=Colors.NC):
    """Print colored message to terminal"""
    print(f"{color}{message}{Colors.NC}")

def find_available_port(start_port=8030, max_attempts=50):
    """Find the next available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available('127.0.0.1', port):
            return port
    
    # If no port found in range, raise exception
    raise RuntimeError(f"No available ports found in range {start_port}-{start_port + max_attempts}")

def is_port_available(host, port):
    """Check if port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # 1 second timeout
            result = s.connect_ex((host, port))
            return result != 0  # Port is available if connection failed
    except OSError:
        return False

def kill_process_on_port(port):
    """Attempt to kill any process using the specified port"""
    try:
        if os.name == 'nt':  # Windows
            # Find process using the port
            result = subprocess.run(
                ['netstat', '-ano'], 
                capture_output=True, 
                text=True
            )
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        print_colored(f"Killing process {pid} on port {port}", Colors.YELLOW)
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        return True
        else:  # Unix/Linux/macOS
            # Find process using lsof
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'], 
                capture_output=True, 
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        print_colored(f"Killing process {pid} on port {port}", Colors.YELLOW)
                        subprocess.run(['kill', '-9', pid], capture_output=True)
                return True
    except Exception as e:
        print_colored(f"Could not kill process on port {port}: {e}", Colors.YELLOW)
    
    return False

def get_project_directory():
    """Get project directory from r2h2 config or fallback to current directory"""
    try:
        import r2h2.config
        r2h2_app_dir = Path(r2h2.config.get_config_path()).parent / 'R2H2_app'
        
        # Check if Django files exist in the R2H2 config location
        if (r2h2_app_dir / 'manage.py').exists():
            return str(r2h2_app_dir)
        else:
            # Fallback to current directory
            current_dir = Path(__file__).parent
            print_colored(f"Django files not found in R2H2 config location", Colors.YELLOW)
            print_colored(f"Using current directory: {current_dir}", Colors.YELLOW)
            return str(current_dir)
            
    except ImportError:
        # Fallback to current directory if r2h2 not available
        current_dir = Path(__file__).parent
        print_colored("r2h2.config not available, using current directory", Colors.YELLOW)
        return str(current_dir)

def ensure_r2h2_config():
    """Ensure config.yaml exists, creating it interactively if missing.
    Also reports where db.sqlite3 will be stored."""
    try:
        import r2h2.config as cfg_module

        cfg_path = cfg_module.get_config_path()
        cfg = cfg_module.load_config()

        if cfg is None:
            print_colored("\n⚠  No R2H2 config found.", Colors.YELLOW)
            print_colored(f"   Config will be saved to: {cfg_path}", Colors.BLUE)

            # Suggest the platform data directory as default
            try:
                import platformdirs
                default_data = Path(platformdirs.user_data_dir("r2h2", "r2h2"))
            except Exception:
                default_data = Path.home() / "r2h2_data"

            val = input(
                f"   Enter path for R2H2 data storage [{default_data}]: "
            ).strip()
            data_root = Path(val).expanduser().resolve() if val else default_data
            data_root.mkdir(parents=True, exist_ok=True)

            cfg = cfg_module.create_config_file(data_root=str(data_root))
            print_colored(f"✓ Config created at: {cfg_path}", Colors.GREEN)
        else:
            print_colored(f"✓ Config found: {cfg_path}", Colors.GREEN)

        # Report DB location
        data_root = Path(cfg['paths']['data_root'])
        db_path = data_root / 'R2H2_DataBase.sqlite3'
        print_colored(f"✓ Database location: {db_path}", Colors.BLUE)

        # Ensure data_root exists (in case it was deleted)
        data_root.mkdir(parents=True, exist_ok=True)

        return True

    except ImportError:
        print_colored("⚠  r2h2.config not available — skipping config check.", Colors.YELLOW)
        return True
    except Exception as e:
        print_colored(f"✗ Failed to initialise R2H2 config: {e}", Colors.RED)
        return False


def check_dependencies():
    """Check if required dependencies are installed"""
    print_colored("Checking dependencies...", Colors.YELLOW)
    
    # Check Django
    try:
        import django
        print_colored(f"✓ Django {django.get_version()} found", Colors.GREEN)
    except ImportError:
        print_colored("✗ Django is not installed", Colors.RED)
        print_colored("Install with: pip install django", Colors.YELLOW)
        return False
    
    # Check r2h2
    try:
        import r2h2
        print_colored("✓ r2h2 module found", Colors.GREEN)
    except ImportError:
        print_colored("✗ r2h2 module is not installed", Colors.RED)
        return False
    
    return True

def find_virtual_environment(project_dir):
    """Find and activate virtual environment"""
    venv_names = ['r2h2_env', 'venv', '.venv']
    
    for venv_name in venv_names:
        venv_path = Path(project_dir) / venv_name
        if venv_path.exists():
            if os.name == 'nt':  # Windows
                activate_script = venv_path / 'Scripts' / 'activate.bat'
            else:  # Unix/Linux/macOS
                activate_script = venv_path / 'bin' / 'activate'
            
            if activate_script.exists():
                print_colored(f"Found virtual environment: {venv_name}", Colors.GREEN)
                return str(venv_path)
    
    print_colored("No virtual environment found. Using system Python.", Colors.YELLOW)
    return None

def run_django_command(project_dir, venv_path, command):
    """Run Django management command"""
    env = os.environ.copy()
    
    if venv_path:
        if os.name == 'nt':  # Windows
            python_exe = Path(venv_path) / 'Scripts' / 'python.exe'
        else:  # Unix/Linux/macOS
            python_exe = Path(venv_path) / 'bin' / 'python'
    else:
        python_exe = sys.executable
    
    cmd = [str(python_exe), 'manage.py'] + command
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def run_migrations(project_dir, venv_path):
    """Check and run database migrations"""
    print_colored("Checking for database migrations...", Colors.YELLOW)
    
    # Check if migrations are needed
    success, output = run_django_command(project_dir, venv_path, ['makemigrations', '--check', '--dry-run'])
    
    if not success:
        print_colored("Creating new migrations...", Colors.YELLOW)
        success, output = run_django_command(project_dir, venv_path, ['makemigrations'])
        if not success:
            print_colored(f"Error creating migrations: {output}", Colors.RED)
            return False
    
    # Apply migrations
    print_colored("Applying database migrations...", Colors.YELLOW)
    success, output = run_django_command(project_dir, venv_path, ['migrate'])
    
    if not success:
        print_colored(f"Error applying migrations: {output}", Colors.RED)
        return False
    
    print_colored("✓ Migrations completed", Colors.GREEN)
    return True

def open_browser_delayed(url, delay=3):
    """Open browser after delay"""
    def delayed_open():
        time.sleep(delay)
        print_colored(f"Opening browser: {url}", Colors.BLUE)
        webbrowser.open(url)
    
    thread = threading.Thread(target=delayed_open)
    thread.daemon = True
    thread.start()

def start_django_server(project_dir, venv_path, host='127.0.0.1', preferred_port=8030):
    """Start Django development server on next available port"""
    env = os.environ.copy()

    if venv_path:
        if os.name == 'nt':  # Windows
            python_exe = Path(venv_path) / 'Scripts' / 'python.exe'
        else:  # Unix/Linux/macOS
            python_exe = Path(venv_path) / 'bin' / 'python'
    else:
        python_exe = sys.executable

    # Find available port
    try:
        if is_port_available(host, preferred_port):
            port = preferred_port
            print_colored(f"✓ Using preferred port {port}", Colors.GREEN)
        else:
            print_colored(f"Port {preferred_port} is in use, searching for available port...", Colors.YELLOW)

            choice = input(f"Kill existing process on port {preferred_port}? (y/N): ").strip().lower()
            if choice == 'y':
                if kill_process_on_port(preferred_port):
                    time.sleep(1)
                    if is_port_available(host, preferred_port):
                        port = preferred_port
                        print_colored(f"✓ Freed up port {port}", Colors.GREEN)
                    else:
                        port = find_available_port(preferred_port + 1)
                        print_colored(f"✓ Using alternative port {port}", Colors.GREEN)
                else:
                    port = find_available_port(preferred_port + 1)
                    print_colored(f"✓ Using alternative port {port}", Colors.GREEN)
            else:
                port = find_available_port(preferred_port + 1)
                print_colored(f"✓ Using alternative port {port}", Colors.GREEN)

    except RuntimeError as e:
        print_colored(f"Error: {e}", Colors.RED)
        sys.exit(1)

    cmd = [
        str(python_exe),
        'manage.py',
        'runserver',
        f'{host}:{port}',
        '--noreload',
        '--settings=r2h2_ui.settings',
    ]

    print_colored(f"Starting Django server at http://{host}:{port}", Colors.GREEN)
    print_colored("Press Ctrl+C to stop the server", Colors.YELLOW)

    # Open browser after delay
    open_browser_delayed(f"http://{host}:{port}")

    try:
        server = subprocess.Popen(
            cmd,
            cwd=project_dir,
            env=env,
            stdout=subprocess.DEVNULL,  # suppress request logs
            stderr=subprocess.PIPE,     # keep errors visible for debugging
        )

        # Wait for the server to start
        time.sleep(2)

        # Check if the server is running
        if server.poll() is None:
            print_colored(f"✓ Django server is running with PID: {server.pid}", Colors.GREEN)
        else:
            # Read stderr to show what went wrong
            err = server.stderr.read().decode(errors='replace')
            print_colored("✗ Failed to start Django server", Colors.RED)
            if err:
                print_colored(f"  Error detail: {err.strip()}", Colors.RED)
            sys.exit(1)

    except Exception as e:
        print_colored(f"Error starting server: {e}", Colors.RED)
        sys.exit(1)

    try:
        server.wait()
    except KeyboardInterrupt:
        server.terminate()
        print_colored("\nShutting down R2H2 application...", Colors.YELLOW)
        print_colored("Thank you for using R2H2! 🚀", Colors.GREEN)

def main():
    """Main launch function"""
    print_colored("=== R2H2 Desktop Application Launcher ===", Colors.GREEN)
    
    # Configuration
    HOST = '127.0.0.1'
    PREFERRED_PORT = 8030
    
    # Get project directory
    project_dir = get_project_directory()
    print_colored(f"Project directory: {project_dir}", Colors.BLUE)
    
    # Check if manage.py exists
    manage_py = Path(project_dir) / 'manage.py'
    if not manage_py.exists():
        print_colored(f"Error: manage.py not found in {project_dir}", Colors.RED)
        print_colored("Please ensure R2H2_app is installed correctly.", Colors.RED)
        sys.exit(1)
    
    # Ensure config.yaml exists and report DB location
    if not ensure_r2h2_config():
        print_colored("Failed to initialise R2H2 config", Colors.RED)
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        print_colored("Please install missing dependencies", Colors.RED)
        sys.exit(1)
    
    # Find virtual environment
    venv_path = find_virtual_environment(project_dir)
    
    # Run migrations
    if not run_migrations(project_dir, venv_path):
        print_colored("Failed to run migrations", Colors.RED)
        sys.exit(1)
    
    # Start Django server (will find available port automatically)
    start_django_server(project_dir, venv_path, HOST, PREFERRED_PORT)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\nApplication terminated by user", Colors.YELLOW)
        sys.exit(0)
    except Exception as e:
        print_colored(f"Unexpected error: {e}", Colors.RED)
        sys.exit(1)