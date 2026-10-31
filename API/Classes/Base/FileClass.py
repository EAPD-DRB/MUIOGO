"""JSON persistence and the text-file publication helper used by case services.

Only atomicWrite stages a replacement; the JSON writers write directly to disk.
"""
import json
import os
from contextlib import contextmanager

class File:
    @staticmethod
    @contextmanager
    def atomicWrite(path):
        """
        Context manager for writing a plain text file safely: writes go to a
        '<path>.tmp' file first, which only replaces the real file if the
        whole 'with' block completes without error. On failure, the original
        file (if any) is left untouched and the partial '.tmp' file is removed.
        Usage: with File.atomicWrite(path) as f: f.write(...) / f.writelines(...)
        """
        tmp_path = str(path) + '.tmp'
        # The temporary name is shared by all writers to this path. Callers must
        # serialize writes to one destination even though replacement is atomic.
        f = open(tmp_path, mode="w")
        try:
            yield f
        except Exception:
            f.close()
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise
        else:
            f.close()
            os.replace(tmp_path, path)

    @staticmethod
    def readFile(path):
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
    def writeFile(data, path):
        try:
            with open(path, mode="w") as f:
                f.write(json.dumps(data, ensure_ascii=True, indent=4, sort_keys=False))
        except (IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    @staticmethod
    def writeFileUJson(data, path):
        try:
            with open(path, mode="w") as f:
                f.write(json.dumps(data))
        except (IOError, IndexError):
            raise IndexError
        except OSError:
            raise OSError

    @staticmethod
    def readParamFile(path):
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
