import os
from pathlib import Path
import socket
import pandas as pd
import yaml
import platformdirs



### Helper functions for config management

# Internal function to get user config directory
def _user_config_dir() -> Path:
    """Return cross-platform user config directory Path."""
    if platformdirs is not None:
        return Path(platformdirs.user_config_dir("r2h2", "r2h2"))
    return Path.home() / ".r2h2"

# Internal function to get path to config.yaml
def get_config_path() -> Path:
    """Get the path to the config.yaml file (ensuring parent exists)."""
    cfg_dir = _user_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.yaml"

# Internal function to load config from config.yaml
def load_config():
    """Load configuration from config.yaml if it exists; return dict or None."""
    cfg_file = get_config_path()
    if not cfg_file.exists():
        return None
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")
    with open(cfg_file, "r") as f:
        cfg = yaml.safe_load(f) or {}

    # Normalize all path fields to POSIX style for portability
    try:
        paths = cfg.get("paths", {})
        for key, val in list(paths.items()):
            if isinstance(val, str) and val.strip():
                paths[key] = Path(val).expanduser().resolve().as_posix()
        cfg["paths"] = paths
    except Exception:
        # If normalization fails, return original cfg without raising
        pass

    return cfg

# Internal function to create config.yaml
def create_config_file(data_root: str = None):
    """
    Create config.yaml. If data_root is None, prompt via CLI.

    Args:
        data_root: Path to local data root.

    Returns:
        dict: The config that was written.
    """
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    if not data_root:
        default_base = Path.home()
        val = input(f"Enter path to data root [{default_base}]: ").strip()
        data_root = val or str(default_base)

    resolved = Path(data_root).expanduser().resolve()
    already_existed = resolved.exists()
    resolved.mkdir(parents=True, exist_ok=True)   # ensure dir exists for SQLite
    if not already_existed:
        print(f"  Created directory: {resolved}")

    cfg = {
        "paths": {
            "data_root": str(resolved),
        },
        "created": pd.Timestamp.now().isoformat(),
    }

    cfg_file = get_config_path()
    with open(cfg_file, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return cfg

# Get or create config - intended use by initialisation of main r2h2 class
def get_or_create_config():
    """Return existing config or create it interactively if missing.

    When stdin is not a tty (e.g. called from an installer script or
    ``manage.py migrate --noinput``) the prompt is skipped and a
    sensible default data root is used instead:
        Windows : %USERPROFILE%\r2h2-data
        Unix    : ~/r2h2-data
    The user can change this later via ``r2h2.config.update_data_root()``.
    """
    import sys
    cfg = load_config()
    if cfg is not None:
        return cfg
    # Env-var override (set by installer before running migrate)
    env_root = os.environ.get('R2H2_DATA_ROOT')
    if env_root:
        return create_config_file(data_root=env_root)
    # Non-interactive context: don't prompt, use a safe default
    if not sys.stdin.isatty():
        default_root = Path.home() / 'r2h2-data'
        return create_config_file(data_root=str(default_root))
    return create_config_file()

# Update data_root in config.yaml - functional tool for user 
def update_data_root(new_path: str):
    """
    Update the data_root path in config.yaml.

    Args:
        new_path: New path to set as data_root.

    Returns:
        dict: Updated config.
    """
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    cfg = load_config()
    if cfg is None:
        cfg = {"paths": {}}

    cfg.setdefault("paths", {})
    cfg["paths"]["data_root"] = Path(new_path).expanduser().resolve().as_posix()
    cfg["modified"] = pd.Timestamp.now().isoformat()

    cfg_file = get_config_path()
    with open(cfg_file, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return cfg


def update_wind_data_dir(new_path: str):
    """
    Update the wind_data_dir path in config.yaml.

    Args:
        new_path: Directory where uploaded wind HDF5 files are stored.

    Returns:
        dict: Updated config.
    """
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    cfg = load_config()
    if cfg is None:
        cfg = {"paths": {}}

    cfg.setdefault("paths", {})
    wind_dir = Path(new_path).expanduser().resolve()
    wind_dir.mkdir(parents=True, exist_ok=True)
    cfg["paths"]["wind_data_dir"] = wind_dir.as_posix()
    cfg["modified"] = pd.Timestamp.now().isoformat()

    cfg_file = get_config_path()
    with open(cfg_file, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return cfg


def get_wind_data_dir() -> Path:
    """
    Return the configured wind data directory, falling back to
    ``<data_root>/wind_data`` if not explicitly set.
    """
    cfg = load_config()
    if cfg:
        wind_dir = cfg.get("paths", {}).get("wind_data_dir")
        if wind_dir:
            p = Path(wind_dir)
            p.mkdir(parents=True, exist_ok=True)
            return p
    # Fallback: derive from data_root
    if cfg:
        data_root = cfg.get("paths", {}).get("data_root")
        if data_root:
            p = Path(data_root) / "wind_data"
            p.mkdir(parents=True, exist_ok=True)
            return p
    # Last resort: app data/wind_data
    here = Path(__file__).resolve().parent.parent / "data" / "wind_data"
    here.mkdir(parents=True, exist_ok=True)
    return here


############################################################

# Contaier class to hold paths and other global settings
class Paths():

    def __init__(self, verbose=True):

        # Initialise `R2H2` object with data_root location
        cfg = get_or_create_config()
        self.data_root = Path(cfg['paths']['data_root'])
        
        # Determine whether Windows or Unix
        if os.name == 'nt':
            self.machine_id = "Windows"
        else:
            self.machine_id = socket.gethostname()
        
        # Prompt user on data_root location and how to change it
        if verbose:
            print(f"R2H2 is configured to access data stored here: {self.data_root}.")
            print(f'To change this path, use:  r2h2.config.update_data_root("{str(Path.home() / "...")}")\n')

