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
    def writeFile(data, path, indent=4):
        # indent=None emits compact JSON on the C-accelerated encoder — ~6x
        # faster and ~2.5x smaller than indented output. Callers pass it only
        # for the multi-MB machine-read view/result files written on every run;
        # everything else (including the version-controlled Parameters/
        # Variables/Duals/Indicators files) keeps the readable, diffable
        # 4-space default.
        try:
            with open(path, mode="w") as f:
                if indent is None:
                    f.write(json.dumps(data, ensure_ascii=True, separators=(",", ":")))
                else:
                    f.write(json.dumps(data, ensure_ascii=True, indent=indent, sort_keys=False))
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