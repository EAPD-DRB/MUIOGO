"""File I/O utilities for reading and writing JSON data."""

#import ujson as json
import json
from pathlib import Path
from typing import Any, Union


class File:
    """Utility class providing static methods for JSON file operations.

    All methods are static and handle reading/writing JSON data to
    the filesystem. They propagate I/O and OS errors to callers.
    """

    @staticmethod
    def readFile(path: Union[str, Path]) -> Any:
        """Read and parse a JSON file.

        Args:
            path: Filesystem path to the JSON file.

        Returns:
            The parsed JSON content (dict, list, or primitive).

        Raises:
            IndexError: If the file content triggers an index error.
            IOError: If the file cannot be read.
            OSError: If an OS-level error occurs.
        """
        try:
            with open(path, mode="r") as f:
                data = json.loads(f.read())
            return data
        except IndexError:
            raise IndexError
        except IOError:
            raise IOError
        except OSError:
            raise OSError

    @staticmethod
    def writeFile(data: Any, path: Union[str, Path]) -> None:
        """Serialize data to a pretty-printed JSON file.

        Args:
            data: Python object to serialize (must be JSON-serializable).
            path: Filesystem path where the JSON will be written.

        Raises:
            IndexError: If an index/IO error occurs during writing.
            OSError: If an OS-level error occurs.
        """
        try:
            with open(path, mode="w") as f:
                f.write(json.dumps(data, ensure_ascii=True, indent=4, sort_keys=False))
        except (IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    @staticmethod
    def writeFileUJson(data: Any, path: Union[str, Path]) -> None:
        """Serialize data to a compact JSON file.

        Args:
            data: Python object to serialize (must be JSON-serializable).
            path: Filesystem path where the JSON will be written.

        Raises:
            IndexError: If an index/IO error occurs during writing.
            OSError: If an OS-level error occurs.
        """
        try:
            with open(path, mode="w") as f:
                f.write(json.dumps(data))
        except (IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    @staticmethod
    def readParamFile(path: Union[str, Path]) -> Any:
        """Read and parse a parameter JSON file.

        Functionally identical to :meth:`readFile` but kept as a separate
        entry point for semantic clarity when loading parameter definitions.

        Args:
            path: Filesystem path to the parameter JSON file.

        Returns:
            The parsed JSON content.

        Raises:
            IndexError: If the file content triggers an index error.
            IOError: If the file cannot be read.
            OSError: If an OS-level error occurs.
        """
        try:
            with open(path, mode="r") as f:
                data = json.loads(f.read())
            return data
        except IndexError:
            raise IndexError
        except IOError:
            raise IOError
        except OSError:
            raise OSError