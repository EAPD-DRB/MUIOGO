"""Read CLEWS case structure and reshape parameter rows into indexed lookups.

Group names describe dimensions: R=region, Y=year, T=technology, C=commodity,
E=emission, S=storage, M=mode, Ts=timeslice, and Cn=user-defined constraint.
Source tables use stable entity IDs; the export layer maps them to model codes.
"""

from pathlib import Path
import os
import platform
import shutil
import math
from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.HelpersClass import Helpers

_VIEW_INDEX_FIELDS = {
    't': 'TechId', 'f': 'CommId', 'e': 'EmisId',
    'l': 'TsId', 'm': 'MoId', 'cn': 'ConId',
}

class Osemosys():
    # The OSeMOSYS model file every solve uses. The model-file page
    # (/readModelFile) reads the same name, so the two can never disagree.
    MODEL_FILE_NAME = 'model.v.5.7withStorageFixNoPerformance.txt'

    def __init__(self, case):
        Config.validate_path(Config.DATA_STORAGE, case)
        self.case = case
        self.storagePath = Path(Config.DATA_STORAGE)
        self.casePath = self.storagePath / case

        self.PARAMETERS = File.readParamFile(self.storagePath / 'Parameters.json')
        self.VARIABLES = File.readParamFile(self.storagePath / 'Variables.json')
        # Optional catalogs may be absent in older installations. Keep opening
        # those cases possible; supplied definitions drive the result exports.
        self.DUALS = self._safe_read_param_file(self.storagePath / 'Duals.json')
        self.INDICATORS = self._safe_read_param_file(self.storagePath / 'Indicators.json')
        self.genData =  File.readFile(self.casePath / 'genData.json')
        # Pre-v5.6 cases never had osy-indicators; guard so opening them does
        # not KeyError. `or []` also normalizes the "key present but null"
        # case so downstream iterations are safe.
        self.customIndicators = self.genData.get('osy-indicators') or []
        self.resData = File.readFile(self.casePath / 'view' / 'resData.json')

        #Case.__init__(self, case)
        self.zipPath = self.storagePath / (case + '.zip')

        self.rPath = self.casePath / 'R.json'
        self.ryPath = self.casePath / 'RY.json'
        self.rtPath = self.casePath / 'RT.json'
        self.rePath = self.casePath / 'RE.json'
        self.rsPath = self.casePath / 'RS.json'
        self.rycnPath = self.casePath / 'RYCn.json'
        self.rytPath = self.casePath / 'RYT.json'
        self.rysPath = self.casePath / 'RYS.json'
        self.rytcnPath = self.casePath / 'RYTCn.json'
        self.rytmPath = self.casePath / 'RYTM.json'
        self.rytcPath = self.casePath / 'RYTC.json'
        self.rytcmPath = self.casePath / 'RYTCM.json'
        self.rytsmPath = self.casePath / 'RYTSM.json'
        self.rtsmPath = self.casePath / 'RTSM.json'
        self.rytsPath = self.casePath / 'RYTs.json'
        self.rydtbPath = self.casePath / 'RYDtb.json'
        self.rysedtPath = self.casePath / 'RYSeDt.json'
        self.rycPath = self.casePath / 'RYC.json'
        self.ryePath = self.casePath / 'RYE.json'
        self.ryttsPath = self.casePath / 'RYTTs.json'
        self.ryctsPath = self.casePath / 'RYCTs.json'
        self.rytePath = self.casePath / 'RYTE.json'
        self.rytemPath = self.casePath / 'RYTEM.json'

        self.osemosysFile = Path(Config.SOLVERs_FOLDER, self.MODEL_FILE_NAME)
        self.osemosysFileOriginal = Path(Config.SOLVERs_FOLDER,'osemosys.txt')
        self._glpkFolder = None
        self._cbcFolder = None
        self._glpsol_is_bundled = None
        self._cbc_is_bundled = None

        self.resultsPath = self.casePath / 'res'
        self.viewFolderPath = self.casePath / 'view'

        self.resDataPath = self.viewFolderPath / 'resData.json'

        self.PARAM = Helpers.build_param(self.PARAMETERS)
        self.VARS = Helpers.build_vars(self.VARIABLES)
        self.VAR_BY_NAME = Helpers.build_var_by_name(self.VARIABLES)
        # Index result definitions by solver name once, including annual
        # commodity prices from Duals.json and case-specific custom indicators.
        tech_map = self.getTechsMap()
        self.IND_BY_NAME = Helpers.merge_all_indicators(self.INDICATORS, self.customIndicators, tech_map)
        self.IND_GROUPED = Helpers.merge_all_indicators_grouped(self.INDICATORS, self.customIndicators, tech_map)
        self.DUALS_BY_NAME = Helpers.build_var_by_name(self.DUALS)

    @property
    def glpkFolder(self):
        if self._glpkFolder is None:
            self._glpkFolder, self._glpsol_is_bundled = self._resolve_solver_folder(
                env_var="SOLVER_GLPK_PATH",
                binary_name="glpsol",
                bundled_path=Path(Config.SOLVERs_FOLDER, "GLPK"),
            )
        return self._glpkFolder

    @property
    def cbcFolder(self):
        if self._cbcFolder is None:
            self._cbcFolder, self._cbc_is_bundled = self._resolve_solver_folder(
                env_var="SOLVER_CBC_PATH",
                binary_name="cbc",
                bundled_path=Path(Config.SOLVERs_FOLDER, "COIN-OR"),
            )
        return self._cbcFolder

    @property
    def glpsol_is_bundled(self):
        # Trigger lazy resolution so _glpsol_is_bundled gets set.
        _ = self.glpkFolder
        return bool(self._glpsol_is_bundled)

    @property
    def cbc_is_bundled(self):
        _ = self.cbcFolder
        return bool(self._cbc_is_bundled)

    @staticmethod
    def _safe_read_param_file(path: Path) -> dict:
        """Read a param JSON file, returning {} when the file is missing or
        unreadable. Used for Duals.json / Indicators.json which MUIO 5.6 reads
        but upstream forgot to commit. We ship empty stubs but should still
        survive if those go missing on a given deploy."""
        try:
            return File.readParamFile(path)
        except (FileNotFoundError, IOError, OSError):
            return {}

    @staticmethod
    def _solver_binary_names(binary_name: str):
        names = [binary_name]
        if platform.system() == "Windows" and not binary_name.lower().endswith(".exe"):
            names.insert(0, f"{binary_name}.exe")
        return names

    @staticmethod
    def _find_solver_binary(path: Path, binary_name: str, recursive: bool = False):
        binary_names = Osemosys._solver_binary_names(binary_name)

        if path.is_file():
            lowered_names = {name.lower() for name in binary_names}
            return path if path.name.lower() in lowered_names else None

        if not path.is_dir():
            return None

        for name in binary_names:
            candidate = path / name
            if candidate.is_file():
                return candidate

        if recursive:
            for name in binary_names:
                for candidate in path.rglob(name):
                    if candidate.is_file():
                        return candidate

        return None

    @staticmethod
    def _resolve_solver_folder(env_var: str, binary_name: str, bundled_path: Path):
        """Resolve a solver binary folder using a four-tier priority chain.

        Tiers:
          1. Environment variable (e.g. SOLVER_GLPK_PATH) — set by setup script.
          2. System PATH via shutil.which.
          3. Standard install locations per platform (MUIO 5.6 inheritance):
             macOS: /opt/homebrew/bin, /usr/local/bin, /usr/bin
             Linux: /usr/bin, /usr/local/bin, /bin, /snap/bin
          4. Bundled binary folder inside SOLVERs_FOLDER.

        Returns (folder, is_bundled) — is_bundled is True only when the binary
        was found in the bundled SOLVERs_FOLDER (tier 4). Used by DataFileClass.run
        to decide whether the subprocess cwd should be the solver folder
        (bundled, so adjacent DLLs resolve) or None (system install).

        Raises RuntimeError when resolution is attempted and no solver can be
        located, instead of silently storing a wrong path and failing mid-run.
        """
        env_val = os.environ.get(env_var, "").strip().strip("\"'")
        if env_val:
            env_path = Path(env_val).expanduser()
            env_binary = Osemosys._find_solver_binary(env_path, binary_name, recursive=False)
            if env_binary is not None:
                return env_binary.resolve().parent, False

            raise RuntimeError(
                f"{env_var} is set to '{env_val}', but no '{binary_name}' binary was found there.\n"
                f"Set {env_var} to the solver executable or to the directory containing it."
            )

        for solver_name in Osemosys._solver_binary_names(binary_name):
            which = shutil.which(solver_name)
            if which:
                return Path(which).resolve().parent, False

        system = platform.system()
        if system == "Darwin":
            standard_paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
        elif system == "Linux":
            standard_paths = ["/usr/bin", "/usr/local/bin", "/bin", "/snap/bin"]
        else:
            standard_paths = []

        for p in standard_paths:
            candidate = Osemosys._find_solver_binary(Path(p), binary_name, recursive=False)
            if candidate is not None:
                return candidate.resolve().parent, False

        bundled_binary = Osemosys._find_solver_binary(bundled_path, binary_name, recursive=True)
        if bundled_binary is not None:
            return bundled_binary.resolve().parent, True

        raise RuntimeError(
            f"Solver binary '{binary_name}' could not be found.\n"
            f"Set {env_var}, install '{binary_name}' on PATH, or provide bundled binaries under '{bundled_path}'."
        )

    def getParamDefaultValues(self):
        d = {}
        for k, l in self.PARAMETERS.items():
            for de in l:
                d[de['id']] = de['default']
        return d

    def keys_exists(self, element, *keys):
        '''
        Check if *keys (nested) exists in `element` (dict).
        '''
        if not isinstance(element, dict):
            raise AttributeError('keys_exists() expects dict as first argument.')
        if len(keys) == 0:
            raise AttributeError('keys_exists() expects at least two arguments, one given.')

        _element = element
        for key in keys:
            try:
                _element = _element[key]
            except KeyError:
                return False
        return True
        
    def getYears(self):
        return self.genData['osy-years']

    def getTsIds(self):
        return [ ts['TsId'] for ts in self.genData["osy-ts"]]

    def getTsMap(self):
        return {tech['TsId']: tech['Ts'] for tech in self.genData["osy-ts"] }

    def getTsNames(self):
        return [ ts['Ts'] for ts in self.genData["osy-ts"]]

    def getMods(self):
        mo = int(self.genData['osy-mo'])+1
        mods = []
        for m in range(1, mo):
            mods.append(m)
        return mods 

    def getTechIds(self):
        return [ tech['TechId'] for tech in self.genData["osy-tech"]]

    def getTechNames(self):
        return [ tech['Tech'] for tech in self.genData["osy-tech"]]

    def getTechs(self):
        return [ {tech['TechId']:tech['Tech']} for tech in self.genData["osy-tech"]]

    def getTechsMap(self):
        return {tech['TechId']: tech['Tech'] for tech in self.genData["osy-tech"] }
    
    def getEmiIds(self):
        return [ tech['EmisId'] for tech in self.genData["osy-emis"]]

    def getEmiNames(self):
        return [ tech['Emis'] for tech in self.genData["osy-emis"]]
    
    def getEmis(self):
        return [ {tech['EmisId']: tech['Emis']} for tech in self.genData["osy-emis"]]

    def getEmisMap(self):
        return {tech['EmisId']: tech['Emis'] for tech in self.genData["osy-emis"] }

    def getStgs(self):
        return [ {stg['StgId']: stg['Stg']} for stg in self.genData["osy-stg"]]
    
    def getStgNames(self):
        return [ stg['Stg'] for stg in self.genData["osy-stg"]]
    
    def getStgIds(self):
        return [ stg['StgId'] for stg in self.genData["osy-stg"]]
    
    def getStgMap(self):
        return {stg['StgId']: stg['Stg'] for stg in self.genData["osy-stg"] }
    
    def getStgByType(self):
        stgByType = {}
        for stg in self.genData["osy-stg"]:
            if stg['Operation'] not in stgByType:
                stgByType[stg['Operation']] = []
            stgByType[stg['Operation']].append(stg['Stg'])
        return stgByType

    def getSeIds(self):
        return [ se['SeId'] for se in self.genData["osy-se"]]
    
    def getSeMap(self):
        return { se['SeId']: se['Se'] for se in self.genData["osy-se"] }

    def getDtIds(self):
        return [ se['DtId'] for se in self.genData["osy-dt"]]
    
    def getDtMap(self):
        return { se['DtId']: se['Dt'] for se in self.genData["osy-dt"] }

    def getDtbIds(self):
        return [ se['DtbId'] for se in self.genData["osy-dtb"]]
    
    def getDtbMap(self):
        return { se['DtbId']: se['Dtb'] for se in self.genData["osy-dtb"] }

    def getCommIds(self):
        return [ tech['CommId'] for tech in self.genData["osy-comm"]]
    
    def getCommNames(self):
        return [ tech['Comm'] for tech in self.genData["osy-comm"]]

    def getComms(self):
        return [ {tech['CommId']: tech['Comm']} for tech in self.genData["osy-comm"]]

    def getCommsMap(self):
        return {tech['CommId']: tech['Comm'] for tech in self.genData["osy-comm"] }
    
    #23052026 - dodali smo funkciju koja vraca sve comm liste, jednu sa svim comm, a ostale po levelu Blaancing levels

    def getAllCommLists(self):
        result = {
            "ALL": [],
            "Ts": [],
            "Se": [],
            "An": []
        }

        for tech in self.genData["osy-comm"]:
            comm = tech["Comm"]
            # Cases saved before MUIO 5.7 have no BalanceLevel: they were balanced
            # per timeslice, so keep that. An unknown level would leave the
            # commodity in no balance set at all, so refuse it instead.
            level = tech.get("BalanceLevel") or "Ts"
            if level not in ("Ts", "Se", "An"):
                raise ValueError(
                    "Commodity '{}' has an unknown balance level '{}' "
                    "(expected Ts, Se or An).".format(comm, level))

            result["ALL"].append(comm)
            result[level].append(comm)

        return result

    def getConIds(self):
        return [ tech['ConId'] for tech in self.genData["osy-constraints"]]

    def getConsMap(self):
        return {con['ConId']: con['Con'] for con in self.genData["osy-constraints"] }

    def getScenariosByCase(self):
        scBycs = {}
        for case in self.resData["osy-cases"]:
            scBycs[case['Case']] = []
            for sc in case['Scenarios']:
                chunk = {}
                chunk['ScId'] = sc['ScenarioId']
                chunk['Sc'] = sc['Scenario']
                chunk['Active'] = sc['Active']
                scBycs[case['Case']].append(chunk)
        return scBycs

    def getScOrder(self, caserunname):
        """Return the stored scenario order; later active non-null values win."""
        scenarioBycase = self.getScenariosByCase()
        return scenarioBycase[caserunname]

    def getStorageTechIds(self):
        techIds = {}
        for param in self.PARAMETERS['RTSM']:
            techIds[param['id']] = {}
            for stg in self.genData["osy-stg"]:
                if stg[param['id']]: 
                    techIds[param['id']][stg['StgId']]=[]
                    techIds[param['id']][stg['StgId']].append(stg[param['id']])
        return techIds
    
    #output actTech['IAR'] = ['Tech_1', 'Tech_2'...]
    def getActivityTechIds(self):
        techIds = {}
        for param in self.PARAMETERS['RYTCM']:
            techIds[param['id']] = []
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    techIds[param['id']].append(tech['TechId'])
        return techIds

    #output actTech['IAR']['Tech_1'] = ['Comm_1', 'Comm_2'...]
    def getActivityCommIds(self):
        commIds = {}
        for param in self.PARAMETERS['RYTCM']:
            commIds[param['id']] = {}
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    commIds[param['id']][tech['TechId']] = tech[param['id']]
        return commIds

    #output actTech['INCR'] = ['Tech_1', 'Tech_2'...]
    def getInputCapTechIds(self):
        techIds = {}
        for param in self.PARAMETERS['RYTC']:
            techIds[param['id']] = []
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    techIds[param['id']].append(tech['TechId'])
        return techIds

    #output actTech['INCR']['Tech_1'] = ['Comm_1', 'Comm_2'...]
    def getInputCapCommIds(self):
        commIds = {}
        for param in self.PARAMETERS['RYTC']:
            commIds[param['id']] = {}
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    commIds[param['id']][tech['TechId']] = tech[param['id']]
        return commIds 

    def getConstraintTechIds(self):
        techIds = {}
        for param in self.PARAMETERS['RYTCn']:
            techIds[param['id']] = {}
            for con in self.genData["osy-constraints"]:
                # if con[param['id']]: 
                if con['CM']: 
                    techIds[param['id']][con['ConId']] = []
                    # for tech in con[param['id']]:
                    for tech in con['CM']:
                        techIds[param['id']][con['ConId']].append(tech)
        return techIds

    def getActivityEmissionTechIds(self):
        techIds = {}
        for param in self.PARAMETERS['RYTEM']:
            techIds[param['id']] = []
            for tech in self.genData["osy-tech"]:
                #dodali smo novi paramtear pored EAR imamo i EACR, sad se uslov mora promijneniti
                #if tech[param['id']]: 
                if tech['EAR']: 
                    techIds[param['id']].append(tech['TechId'])
        return techIds

    def getActivityEmisionIds(self):
        commIds = {}
        for param in self.PARAMETERS['RYTEM']:
            commIds[param['id']] = {}
            for tech in self.genData["osy-tech"]:
                #dodali smo novi paramtear pored EAR imamo i EACR, sad se uslov mora promijneniti
                # if tech[param['id']]: 
                #     commIds[param['id']][tech['TechId']] = tech[param['id']]
                if tech['EAR']: 
                    commIds[param['id']][tech['TechId']] = tech['EAR']
        return commIds

    def R(self, Rdata):
        R = {}
        for param, obj1 in Rdata.items():
            R[param] = {}
            for sc, array in obj1.items():
                R[param][sc] = {}
                for o in array:
                    R[param][sc]['value'] = o['value']
                        
        return R

    def RCn(self):
        RCn = {}
        for con in self.genData["osy-constraints"]:
            RCn[con['ConId']] = con['Tag']
        return RCn

    def RY(self, RYdata):
        RY = {}
        for param, obj1 in RYdata.items():
            RY[param] = {}
            for sc, array in obj1.items():
                RY[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        RY[param][sc][year] = val
        return RY

    def RT(self, RTdata):
        RT = {}
        for param, obj1 in RTdata.items():
            RT[param] = {}
            for sc, array in obj1.items():
                RT[param][sc] = {}
                for o in array:
                    for tech, val in o.items():
                        RT[param][sc][tech] = val
        return RT

    def RE(self, REdata):
        RE = {}
        for param, obj1 in REdata.items():
            RE[param] = {}
            for sc, array in obj1.items():
                RE[param][sc] = {}
                for o in array:
                    for emi, val in o.items():
                        RE[param][sc][emi] = val
        return RE

    def RS(self, RSdata):
        RS = {}
        for param, obj in RSdata.items():
            RS[param] = {}
            for sc, array in obj.items():
                RS[param][sc] = {}
                for o in array:
                    for stg, val in o.items():
                        RS[param][sc][stg] = val
        return RS
     
    def RTSM(self, RTSMdata):
        RTSM = {}
        for param, obj1 in RTSMdata.items():
            RTSM[param] = {}
            for sc, array in obj1.items():
                RTSM[param][sc] = {}
                for obj in array:
                    for value, val in obj.items():
                        if (value != 'TechId' and value != 'StgId' and value != 'MoId'):

                            if obj['StgId'] not in RTSM[param][sc]:
                                RTSM[param][sc][obj['StgId']] = {}
                            if obj['TechId'] not in RTSM[param][sc][obj['StgId']]:
                                RTSM[param][sc][obj['StgId']][obj['TechId']] = {}
                            RTSM[param][sc][obj['StgId']][obj['TechId']][obj['MoId']] = val
        return RTSM
    
    def RYCn(self, RYCndata):
        RYCn = {}
        for param, obj1 in RYCndata.items():
            RYCn[param] = {}
            for sc, array in obj1.items():
                RYCn[param][sc] = {}
                for o in array:
                    for year, val in o.items():
                        if (year != 'ConId'):
                            if year not in RYCn[param][sc]:
                                RYCn[param][sc][year] = {}   
                            RYCn[param][sc][year][o['ConId']] = val
        return RYCn

    def RYT(self, RYTdata):
        RYT = {}
        for param, obj1 in RYTdata.items():
            RYT[param] = {}
            for sc, array in obj1.items():
                RYT[param][sc] = {}
                for o in array:
                    for year, val in o.items():
                        if (year != 'TechId'):
                            if year not in RYT[param][sc]:
                                RYT[param][sc][year] = {}   
                            RYT[param][sc][year][o['TechId']] = val
        return RYT

    def RYS(self, RYSdata):
        RYS = {}
        for param, obj in RYSdata.items():
            RYS[param] = {}
            for sc, array in obj.items():
                RYS[param][sc] = {}
                for o in array:
                    for year, val in o.items():
                        if (year != 'StgId'):
                            if year not in RYS[param][sc]:
                                RYS[param][sc][year] = {}   
                            RYS[param][sc][year][o['StgId']] = val
        return RYS
    
    def RYTCn(self, RYTCndata):
        RYTCn = {}
        for param, obj1 in RYTCndata.items():
            RYTCn[param] = {}
            for sc, array in obj1.items():
                RYTCn[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'ConId'):
                            if year not in RYTCn[param][sc]:
                                RYTCn[param][sc][year] = {}
                            if obj['TechId'] not in RYTCn[param][sc][year]:
                                RYTCn[param][sc][year][obj['TechId']] = {}
                            RYTCn[param][sc][year][obj['TechId']][obj['ConId']] = val
        return RYTCn

    def RYTM(self, RYTMdata):
        RYTM = {}
        for param, obj1 in RYTMdata.items():
            RYTM[param] = {}
            for sc, array in obj1.items():
                RYTM[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'MoId'):
                            if year not in RYTM[param][sc]:
                                RYTM[param][sc][year] = {}
                            if obj['TechId'] not in RYTM[param][sc][year]:
                                RYTM[param][sc][year][obj['TechId']] = {}
                            RYTM[param][sc][year][obj['TechId']][obj['MoId']] = val
        return RYTM

    def RYC(self, RYCdata):
        RYC = {}
        for param, obj1 in RYCdata.items():
            RYC[param] = {}
            for sc, array in obj1.items():
                RYC[param][sc] = {}
                for o in array:
                    for year, val in o.items():
                        if (year != 'CommId'):
                            if year not in RYC[param][sc]:
                                RYC[param][sc][year] = {}
                            RYC[param][sc][year][o['CommId']] = val
        return RYC

    def RYE(self, RYEdata):
        RYE = {}
        for param, obj1 in RYEdata.items():
            RYE[param] = {}
            for sc, array in obj1.items():
                RYE[param][sc] = {}
                for o in array:
                    for year, val in o.items():
                        if year not in RYE[param][sc]:
                            RYE[param][sc][year] = {}
                        if (year != 'EmisId'):
                            RYE[param][sc][year][o['EmisId']] = val
        return RYE

    def RYTs(self, RYTsdata):
        RYTs = {}
        for param, obj1 in RYTsdata.items():
            RYTs[param] = {}
            for sc, array in obj1.items():
                RYTs[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TsId'):
                            if year not in RYTs[param][sc]:
                                RYTs[param][sc][year] = {}
                            RYTs[param][sc][year][obj['TsId']] = val
        return RYTs

    def RYDtb(self, RYDtbdata):
        RYDtb = {}
        for param, obj1 in RYDtbdata.items():
            RYDtb[param] = {}
            for sc, array in obj1.items():
                RYDtb[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'DtbId'):
                            if year not in RYDtb[param][sc]:
                                RYDtb[param][sc][year] = {}
                            RYDtb[param][sc][year][obj['DtbId']] = val
        return RYDtb
    
    def RYSeDt(self, RYSeDtdata):
        RYSeDt = {}
        for param, obj1 in RYSeDtdata.items():
            RYSeDt[param] = {}
            for sc, array in obj1.items():
                RYSeDt[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'SeId' and year != 'DtId'):
                            if year not in RYSeDt[param][sc]:
                                RYSeDt[param][sc][year] = {} 
                            if obj['SeId'] not in RYSeDt[param][sc][year]:
                                RYSeDt[param][sc][year][obj['SeId']] = {}
                            RYSeDt[param][sc][year][obj['SeId']][obj['DtId']] = val
        return RYSeDt
    
    def RYTC(self, RYTCdata):
        RYTC = {}
        for param, obj1 in RYTCdata.items():
            RYTC[param] = {}
            for sc, array in obj1.items():
                RYTC[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'CommId'):
                            if year not in RYTC[param][sc]:
                                RYTC[param][sc][year] = {}
                            if obj['TechId'] not in RYTC[param][sc][year]:
                                RYTC[param][sc][year][obj['TechId']] = {}
                            RYTC[param][sc][year][obj['TechId']][obj['CommId']] = val
        return RYTC

    def RYTCM(self, RYTCMdata):
        RYTCM = {}
        for param, obj1 in RYTCMdata.items():
            RYTCM[param] = {}
            for sc, array in obj1.items():
                RYTCM[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'CommId' and year != 'MoId'):
                            if year not in RYTCM[param][sc]:
                                RYTCM[param][sc][year] = {}
                            if obj['TechId'] not in RYTCM[param][sc][year]:
                                RYTCM[param][sc][year][obj['TechId']] = {}
                            if obj['CommId'] not in RYTCM[param][sc][year][obj['TechId']]:
                                RYTCM[param][sc][year][obj['TechId']][obj['CommId']] = {}
                            RYTCM[param][sc][year][obj['TechId']][obj['CommId']][obj['MoId']] = val
        return RYTCM

    def RYTSM(self, RYTSMdata):
        RYTSM = {}
        for param, obj1 in RYTSMdata.items():
            RYTSM[param] = {}
            for sc, array in obj1.items():
                RYTSM[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'StgId' and year != 'MoId'):
                            if year not in RYTSM[param][sc]:
                                RYTSM[param][sc][year] = {}
                            if obj['StgId'] not in RYTSM[param][sc][year]:
                                RYTSM[param][sc][year][obj['StgId']] = {}
                            if obj['TechId'] not in RYTSM[param][sc][year][obj['StgId']]:
                                RYTSM[param][sc][year][obj['StgId']][obj['TechId']] = {}
                            RYTSM[param][sc][year][obj['StgId']][obj['TechId']][obj['MoId']] = val
        return RYTSM
    
    def RYTE(self, RYTEdata):
        RYTE = {}
        for param, obj1 in RYTEdata.items():
            RYTE[param] = {}
            for sc, array in obj1.items():
                RYTE[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'EmisId'):
                            if year not in RYTE[param][sc]:
                                RYTE[param][sc][year] = {}
                            if obj['TechId'] not in RYTE[param][sc][year]:
                                RYTE[param][sc][year][obj['TechId']] = {}
                            RYTE[param][sc][year][obj['TechId']][obj['EmisId']] = val
        return RYTE

    def RYTEM(self, RYTEMdata):
        RYTEM = {}
        for param, obj1 in RYTEMdata.items():
            RYTEM[param] = {}
            for sc, array in obj1.items():
                RYTEM[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'EmisId' and year != 'MoId'):
                            if year not in RYTEM[param][sc]:
                                RYTEM[param][sc][year] = {}
                            if obj['TechId'] not in RYTEM[param][sc][year]:
                                RYTEM[param][sc][year][obj['TechId']] = {}
                            if obj['EmisId'] not in RYTEM[param][sc][year][obj['TechId']]:
                                RYTEM[param][sc][year][obj['TechId']][obj['EmisId']] = {}
                            RYTEM[param][sc][year][obj['TechId']][obj['EmisId']][obj['MoId']] = val
        return RYTEM

    def RYTTs(self, RYTTsdata):
        RYTTs = {}
        for param, obj1 in RYTTsdata.items():
            RYTTs[param] = {}
            for sc, array in obj1.items():
                RYTTs[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'TechId' and year != 'TsId'):
                            if year not in RYTTs[param][sc]:
                                RYTTs[param][sc][year] = {}
                            if obj['TechId'] not in RYTTs[param][sc][year]:
                                RYTTs[param][sc][year][obj['TechId']] = {}
                            RYTTs[param][sc][year][obj['TechId']][obj['TsId']] = val
        return RYTTs

    def RYCTs(self, RYCTsdata):
        RYCTs = {}
        for param, obj1 in RYCTsdata.items():
            RYCTs[param] = {}
            for sc, array in obj1.items():
                RYCTs[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        if (year != 'CommId' and year != 'TsId'):
                            if year not in RYCTs[param][sc]:
                                RYCTs[param][sc][year] = {} 
                            if obj['CommId'] not in RYCTs[param][sc][year]:
                                RYCTs[param][sc][year][obj['CommId']] = {}
                            RYCTs[param][sc][year][obj['CommId']][obj['TsId']] = val
        return RYCTs

    def viewDataByTech(self):
        jsonData = {}
        data = {}
        for tech in self.genData["osy-tech"]:
            data[tech['TechId']] = []
            for group, array in self.PARAMETERS.items():
                if group in Config.TECH_GROUPS:
                    jsonData[group] =  File.readFile(Path(Config.DATA_STORAGE,self.case, group+'.json'))
                    for obj in array:
                        byTech = {}
                        byTech['groupId'] = group
                        byTech['param'] = obj['id']
                        byTech['paramName'] = obj['value']
                        for sc, array in jsonData[group][obj['id']].items():
                            byTech['ScId'] = sc
                            for obj2 in array:
                                if obj2['TechId'] == tech['TechId']:
                                    byTech['TechId'] = tech['TechId']
                                    if 'CommId' not in obj:
                                        byTech['CommId'] = None
                                    if 'EmisId' not in obj:
                                        byTech['EmisId'] = None
                                    if 'ConId' not in obj:
                                        byTech['ConId'] = None
                                    if 'TsId' not in obj:
                                        byTech['TsId'] = None
                                    if 'MoId' not in obj:
                                        byTech['MoId'] = None
                                    for k,v in obj2.items():
                                        if k != 'TechId':
                                            byTech[k] = v
                                    data[tech['TechId']].append(byTech.copy())
        return data

    def viewDataByComm(self):
        jsonData = {}
        data = {}
        for tech in self.genData["osy-comm"]:
            data[tech['CommId']] = []
            for group, array in self.PARAMETERS.items():
                if group in Config.COMM_GROUPS:
                    jsonData[group] =  File.readFile(Path(Config.DATA_STORAGE,self.case, group+'.json'))
                    for obj in array:
                        byComm = {}
                        byComm['groupId'] = group
                        byComm['param'] = obj['id']
                        byComm['paramName'] = obj['value']
                        for sc, array in jsonData[group][obj['id']].items():
                            byComm['ScId'] = sc
                            for obj2 in array:
                                if obj2['CommId'] == tech['CommId']:
                                    byComm['CommId'] = tech['CommId']
                                    if 'TechId' not in obj:
                                        byComm['TechId'] = None
                                    if 'EmisId' not in obj:
                                        byComm['EmisId'] = None
                                    if 'ConId' not in obj:
                                        byComm['ConId'] = None
                                    if 'TsId' not in obj:
                                        byComm['TsId'] = None
                                    if 'MoId' not in obj:
                                        byComm['MoId'] = None
                                    for k,v in obj2.items():
                                        if k != 'CommId':
                                            byComm[k] = v
                                    data[tech['CommId']].append(byComm.copy())
        return data

    def viewDataByEmi(self):
        jsonData = {}
        data = {}
        for tech in self.genData["osy-emis"]:
            data[tech['EmisId']] = []
            for group, array in self.PARAMETERS.items():
                if group in Config.EMIS_GROUPS:
                    jsonData[group] =  File.readFile(Path(Config.DATA_STORAGE,self.case, group+'.json'))
                    for obj in array:
                        byEmi = {}
                        byEmi['groupId'] = group
                        byEmi['param'] = obj['id']
                        byEmi['paramName'] = obj['value']
                        for sc, array in jsonData[group][obj['id']].items():
                            byEmi['ScId'] = sc
                            for obj2 in array:
                                if obj2['EmisId'] == tech['EmisId']:
                                    byEmi['EmisId'] = tech['EmisId']
                                    if 'TechId' not in obj:
                                        byEmi['TechId'] = None
                                    if 'CommId' not in obj:
                                        byEmi['CommId'] = None
                                    if 'ConId' not in obj:
                                        byEmi['ConId'] = None
                                    if 'TsId' not in obj:
                                        byEmi['TsId'] = None
                                    if 'MoId' not in obj:
                                        byEmi['MoId'] = None
                                    for k,v in obj2.items():
                                        if k != 'EmisId':
                                            byEmi[k] = v
                                    data[tech['EmisId']].append(byEmi.copy())
        return data

    def viewRTByTech(self):
        jsonData = {}
        data = {}
        for tech in self.genData["osy-tech"]:
            data[tech['TechId']] = []
            for group, array in self.PARAMETERS.items():
                if group in Config.SINGLE_TECH_GROUPS:
                    jsonData[group] =  File.readFile(Path(Config.DATA_STORAGE,self.case, group+'.json'))
                    for obj in array:
                        byTech = {}
                        byTech['groupId'] = group
                        byTech['param'] = obj['id']
                        byTech['paramName'] = obj['value']
                        for sc, array in jsonData[group][obj['id']].items():
                            byTech['ScId'] = sc
                            for obj2 in array:
                                for k,v in obj2.items():
                                    if k == tech['TechId']:
                                        byTech['value'] = v
                                data[tech['TechId']].append(byTech.copy())
        return data

    def viewREByEmi(self):
        jsonData = {}
        data = {}
        for tech in self.genData["osy-emis"]:
            data[tech['EmisId']] = []
            for group, array in self.PARAMETERS.items():
                if group in Config.SINGLE_EMIS_GROUPS:
                    jsonData[group] =  File.readFile(Path(Config.DATA_STORAGE,self.case, group+'.json'))
                    for obj in array:
                        byEmi = {}
                        byEmi['groupId'] = group
                        byEmi['param'] = obj['id']
                        byEmi['paramName'] = obj['value']
                        for sc, array in jsonData[group][obj['id']].items():
                            byEmi['ScId'] = sc
                            for obj2 in array:
                                for k,v in obj2.items():
                                    if k == tech['EmisId']:
                                        byEmi['value'] = v
                                data[tech['EmisId']].append(byEmi.copy())
        return data

    def _save_view_cell(self, group, param, scenario, ids, value, year=None):
        """Resolve one source cell; an unused dimension is not a wildcard.

        Parameters.json defines the indices. Reject incomplete or ambiguous
        selections before writing, including modes and user-defined constraints.
        """
        if not all(isinstance(key, str) and key for key in (group, param, scenario)):
            raise ValueError('Group, parameter and scenario must be identifiers.')
        allowed = (Config.TECH_GROUPS + Config.COMM_GROUPS + Config.EMIS_GROUPS
                   if year is not None else Config.SINGLE_TECH_GROUPS + Config.SINGLE_EMIS_GROUPS)
        if group not in allowed:
            raise ValueError('This parameter group cannot be edited in this view.')
        definition = next((p for p in self.PARAMETERS.get(group, []) if p['id'] == param), None)
        if definition is None:
            raise ValueError('Unknown parameter or parameter group.')
        dimensions = set(definition['setrelation'])
        if dimensions - {'r', 'y'} - _VIEW_INDEX_FIELDS.keys() or ('y' in dimensions) != (year is not None):
            raise ValueError('Unsupported parameter dimensions.')
        required = {_VIEW_INDEX_FIELDS[d] for d in dimensions if d in _VIEW_INDEX_FIELDS}
        selected = {key: val for key, val in ids.items() if val is not None}
        if selected.keys() != required:
            raise ValueError('Supply exactly the IDs required by this parameter.')
        for key, val in selected.items():
            if key == 'MoId':
                # jqx declares this grid field as a string; source modes are integers.
                if isinstance(val, str) and val.isascii() and val.isdecimal():
                    val = int(val)
                if type(val) is not int or val not in self.getMods():
                    raise ValueError('Invalid mode ID.')
                selected[key] = val
            elif not isinstance(val, str) or not val:
                raise ValueError(f'Invalid {key}.')
        if scenario not in {s['ScenarioId'] for s in self.genData['osy-scenarios']}:
            raise ValueError('Unknown scenario.')
        if year is not None:
            if type(year) not in (str, int) or str(year) not in {str(y) for y in self.getYears()}:
                raise ValueError('Unknown model year.')
            year = str(year)
        try:
            finite_value = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite_value = False
        if not finite_value:
            raise ValueError('The parameter value must be a finite number.')

        # The group is from the configured catalog, never an arbitrary file path.
        path = self.casePath / f'{group}.json'
        data = File.readFile(path)
        rows = data.get(param, {}).get(scenario)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError('The source parameter or scenario is missing.')
        if year is not None:
            matches = [row for row in rows if all(row.get(key) == val for key, val in selected.items())]
            column = year
        else:
            # RT/RE use entity IDs as dictionary keys rather than row index fields.
            if len(selected) != 1:
                raise ValueError('Select one technology or emission.')
            column = next(iter(selected.values()))
            matches = [row for row in rows if column in row]
        if len(matches) != 1 or column not in matches[0]:
            raise ValueError('The edit must identify exactly one existing cell.')
        matches[0][column] = value
        File.writeFile(data, path)

    def updateViewData(self, casename, year, ScId, GroupId, ParamId, TechId, CommId, EmisId, Timeslice, value,
                       MoId=None, ConId=None):
        if casename != self.case:
            raise ValueError('Case identity mismatch.')
        self._save_view_cell(GroupId, ParamId, ScId, {
            'TechId': TechId, 'CommId': CommId, 'EmisId': EmisId,
            'TsId': Timeslice, 'MoId': MoId, 'ConId': ConId,
        }, value, year=year)

    def updateTEViewData(self, casename, ScId, GroupId, ParamId, TechId, EmisId, value):
        if casename != self.case:
            raise ValueError('Case identity mismatch.')
        self._save_view_cell(GroupId, ParamId, ScId, {'TechId': TechId, 'EmisId': EmisId}, value)
