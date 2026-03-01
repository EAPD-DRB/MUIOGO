"""
storage_setup.py

Platform-aware data directory initialization.
Called once during application startup — never at module import time.
"""

import logging
import os
import platform
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_data_directory(path: Path) -> None:
    """Create the data-storage directory and set safe permissions.

    Behaviour per platform
    ----------------------
    - **Linux / macOS**: ``chmod 0o755`` (owner rwx, group/others rx).
    - **Windows**: ``chmod`` is skipped entirely; rely on NTFS ACLs.

    After creation the directory is checked for writability.  If the
    directory cannot be created, or is not writable, a clear error is
    raised so that the calling code can decide whether to abort startup
    or handle the failure, rather than continuing with a broken storage path.

    Parameters
    ----------
    path : pathlib.Path
        Absolute or relative path to the data-storage directory.

    Raises
    ------
    OSError
        If the directory cannot be created (e.g. read-only parent).
    PermissionError
        If the directory exists but is not writable.
    """
    # --- 1. Ensure directory tree exists --------------------------------
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.info("Data-storage directory ready: %s", path.resolve())
    except OSError:
        logger.exception("Failed to create data-storage directory: %s", path)
        raise

    # --- 2. Set permissions (Unix only) ---------------------------------
    current_platform = platform.system()

    if current_platform in ("Linux", "Darwin"):
        try:
            path.chmod(0o755)
            logger.info(
                "Permissions set to 0o755 on %s (platform: %s)",
                path,
                current_platform,
            )
        except OSError:
            logger.warning(
                "Could not set permissions on %s. "
                "Continuing with existing filesystem permissions.",
                path,
                exc_info=True,
            )
    else:
        logger.info(
            "Skipping chmod on %s (platform: %s); using existing filesystem permissions.",
            path,
            current_platform,
        )

    # --- 3. Validate writability ----------------------------------------
    # For directories, being able to create files typically requires both
    # write *and* execute/search permissions. Check both, then confirm with
    # a small create/delete probe to catch ACL or FS quirks.
    if not os.access(path, os.W_OK | os.X_OK):
        raise PermissionError(
            f"Data-storage directory is not writable: {path}"
        )

    # Create/delete probe: ensures we can actually write inside the directory.
    test_file = path / ".storage_setup_write_test"
    try:
        with open(test_file, "w"):
            pass
    except OSError as exc:
        raise PermissionError(
            f"Data-storage directory is not writable: {path}"
        ) from exc
    else:
        try:
            test_file.unlink()
        except OSError:
            # Non-fatal: directory is writable (file was created), but cleanup failed.
            logger.debug(
                "Temporary writability probe file could not be removed: %s",
                test_file,
                exc_info=True,
            )
