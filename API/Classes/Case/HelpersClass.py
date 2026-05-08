# Classes/Helpers/helpers.py

import os
import shutil
from pathlib import Path
from copy import deepcopy


class Helpers:

    @staticmethod
    def build_param(parameters: dict) -> dict[str, dict[str, str]]:
        d = {}
        for k, lst in parameters.items():
            tmp = {}
            for de in lst:
                tmp[de['id']] = str(de['value']).replace(" ", "")
            d[k] = tmp
        return d

    @staticmethod
    def build_vars(variables: dict) -> list[str]:
        names = []
        for _, lst in variables.items():
            for de in lst:
                names.append(de['name'])
        return names

    @staticmethod
    def build_var_by_name(variables: dict) -> dict:
        out = {}
        for group, entries in variables.items():
            for obj in entries:
                out[obj["name"]] = {
                    "id": obj["id"],
                    "group": group,
                    "setrelation": obj.get("setrelation", [])
                }
        return out

    @staticmethod
    def merge_groups(a: dict, b: dict) -> dict:
        out = {**a}
        for key, value in b.items():
            if key in out and isinstance(out[key], dict) and isinstance(value, dict):
                out[key] = {**out[key], **value}
            elif key in out and isinstance(out[key], list) and isinstance(value, list):
                out[key] = out[key] + value
            else:
                out[key] = value
        return out

    @staticmethod
    def resolve_solver_executable(folder: Path, exe_name: str, system: str):
        candidate = folder / exe_name
        if candidate.exists():
            if system != "Windows":
                os.chmod(candidate, os.stat(candidate).st_mode | 0o111)
            return str(candidate.resolve()), True

        which = shutil.which(exe_name)
        if which:
            return which, False

        paths = []
        if system == "Darwin":
            paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
        elif system == "Linux":
            paths = ["/usr/bin", "/usr/local/bin", "/bin", "/snap/bin"]

        for p in paths:
            test = Path(p) / exe_name
            if test.exists():
                return str(test), False

        raise FileNotFoundError(f"Solver not found: {exe_name}")

    @staticmethod
    def keys_exists(element: dict, *keys) -> bool:
        if not isinstance(element, dict):
            return False

        cur = element
        for key in keys:
            if key not in cur:
                return False
            cur = cur[key]
        return True

    # -------------------------------------------------------
    # Ovdje ide logika indikatora, ali bez `self`
    # -------------------------------------------------------

    @staticmethod
    def merge_all_indicators(indicator_types_json, custom_indicators, tech_map):
        type_by_id = {}

        for group, items in indicator_types_json.items():
            for item in items:
                type_by_id[item["id"]] = {**item, "group": group}

        result = {}

        for item in custom_indicators:
            indicator_id = item.get("IndicatorId")
            type_id = item.get("IndicatorTypeId")

            if not indicator_id or not type_id:
                continue

            type_rec = type_by_id.get(type_id)
            if not type_rec:
                continue

            merged = deepcopy(item)
            merged["Techs"] = [tech_map.get(t, t) for t in merged.get("Techs", [])]
            merged["group"] = type_rec["group"]
            merged["indicator_type"] = {k: v for k, v in type_rec.items() if k != "group"}
            merged["id"] = indicator_id
            merged.pop("IndicatorId", None)

            result[indicator_id] = merged

        return result
    
    @staticmethod
    def merge_all_indicators_grouped(indicator_types_json: dict, custom_indicators: list, tech_map: dict) -> dict:
        """
        Vraća strukturu grupisanu po 'group':
        {
            "<group>": [
                { ... indikator ... },
                { ... indikator ... }
            ]
        }
        """

        # 1) Sakupi sve tipove indikatora + group info
        type_by_id = {}
        for group_name, group_items in indicator_types_json.items():
            if not isinstance(group_items, list):
                continue

            for item in group_items:
                if isinstance(item, dict) and "id" in item:
                    type_by_id[item["id"]] = { **item, "group": group_name }

        # 2) rezultat: group -> list of objects
        result = {}

        # 3) obrada custom indikatora
        for item in custom_indicators:
            if not isinstance(item, dict):
                continue

            indicator_name = item.get("Indicator")
            indicator_id = item.get("IndicatorId")
            indicator_type_id = item.get("IndicatorTypeId")

            if not indicator_name or not indicator_id or not indicator_type_id:
                continue

            type_rec = type_by_id.get(indicator_type_id)
            if not type_rec:
                continue

            group = type_rec["group"]
            merged = deepcopy(item)

            # Mapiranje Sets: TECHid -> TechName
            techs_ids = merged.get("Techs", [])
            if isinstance(techs_ids, list):
                merged["Techs"] = [tech_map.get(t, t) for t in techs_ids]

            # Root-level group
            merged["group"] = group

            # indicator_type bez 'group'
            clean_type = {k: v for k, v in type_rec.items() if k != "group"}
            merged["indicator_type"] = deepcopy(clean_type)

            # Rename IndicatorId -> id
            merged["id"] = indicator_id
            if "IndicatorId" in merged:
                del merged["IndicatorId"]

            # -------------------------------
            # UPIS: grupa -> lista objekata
            # -------------------------------
            if group not in result:
                result[group] = []

            result[group].append(merged)

        return result