#import ujson as json
import json
from API.Config.version import CURRENT_MODEL_VERSION
from API.Classes.Base.model_version_validator import validate_model_version

class File:
    @staticmethod
    def readFile(path):
        try:
            with open(path, mode="r") as f:
                data = json.loads(f.read())

            # PR2: Enforce schema validation at load time
            validate_model_version(data)

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
            with open(path, "w") as f:
                # Inject version at save time
                if isinstance(data, dict):
                    data["modelVersion"] = CURRENT_MODEL_VERSION

                f.write(json.dumps(data, ensure_ascii=True, indent=4, sort_keys=False))
        except IndexError:
            raise IndexError
        except IOError:
            raise IOError
        except OSError:
            raise OSError

    @staticmethod
    def writeFileUJson(data, path):
        try:
            with open(path, mode="w") as f:
                f.write(json.dumps(data))
        except IndexError:
            raise IndexError
        except IOError:
            raise IOError
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