import os
from Classes.Base.FileClass import File
from Classes.Case.OsemosysClass import Osemosys
from Classes.Case.CaseClass import Case
from API.Classes.Base.SchemaRegistry import SchemaRegistry
from API.Classes.Base.ParameterIterator import ParameterIterator


class UpdateCase(Osemosys):
    def __init__(self, case, genData):
        Osemosys.__init__(self, case)
        self.genDataUpdate = genData
        self.case = case

    # -------------------------------------------------------------------------
    # Core engine
    # -------------------------------------------------------------------------

    def _execute_unified_update(
        self,
        group_key,
        path_attr,
        normalizer_name,
        optional_file=False,
        item_filter=None,
        item_expander=None,
    ):
        try:
            path = getattr(self, path_attr)

            if optional_file and not os.path.isfile(path):
                getattr(Case(self.case, self.genDataUpdate), f"default_{group_key}")()
                return

            existing_data = getattr(self, normalizer_name)(File.readFile(path))

            data = ParameterIterator.build_update(
                group_key       = group_key,
                parameters      = self.PARAMETERS[group_key],
                gen_data        = self.genDataUpdate,
                scenarios       = self.genDataUpdate["osy-scenarios"],
                existing_data   = existing_data,
                scenario_id_key = "ScenarioId",
                base_scenario   = "SC_0",
                keys_exists_fn  = self.keys_exists,
                item_filter     = item_filter,
                item_expander   = item_expander,
            )

            File.writeFile(data, path)

        except IOError:
            raise IOError

    # -------------------------------------------------------------------------
    # Scalar (non-year) groups: R, RT, RE, RS
    # -------------------------------------------------------------------------
    # These store flat {dim_id: value} chunks with no year axis.
    # ParameterIterator always produces year-keyed chunks, so these get a
    # dedicated thin handler that's still far shorter than the originals.
    # -------------------------------------------------------------------------

    def _execute_scalar_update(
        self,
        group_key,
        path_attr,
        normalizer_name,
        dim_list_key,
        dim_id_key,
        optional_file=False,
    ):
        try:
            path = getattr(self, path_attr)

            if optional_file and not os.path.isfile(path):
                getattr(Case(self.case, self.genDataUpdate), f"default_{group_key}")()
                return

            source    = getattr(self, normalizer_name)(File.readFile(path))
            dim_items = self.genDataUpdate[dim_list_key]
            scenarios = self.genDataUpdate["osy-scenarios"]

            result = {}
            for param in self.PARAMETERS[group_key]:
                pid = param["id"]
                result[pid] = {}
                for sc in scenarios:
                    sc_id = sc["ScenarioId"]
                    chunk = {}
                    for item in dim_items:
                        iid = item[dim_id_key]
                        if self.keys_exists(source, pid, sc_id, iid):
                            chunk[iid] = source[pid][sc_id][iid]
                        elif sc_id == "SC_0":
                            chunk[iid] = param["default"]
                        else:
                            chunk[iid] = None
                    result[pid][sc_id] = [chunk]

            File.writeFile(result, path)

        except IOError:
            raise IOError

    # -------------------------------------------------------------------------
    # Group R — unique shape: {param_id: {sc_id: [{'value': v}]}}
    # -------------------------------------------------------------------------

    def update_R(self):
        try:
            source    = self.R(File.readFile(self.rPath))
            scenarios = self.genDataUpdate["osy-scenarios"]
            result    = {}
            for param in self.PARAMETERS["R"]:
                pid = param["id"]
                result[pid] = {}
                for sc in scenarios:
                    sc_id = sc["ScenarioId"]
                    if self.keys_exists(source, pid, sc_id, "value"):
                        value = source[pid][sc_id]["value"]
                    elif sc_id == "SC_0":
                        value = param["default"]
                    else:
                        value = None
                    result[pid][sc_id] = [{"value": value}]
            File.writeFile(result, self.rPath)
        except IOError:
            raise IOError

    # -------------------------------------------------------------------------
    # Scalar dimension groups
    # -------------------------------------------------------------------------

    def update_RT(self):
        self._execute_scalar_update("RT", "rtPath", "RT", "osy-tech", "TechId")

    def update_RE(self):
        self._execute_scalar_update("RE", "rePath", "RE", "osy-emis", "EmisId")

    def update_RS(self):
        self._execute_scalar_update("RS", "rsPath", "RS", "osy-stg", "StgId", optional_file=True)

    # -------------------------------------------------------------------------
    # Standard year-keyed groups — pure ParameterIterator
    # -------------------------------------------------------------------------

    def update_RY(self):
        self._execute_unified_update("RY",    "ryPath",   "RY")

    def update_RYT(self):
        self._execute_unified_update("RYT",   "rytPath",  "RYT")

    def update_RYC(self):
        self._execute_unified_update("RYC",   "rycPath",  "RYC")

    def update_RYE(self):
        self._execute_unified_update("RYE",   "ryePath",  "RYE")

    def update_RYS(self):
        self._execute_unified_update("RYS",   "rysPath",  "RYS",   optional_file=True)

    def update_RYTs(self):
        self._execute_unified_update("RYTs",  "rytsPath", "RYTs")

    def update_RYDtb(self):
        self._execute_unified_update("RYDtb", "rydtbPath","RYDtb", optional_file=True)

    def update_RYSeDt(self):
        self._execute_unified_update("RYSeDt","rysedtPath","RYSeDt",optional_file=True)

    def update_RYTM(self):
        self._execute_unified_update("RYTM",  "rytmPath", "RYTM")

    def update_RYTTs(self):
        self._execute_unified_update("RYTTs", "ryttsPath","RYTTs")

    def update_RYCTs(self):
        self._execute_unified_update("RYCTs", "ryctsPath","RYCTs")

    def update_RYCn(self):
        self._execute_unified_update("RYCn",  "rycnPath", "RYCn")

    # -------------------------------------------------------------------------
    # Filtered groups — item_filter + item_expander callbacks
    # -------------------------------------------------------------------------

    def update_RYTC(self):
        self._execute_unified_update(
            "RYTC", "rytcPath", "RYTC",
            item_filter   = lambda item, pid: bool(item.get(pid)),
            item_expander = lambda item, pid: [{"CommId": c} for c in item[pid]],
        )

    def update_RYTE(self):
        self._execute_unified_update(
            "RYTE", "rytePath", "RYTE",
            item_filter   = lambda item, pid: bool(item.get(pid)),
            item_expander = lambda item, pid: [{"EmisId": e} for e in item[pid]],
        )

    def update_RYTCM(self):
        mo = int(self.genDataUpdate["osy-mo"]) + 1
        self._execute_unified_update(
            "RYTCM", "rytcmPath", "RYTCM",
            item_filter   = lambda item, pid: bool(item.get(pid)),
            item_expander = lambda item, pid: [
                {"CommId": c, "MoId": m}
                for c in item[pid]
                for m in range(1, mo)
            ],
        )

    def update_RYTEM(self):
        mo = int(self.genDataUpdate["osy-mo"]) + 1
        self._execute_unified_update(
            "RYTEM", "rytemPath", "RYTEM",
            item_filter   = lambda item, pid: bool(item.get("EAR")),
            item_expander = lambda item, pid: [
                {"EmisId": e, "MoId": m}
                for e in item["EAR"]
                for m in range(1, mo)
            ],
        )

    def update_RTSM(self):
        mo = int(self.genDataUpdate["osy-mo"]) + 1
        self._execute_unified_update(
            "RTSM", "rtsmPath", "RTSM",
            optional_file = True,
            item_filter   = lambda item, pid: bool(item.get(pid)),
            item_expander = lambda item, pid: [
                {"TechId": item[pid], "MoId": m}
                for m in range(1, mo)
            ],
        )

    def update_RYTSM(self):
        mo = int(self.genDataUpdate["osy-mo"]) + 1
        self._execute_unified_update(
            "RYTSM", "rytsmPath", "RYTSM",
            optional_file = True,
            item_filter   = lambda item, pid: bool(item.get(pid)),
            item_expander = lambda item, pid: [
                {"TechId": item[pid], "MoId": m}
                for m in range(1, mo)
            ],
        )

    def update_RYTCn(self):
        self._execute_unified_update(
            "RYTCn", "rytcnPath", "RYTCn",
            item_filter   = lambda item, pid: bool(item.get("CM")),
            item_expander = lambda item, pid: [
                {"TechId": tech, "ConId": item["ConId"]}
                for tech in item["CM"]
            ],
        )

    # -------------------------------------------------------------------------
    # updateCase — preserved exactly
    # -------------------------------------------------------------------------

    def updateCase(self):
        try:
            registry = SchemaRegistry.instance().bind_to_class(self.__class__)
            for group, array in self.PARAMETERS.items():
                if array:
                    path = self.jsonPath[group]
                    existing_data = File.readFile(path) if os.path.exists(path) else None
                    data = registry.dispatch_update(self, group, existing_data=existing_data)
                    if isinstance(data, dict):
                        File.writeFile(data, path)
        except Exception as e:
            print(f"Error during case update at group {group}: {str(e)}")
            raise