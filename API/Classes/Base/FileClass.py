#import ujson as json
import json

class File:
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

    @staticmethod
    def writeFileAtomic(data, path):
        import os
        import tempfile
        path = str(path)
        dir_name = os.path.dirname(path) or '.'
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(json.dumps(data, ensure_ascii=True, indent=4, sort_keys=False))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise e
