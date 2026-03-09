#!/usr/bin/env python3

"""
Setup script to install R2H2 desktop launcher
Creates a command-line launcher for easy access
"""

import os
import sys
import subprocess
from pathlib import Path

def get_shell_config_file():
    """Determine which shell config file to use"""
    shell = os.environ.get('SHELL', '')
    
    if 'zsh' in shell:
        return Path.home() / '.zshrc'
    elif 'bash' in shell:
        # Try .bash_profile first (macOS convention), then .bashrc
        bash_profile = Path.home() / '.bash_profile'
        bashrc = Path.home() / '.bashrc'
        return bash_profile if bash_profile.exists() or sys.platform == 'darwin' else bashrc
    else:
        # Default fallback
        return Path.home() / '.profile'

def add_to_path():
    """Add ~/.local/bin to PATH in shell config"""
    config_file = get_shell_config_file()
    local_bin = str(Path.home() / '.local' / 'bin')
    
    print(f"Adding {local_bin} to PATH in {config_file}")
    
    # Check if already in config
    if config_file.exists():
        content = config_file.read_text()
        if local_bin in content and 'PATH' in content:
            print("✓ PATH already configured")
            return True
    
    # Add PATH export
    path_line = f'export PATH="$HOME/.local/bin:$PATH"\n'
    
    with open(config_file, 'a') as f:
        f.write(f'\n# Added by R2H2 setup\n')
        f.write(path_line)
    
    print(f"✓ Added PATH to {config_file}")
    return True

def create_launcher_script():
    """Create a system-wide launcher script"""
    
    # Get the current script directory
    current_dir = Path(__file__).parent
    launch_script = current_dir / 'launch_r2h2.py'
    
    if not launch_script.exists():
        print("Error: launch_r2h2.py not found")
        return False
    
    # Create launcher content
    launcher_content = f'''#!/usr/bin/env python3
"""R2H2 Desktop App Launcher"""
import subprocess
import sys

def main():
    script_path = r"{launch_script}"
    subprocess.run([sys.executable, script_path])

if __name__ == '__main__':
    main()
'''
    
    # Determine launcher location based on OS
    if os.name == 'nt':  # Windows
        launcher_path = Path.home() / 'AppData' / 'Local' / 'bin' / 'r2h2.py'
        launcher_path.parent.mkdir(parents=True, exist_ok=True)
    else:  # Unix/Linux/macOS
        launcher_path = Path.home() / '.local' / 'bin' / 'r2h2'
        launcher_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write launcher script
    with open(launcher_path, 'w') as f:
        f.write(launcher_content)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod(launcher_path, 0o755)
    
    print(f"✓ Launcher installed to: {launcher_path}")
    
    if os.name != 'nt':
        # Auto-configure PATH
        add_to_path()
        
        config_file = get_shell_config_file()
        print(f"\nTo use the launcher in this terminal session:")
        print(f"source {config_file}")
        print("\nOr open a new terminal and run: r2h2")
        
        # Try to source the config file for current session
        try:
            shell = os.environ.get('SHELL', '/bin/bash')
            subprocess.run([shell, '-c', f'source {config_file}'], check=False)
        except:
            pass
            
    else:
        print(f"\nTo run R2H2: python {launcher_path}")
    
    return True

def create_alias_alternative():
    """Create an alias as an alternative to PATH modification"""
    config_file = get_shell_config_file()
    current_dir = Path(__file__).parent
    launch_script = current_dir / 'launch_r2h2.py'
    
    alias_line = f'alias r2h2="python3 {launch_script}"\n'
    
    print(f"Creating alias in {config_file}")
    with open(config_file, 'a') as f:
        f.write(f'\n# R2H2 Desktop alias\n')
        f.write(alias_line)
    
    print("✓ Alias created. Run 'source ~/.zshrc' (or ~/.bash_profile) then 'r2h2'")

if __name__ == '__main__':
    print("=== R2H2 Desktop Launcher Setup ===")
    print(f"Shell: {os.environ.get('SHELL', 'unknown')}")
    print(f"Config file: {get_shell_config_file()}")
    
    choice = input("\nChoose setup method:\n1. Install to ~/.local/bin (recommended)\n2. Create shell alias\nChoice (1/2): ").strip()
    
    if choice == '2':
        create_alias_alternative()
        print("✓ Setup completed! Restart your terminal or run:")
        print(f"source {get_shell_config_file()}")
    else:
        if create_launcher_script():
            print("✓ Setup completed successfully!")
            print("\nRestart your terminal or run:")
            print(f"source {get_shell_config_file()}")
            print("then: r2h2")
        else:
            print("✗ Setup failed")
            sys.exit(1)