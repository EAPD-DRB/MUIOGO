"""
path_security.py — Shared path-validation utilities.

Prevents path-traversal (CWE-22) and Zip-Slip (CWE-23) attacks by:

1.  Rejecting any single path *component* that contains directory separators,
    parent-directory references (".."), or null bytes.  This stops an attacker
    from injecting traversal sequences at the earliest possible point.

2.  Resolving the final absolute path and checking that it starts with the
    trusted base directory.  Even if an attacker finds a way to smuggle a
    crafted component past step 1, the resolved-path check guarantees the
    result cannot escape the intended directory tree.

Why pathlib.resolve()?
    Path.resolve() collapses *all* symbolic links, ".." segments, and "."
    references, giving a canonical absolute path.  Comparing the start of
    this canonical path against the canonical base directory is the
    industry-standard defence recommended by OWASP.

Usage
-----
    from Classes.Base.path_security import validate_path_component, safe_resolve_path

    validate_path_component(user_supplied_name)           # raises ValueError
    safe_path = safe_resolve_path(Config.DATA_STORAGE, casename, file)
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class PathValidationError(ValueError):
    """Raised when a user-supplied path component fails validation."""
    pass


# Only allow alphanumeric, hyphens, underscores, dots, spaces, and
# parentheses — i.e. characters that are safe in filenames on all major OSes.
_SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9 _\-()\[\].]+$")


def validate_path_component(name: str) -> str:
    """Validate a single user-supplied path component (file or directory name).

    Parameters
    ----------
    name : str
        The raw value received from the client (e.g. ``casename``).

    Returns
    -------
    str
        The validated name (unchanged) when it passes all checks.

    Raises
    ------
    PathValidationError
        When the component contains forbidden characters or sequences.
    """
    if not isinstance(name, str) or not name:
        _reject(name, "empty or non-string value")

    # Null-byte injection
    if "\x00" in name:
        _reject(name, "null byte detected")

    # Directory separators (forward or back slash)
    if "/" in name or "\\" in name:
        _reject(name, "directory separator detected")

    # Parent-directory reference
    if ".." in name:
        _reject(name, "parent directory reference detected")

    # Single dot could mean "current directory" — reject bare "."
    if name.strip() == ".":
        _reject(name, "current directory reference detected")

    # Enforce a safe character whitelist
    if not _SAFE_COMPONENT_RE.match(name):
        _reject(name, "disallowed characters in path component")

    return name


def safe_resolve_path(base_dir: Path, *parts: str) -> Path:
    """Build and resolve a path, ensuring it stays inside *base_dir*.

    Parameters
    ----------
    base_dir : Path
        The trusted root directory (e.g. ``Config.DATA_STORAGE``).
    *parts : str
        One or more user-supplied path components.

    Returns
    -------
    Path
        The resolved absolute path guaranteed to be inside *base_dir*.

    Raises
    ------
    PathValidationError
        When the resolved path escapes *base_dir*.
    """
    # Validate every individual component first
    for part in parts:
        if part is not None:
            validate_path_component(str(part))

    resolved_base = base_dir.resolve()
    resolved_target = Path(base_dir, *parts).resolve()

    # The resolved target must be equal to or a child of the base directory.
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        logger.warning(
            "PATH TRAVERSAL BLOCKED — attempted escape from '%s' to '%s'",
            resolved_base,
            resolved_target,
        )
        raise PathValidationError("Invalid path: target is outside the allowed directory")

    return resolved_target


def safe_zip_extract(zip_file, destination: Path) -> None:
    """Safely extract all entries in *zip_file* into *destination*.

    Each entry's target path is resolved and verified to stay inside
    *destination*.  Entries that would escape the directory are skipped
    and logged with a WARNING.

    Parameters
    ----------
    zip_file : zipfile.ZipFile
        An already-opened ``ZipFile`` object.
    destination : Path
        The directory into which files should be extracted.
    """
    resolved_dest = destination.resolve()

    for member in zip_file.infolist():
        # Skip directory entries — they will be created on demand
        if member.is_dir():
            continue

        # Resolve the would-be extraction target
        target = (resolved_dest / Path(member.filename)).resolve()

        try:
            target.relative_to(resolved_dest)
        except ValueError:
            logger.warning(
                "ZIP SLIP BLOCKED — skipping entry '%s' (would extract to '%s')",
                member.filename,
                target,
            )
            continue

        # Ensure parent directories exist
        target.parent.mkdir(parents=True, exist_ok=True)

        # Extract the single member safely using streaming copy
        with zip_file.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)


# ---------------------------------------------------------------------- #
#  Internal helpers
# ---------------------------------------------------------------------- #

def _reject(name: object, reason: str) -> None:
    """Log a warning and raise ``ValueError``.

    The log message includes the reason for forensic purposes, but the
    exception message returned to the caller is intentionally vague so that
    no internal details leak to a potential attacker.
    """
    logger.warning(
        "PATH VALIDATION FAILED — reason: %s | supplied value: %r",
        reason,
        name,
    )
    raise PathValidationError("Invalid path supplied")
