"""Core OSeMOSYS data access and transformation layer."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import platform
import shutil
from Classes.Base import Config
from Classes.Base.FileClass import File

class Osemosys():
    """Core OSeMOSYS model data access and transformation layer.

    Loads parameter definitions, variable definitions, and general model
    data for a given case.  Provides helper methods to reshape JSON
    parameter data, look up dimension IDs/names, and read/write view
    data.

    Attributes:
        case: Case name.
        PARAMETERS: Parameter definitions from ``Parameters.json``.
        VARIABLES: Variable definitions from ``Variables.json``.
        genData: General model data loaded from ``genData.json``.
        resData: Result metadata loaded from ``resData.json``.
        PARAM: Processed parameter name mapping.
        VARS: Flat list of variable names.
    """

    def __init__(self, case: str) -> None:
        """Initialise an Osemosys instance for the given case.

        Args:
            case: Case name (subdirectory under DataStorage).
        """
        self.case = case
        self.PARAMETERS = File.readParamFile(Path(Config.DATA_STORAGE, 'Parameters.json'))
        self.VARIABLES = File.readParamFile(Path(Config.DATA_STORAGE, 'Variables.json'))
        self.genData =  File.readFile(Path(Config.DATA_STORAGE,case,'genData.json'))
        self.resData = File.readFile( Path(Config.DATA_STORAGE, case,'view', 'resData.json'))
        
        #Case.__init__(self, case)
        self.casePath = Path(Config.DATA_STORAGE,case)
        self.zipPath = Path(Config.DATA_STORAGE,case+'.zip')

        #self.genData = Path(Config.DATA_STORAGE,case,'genData.json')

        self.rPath = Path(Config.DATA_STORAGE,case,'R.json')
        self.ryPath = Path(Config.DATA_STORAGE,case,'RY.json')
        self.rtPath = Path(Config.DATA_STORAGE,case,'RT.json')
        self.rePath = Path(Config.DATA_STORAGE,case,'RE.json')
        self.rsPath = Path(Config.DATA_STORAGE,case,'RS.json')
        self.rycnPath = Path(Config.DATA_STORAGE,case,'RYCn.json')
        self.rytPath = Path(Config.DATA_STORAGE,case,'RYT.json')
        self.rysPath = Path(Config.DATA_STORAGE,case,'RYS.json')
        self.rytcnPath = Path(Config.DATA_STORAGE,case,'RYTCn.json')
        self.rytmPath = Path(Config.DATA_STORAGE,case,'RYTM.json')
        self.rytcPath = Path(Config.DATA_STORAGE,case,'RYTC.json')
        self.rytcmPath = Path(Config.DATA_STORAGE,case,'RYTCM.json')
        self.rytsmPath = Path(Config.DATA_STORAGE,case,'RYTSM.json')
        self.rtsmPath = Path(Config.DATA_STORAGE,case,'RTSM.json')
        self.rytsPath = Path(Config.DATA_STORAGE,case,'RYTs.json')
        self.rydtbPath = Path(Config.DATA_STORAGE,case,'RYDtb.json')
        self.rysedtPath = Path(Config.DATA_STORAGE,case,'RYSeDt.json')
        self.rycPath = Path(Config.DATA_STORAGE,case,'RYC.json')
        self.ryePath = Path(Config.DATA_STORAGE,case,'RYE.json')
        self.ryttsPath = Path(Config.DATA_STORAGE,case,'RYTTs.json')
        self.ryctsPath = Path(Config.DATA_STORAGE,case,'RYCTs.json')
        self.rytePath = Path(Config.DATA_STORAGE,case,'RYTE.json')
        self.rytemPath = Path(Config.DATA_STORAGE,case,'RYTEM.json')

        
        self.osemosysFile = Path(Config.SOLVERs_FOLDER,'model.v.5.4.txt') 
        self.osemosysFileOriginal = Path(Config.SOLVERs_FOLDER,'osemosys.txt')
        self._glpkFolder = None
        self._cbcFolder = None

        self.resultsPath = Path(Config.DATA_STORAGE,case,'res')
        self.viewFolderPath = Path(Config.DATA_STORAGE,case,'view')
        
        self.resDataPath = Path(Config.DATA_STORAGE,case,'view', 'resData.json')

        # self.resPath = Path(Config.DATA_STORAGE,case,'res', 'csv')
        
        #self.dataFile = Path(Config.DATA_STORAGE,case, 'res','data.txt')
        # self.resFile = Path(Config.DATA_STORAGE,case, 'res','results.txt')
        # self.lpFile = Path(Config.DATA_STORAGE,case, 'res','lp.lp')
        # self.resCBCPath = Path('..', '..', '..', '..', 'WebAPP', 'DataStorage', case, 'res')
        # self.resPath = Path('..', '..', '..', '..', 'WebAPP', 'DataStorage', case, 'res', 'csv')

        d = {}
        for k, l in self.PARAMETERS.items():
            tmp = {}
            for de in l:
                tmp[de['id']] = (de['value'] or "").replace(" ", "")
            d[k] = tmp
        self.PARAM = d

        a=[]
        for k, l in self.VARIABLES.items():
            for de in l:
                a.append(de['name'])
        self.VARS = a

    @property
    def glpkFolder(self):
        if self._glpkFolder is None:
            self._glpkFolder = self._resolve_solver_folder(
                env_var="SOLVER_GLPK_PATH",
                binary_name="glpsol",
                bundled_path=Path(Config.SOLVERs_FOLDER, "GLPK"),
            )
        return self._glpkFolder

    @property
    def cbcFolder(self):
        if self._cbcFolder is None:
            self._cbcFolder = self._resolve_solver_folder(
                env_var="SOLVER_CBC_PATH",
                binary_name="cbc",
                bundled_path=Path(Config.SOLVERs_FOLDER, "COIN-OR"),
            )
        return self._cbcFolder

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
    def _resolve_solver_folder(env_var: str, binary_name: str, bundled_path: Path) -> Path:
        """Resolve a solver binary folder using a three-tier priority chain:

        1. Environment variable (e.g. SOLVER_GLPK_PATH)
        2. System PATH via shutil.which
        3. Bundled binary folder inside SOLVERs_FOLDER

        Raises RuntimeError when resolution is attempted and no solver can be
        located, instead of silently storing a wrong path and failing mid-run.
        """
        env_val = os.environ.get(env_var, "").strip().strip("\"'")
        if env_val:
            env_path = Path(env_val).expanduser()
            env_binary = Osemosys._find_solver_binary(env_path, binary_name, recursive=False)
            if env_binary is not None:
                return env_binary.resolve().parent

            raise RuntimeError(
                f"{env_var} is set to '{env_val}', but no '{binary_name}' binary was found there.\n"
                f"Set {env_var} to the solver executable or to the directory containing it."
            )

        for solver_name in Osemosys._solver_binary_names(binary_name):
            which = shutil.which(solver_name)
            if which:
                return Path(which).resolve().parent

        bundled_binary = Osemosys._find_solver_binary(bundled_path, binary_name, recursive=True)
        if bundled_binary is not None:
            return bundled_binary.resolve().parent

        raise RuntimeError(
            f"Solver binary '{binary_name}' could not be found.\n"
            f"Set {env_var}, install '{binary_name}' on PATH, or provide bundled binaries under '{bundled_path}'."
        )

    def getParamDefaultValues(self) -> Dict[str, Any]:
        """Return a mapping of parameter IDs to their default values.

        Returns:
            Dictionary keyed by parameter ID with default values.
        """
        d = {}
        for k, l in self.PARAMETERS.items():
            for de in l:
                d[de['id']] = de['default']
        return d

    def keys_exists(self, element: Dict[str, Any], *keys: str) -> bool:
        """Check whether a chain of nested keys exists in a dictionary.

        Args:
            element: The dictionary to inspect.
            *keys: Sequence of keys to look up, each level deeper.

        Returns:
            ``True`` if all keys exist in the nested structure.

        Raises:
            AttributeError: If *element* is not a dict or no keys given.
        """
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
        
    def getYears(self) -> List[str]:
        """Return the list of model years."""
        years = self.genData['osy-years']
        return years

    def getTsIds(self) -> List[str]:
        """Return timeslice IDs."""
        tsIds = [ ts['TsId'] for ts in self.genData["osy-ts"]]
        return tsIds

    def getTsMap(self) -> Dict[str, str]:
        """Return mapping of timeslice ID to timeslice name."""
        timeslices = {tech['TsId']: tech['Ts'] for tech in self.genData["osy-ts"] }
        return timeslices

    def getTsNames(self) -> List[str]:
        """Return timeslice names."""
        tsIds = [ ts['Ts'] for ts in self.genData["osy-ts"]]
        return tsIds    


    def getMods(self) -> List[int]:
        """Return list of mode-of-operation integers."""
        mo = int(self.genData['osy-mo'])+1
        mods = []
        for m in range(1, mo):
            mods.append(m)
        return mods 


    def getTechIds(self) -> List[str]:
        """Return technology IDs."""
        techIds = [ tech['TechId'] for tech in self.genData["osy-tech"]]
        return techIds

    def getTechNames(self) -> List[str]:
        """Return technology names."""
        techIds = [ tech['Tech'] for tech in self.genData["osy-tech"]]
        return techIds

    def getTechs(self) -> List[Dict[str, str]]:
        """Return list of tech ID-to-name dicts."""
        techs = [ {tech['TechId']:tech['Tech']} for tech in self.genData["osy-tech"]]
        return techs

    def getTechsMap(self) -> Dict[str, str]:
        """Return mapping of technology ID to name."""
        techs = {tech['TechId']: tech['Tech'] for tech in self.genData["osy-tech"] }
        return techs
    
    def getEmiIds(self) -> List[str]:
        """Return emission IDs."""
        emiIds = [ tech['EmisId'] for tech in self.genData["osy-emis"]]
        return emiIds

    def getEmiNames(self) -> List[str]:
        """Return emission names."""
        emiIds = [ tech['Emis'] for tech in self.genData["osy-emis"]]
        return emiIds
    
    def getEmis(self) -> List[Dict[str, str]]:
        """Return list of emission ID-to-name dicts."""
        emis = [ {tech['EmisId']: tech['Emis']} for tech in self.genData["osy-emis"]]
        return emis

    def getEmisMap(self) -> Dict[str, str]:
        """Return mapping of emission ID to name."""
        emis = {tech['EmisId']: tech['Emis'] for tech in self.genData["osy-emis"] }
        return emis

    def getStgs(self) -> List[Dict[str, str]]:
        """Return list of storage ID-to-name dicts."""
        stgs = [ {stg['StgId']: stg['Stg']} for stg in self.genData["osy-stg"]]
        return stgs
    
    def getStgNames(self) -> List[str]:
        """Return storage names."""
        stgs = [ stg['Stg'] for stg in self.genData["osy-stg"]]
        return stgs
    
    def getStgIds(self) -> List[str]:
        """Return storage IDs."""
        stgIds = [ stg['StgId'] for stg in self.genData["osy-stg"]]
        return stgIds
    
    def getStgMap(self) -> Dict[str, str]:
        """Return mapping of storage ID to name."""
        stgs = {stg['StgId']: stg['Stg'] for stg in self.genData["osy-stg"] }
        return stgs
    
    def getStgByType(self) -> Dict[str, List[str]]:
        """Return storages grouped by operation type."""
        stgByType = {}
        for stg in self.genData["osy-stg"]:
            if stg['Operation'] not in stgByType:
                stgByType[stg['Operation']] = []
            stgByType[stg['Operation']].append(stg['Stg'])
        return stgByType

    def getSeIds(self) -> List[str]:
        """Return season IDs."""
        seIds = [ se['SeId'] for se in self.genData["osy-se"]]
        return seIds
    
    def getSeMap(self) -> Dict[str, str]:
        """Return mapping of season ID to name."""
        ses = { se['SeId']: se['Se'] for se in self.genData["osy-se"] }
        return ses

    def getDtIds(self) -> List[str]:
        """Return day-type IDs."""
        seIds = [ se['DtId'] for se in self.genData["osy-dt"]]
        return seIds
    
    def getDtMap(self) -> Dict[str, str]:
        """Return mapping of day-type ID to name."""
        ses = { se['DtId']: se['Dt'] for se in self.genData["osy-dt"] }
        return ses

    def getDtbIds(self) -> List[str]:
        """Return daily-time-bracket IDs."""
        seIds = [ se['DtbId'] for se in self.genData["osy-dtb"]]
        return seIds
    
    def getDtbMap(self) -> Dict[str, str]:
        """Return mapping of daily-time-bracket ID to name."""
        ses = { se['DtbId']: se['Dtb'] for se in self.genData["osy-dtb"] }
        return ses

    def getCommIds(self) -> List[str]:
        """Return commodity IDs."""
        commIds = [ tech['CommId'] for tech in self.genData["osy-comm"]]
        return commIds
    
    def getCommNames(self) -> List[str]:
        """Return commodity names."""
        commIds = [ tech['Comm'] for tech in self.genData["osy-comm"]]
        return commIds

    def getComms(self) -> List[Dict[str, str]]:
        """Return list of commodity ID-to-name dicts."""
        comms = [ {tech['CommId']: tech['Comm']} for tech in self.genData["osy-comm"]]
        return comms

    def getCommsMap(self) -> Dict[str, str]:
        """Return mapping of commodity ID to name."""
        comms = {tech['CommId']: tech['Comm'] for tech in self.genData["osy-comm"] }
        return comms
    
    def getConIds(self) -> List[str]:
        """Return constraint IDs."""
        conIds = [ tech['ConId'] for tech in self.genData["osy-constraints"]]
        return conIds

    def getConsMap(self) -> Dict[str, str]:
        """Return mapping of constraint ID to name."""
        cons = {con['ConId']: con['Con'] for con in self.genData["osy-constraints"] }
        return cons

    # def getScIds(self):
    #     scIds = [ sc['ScenarioId'] for sc in self.genData["osy-scenarios"]]
    #     return scIds

    def getScenariosByCase(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return scenarios grouped by case-run name."""
        #scIds = [ sc['ScenarioId'] for sc in self.genData["osy-scenarios"]]
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

    def getScOrder(self, caserunname: str) -> List[Dict[str, Any]]:
        """Return ordered scenario list for a specific case run.

        Args:
            caserunname: Name of the case run.

        Returns:
            List of scenario dicts with ScId, Sc, and Active keys.
        """
        #scIds = [ {'ScId': sc['ScenarioId'], 'Sc': sc['Scenario'], 'Active': sc['Active']} for sc in self.genData["osy-scenarios"]]
        scenarioBycase = self.getScenariosByCase()
        scIds = scenarioBycase[caserunname]
        return scIds

    def getStorageTechIds(self) -> Dict[str, Dict[str, List[str]]]:
        """Return storage technology IDs per parameter and storage."""
        techIds = {}
        for param in self.PARAMETERS['RTSM']:
            techIds[param['id']] = {}
            for stg in self.genData["osy-stg"]:
                if stg[param['id']]: 
                    techIds[param['id']][stg['StgId']]=[]
                    techIds[param['id']][stg['StgId']].append(stg[param['id']])
                    # if techIds[param['id']][stg['StgId']]: 
                    #     techIds[param['id']][stg['StgId']].append(stg[param['id']])
                    # else:
                    #     techIds[param['id']][stg['StgId']]=[]
                    #     techIds[param['id']][stg['StgId']].append(stg[param['id']])
        return techIds
    
    #output actTech['IAR'] = ['Tech_1', 'Tech_2'...]
    def getActivityTechIds(self) -> Dict[str, List[str]]:
        """Return activity technology IDs per RYTCM parameter."""
        techIds = {}
        for param in self.PARAMETERS['RYTCM']:
            techIds[param['id']] = []
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    techIds[param['id']].append(tech['TechId'])
        return techIds

    #output actTech['IAR']['Tech_1'] = ['Comm_1', 'Comm_2'...]
    def getActivityCommIds(self) -> Dict[str, Dict[str, List[str]]]:
        """Return activity commodity IDs per parameter and technology."""
        commIds = {}
        for param in self.PARAMETERS['RYTCM']:
            commIds[param['id']] = {}
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    commIds[param['id']][tech['TechId']] = tech[param['id']]
        return commIds

    #output actTech['INCR'] = ['Tech_1', 'Tech_2'...]
    def getInputCapTechIds(self) -> Dict[str, List[str]]:
        """Return input-capacity technology IDs per RYTC parameter."""
        techIds = {}
        for param in self.PARAMETERS['RYTC']:
            techIds[param['id']] = []
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    techIds[param['id']].append(tech['TechId'])
        return techIds

    #output actTech['INCR']['Tech_1'] = ['Comm_1', 'Comm_2'...]
    def getInputCapCommIds(self) -> Dict[str, Dict[str, List[str]]]:
        """Return input-capacity commodity IDs per parameter and technology."""
        commIds = {}
        for param in self.PARAMETERS['RYTC']:
            commIds[param['id']] = {}
            for tech in self.genData["osy-tech"]:
                if tech[param['id']]: 
                    commIds[param['id']][tech['TechId']] = tech[param['id']]
        return commIds 

    def getConstraintTechIds(self) -> Dict[str, Dict[str, List[str]]]:
        """Return constraint technology IDs per parameter and constraint."""
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

    def getActivityEmissionTechIds(self) -> Dict[str, List[str]]:
        """Return activity-emission technology IDs per RYTEM parameter."""
        techIds = {}
        for param in self.PARAMETERS['RYTEM']:
            techIds[param['id']] = []
            for tech in self.genData["osy-tech"]:
                #dodali smo novi paramtear pored EAR imamo i EACR, sad se uslov mora promijneniti
                #if tech[param['id']]: 
                if tech['EAR']: 
                    techIds[param['id']].append(tech['TechId'])
        return techIds

    def getActivityEmisionIds(self) -> Dict[str, Dict[str, List[str]]]:
        """Return activity emission IDs per parameter and technology."""
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

    def R(self, Rdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *R* parameter JSON into a flat lookup."""
        R = {}
        for param, obj1 in Rdata.items():
            R[param] = {}
            for sc, array in obj1.items():
                R[param][sc] = {}
                for o in array:
                    R[param][sc]['value'] = o['value']
                        
        return R

    def RCn(self) -> Dict[str, Any]:
        """Build constraint tag lookup from general data."""
        RCn = {}
        for con in self.genData["osy-constraints"]:
            RCn[con['ConId']] = con['Tag']
        return RCn

    def RY(self, RYdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RY* parameter JSON into a flat lookup."""
        RY = {}
        for param, obj1 in RYdata.items():
            RY[param] = {}
            for sc, array in obj1.items():
                RY[param][sc] = {}
                for obj in array:
                    for year, val in obj.items():
                        RY[param][sc][year] = val
        return RY

    def RT(self, RTdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RT* parameter JSON into a flat lookup."""
        RT = {}
        for param, obj1 in RTdata.items():
            RT[param] = {}
            for sc, array in obj1.items():
                RT[param][sc] = {}
                for o in array:
                    for tech, val in o.items():
                        RT[param][sc][tech] = val
        return RT

    def RE(self, REdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RE* parameter JSON into a flat lookup."""
        RE = {}
        for param, obj1 in REdata.items():
            RE[param] = {}
            for sc, array in obj1.items():
                RE[param][sc] = {}
                for o in array:
                    for emi, val in o.items():
                        RE[param][sc][emi] = val
        return RE

    def RS(self, RSdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RS* parameter JSON into a flat lookup."""
        RS = {}
        for param, obj in RSdata.items():
            RS[param] = {}
            for sc, array in obj.items():
                RS[param][sc] = {}
                for o in array:
                    for stg, val in o.items():
                        RS[param][sc][stg] = val
        return RS
     
    def RTSM(self, RTSMdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RTSM* parameter JSON into a nested lookup."""
        RTSM = {}
        for param, obj1 in RTSMdata.items():
            RTSM[param] = {}
            for sc, array in obj1.items():
                RTSM[param][sc] = {}
                for obj in array:
                    for value, val in obj.items():
                        if (value != 'TechId' and value != 'StgId' and value != 'MoId'):
                            # if value not in RTSM[param][sc]:
                            #     RTSM[param][sc][year] = {}
                            # if obj['StgId'] not in RTSM[param][sc][year]:
                            #     RTSM[param][sc][year][obj['StgId']] = {}
                            # if obj['TechId'] not in RTSM[param][sc][year][obj['StgId']]:
                            #     RTSM[param][sc][year][obj['StgId']][obj['TechId']] = {}
                            # RTSM[param][sc][year][obj['StgId']][obj['TechId']][obj['MoId']] = val

                            if obj['StgId'] not in RTSM[param][sc]:
                                RTSM[param][sc][obj['StgId']] = {}
                            if obj['TechId'] not in RTSM[param][sc][obj['StgId']]:
                                RTSM[param][sc][obj['StgId']][obj['TechId']] = {}
                            RTSM[param][sc][obj['StgId']][obj['TechId']][obj['MoId']] = val
        return RTSM
    
    def RYCn(self, RYCndata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYCn* parameter JSON into a nested lookup."""
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

    def RYT(self, RYTdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYT* parameter JSON into a nested lookup."""
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

    def RYS(self, RYSdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYS* parameter JSON into a nested lookup."""
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
    
    def RYTCn(self, RYTCndata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTCn* parameter JSON into a nested lookup."""
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

    def RYTM(self, RYTMdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTM* parameter JSON into a nested lookup."""
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

    def RYC(self, RYCdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYC* parameter JSON into a nested lookup."""
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

    def RYE(self, RYEdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYE* parameter JSON into a nested lookup."""
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

    def RYTs(self, RYTsdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTs* parameter JSON into a nested lookup."""
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

    def RYDtb(self, RYDtbdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYDtb* parameter JSON into a nested lookup."""
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
    
    def RYSeDt(self, RYSeDtdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYSeDt* parameter JSON into a nested lookup."""
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
    
    def RYTC(self, RYTCdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTC* parameter JSON into a nested lookup."""
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

    def RYTCM(self, RYTCMdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTCM* parameter JSON into a nested lookup."""
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

    def RYTSM(self, RYTSMdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTSM* parameter JSON into a nested lookup."""
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
    
    def RYTE(self, RYTEdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTE* parameter JSON into a nested lookup."""
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

    def RYTEM(self, RYTEMdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTEM* parameter JSON into a nested lookup."""
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

    def RYTTs(self, RYTTsdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYTTs* parameter JSON into a nested lookup."""
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

    def RYCTs(self, RYCTsdata: Dict[str, Any]) -> Dict[str, Any]:
        """Reshape *RYCTs* parameter JSON into a nested lookup."""
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

    def viewDataByTech(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate parameter view data grouped by technology."""
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

    def viewDataByComm(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate parameter view data grouped by commodity."""
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

    def viewDataByEmi(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate parameter view data grouped by emission."""
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

    def viewRTByTech(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate single-tech parameter view data grouped by technology."""
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

    def viewREByEmi(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aggregate single-emission parameter view data grouped by emission."""
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

    def updateViewData(
        self,
        casename: str,
        year: str,
        ScId: str,
        GroupId: str,
        ParamId: str,
        TechId: Optional[str],
        CommId: Optional[str],
        EmisId: Optional[str],
        Timeslice: Optional[str],
        value: Any,
    ) -> None:
        """Update a single cell value in a parameter JSON file.

        Args:
            casename: Case name.
            year: Year key to update.
            ScId: Scenario ID.
            GroupId: Parameter group ID (e.g. ``'RYT'``).
            ParamId: Parameter ID within the group.
            TechId: Technology ID filter (or *None*).
            CommId: Commodity ID filter (or *None*).
            EmisId: Emission ID filter (or *None*).
            Timeslice: Timeslice ID filter (or *None*).
            value: New value to write.

        Raises:
            IOError: If the file cannot be read or written.
        """
        try:
            jsonPath = Path(Config.DATA_STORAGE,casename, GroupId+'.json')
            jsonData = File.readFile(jsonPath)

            for obj in jsonData[ParamId][ScId]:
                if ((obj['TechId'] == TechId if TechId is not None else True) and 
                    (obj['CommId'] == CommId if CommId is not None else True) and 
                    (obj['EmisId'] == EmisId if EmisId is not None else True) and
                    (obj['TsId'] == Timeslice if Timeslice is not None else True)):
                    obj[year] = value
            File.writeFile( jsonData, jsonPath)
        except(IOError):
            raise IOError

    def updateTEViewData(
        self,
        casename: str,
        ScId: str,
        GroupId: str,
        ParamId: str,
        TechId: Optional[str],
        EmisId: Optional[str],
        value: Any,
    ) -> None:
        """Update a technology/emission scalar value in a parameter JSON file.

        Args:
            casename: Case name.
            ScId: Scenario ID.
            GroupId: Parameter group ID.
            ParamId: Parameter ID.
            TechId: Technology ID filter (or *None*).
            EmisId: Emission ID filter (or *None*).
            value: New value to write.

        Raises:
            IOError: If the file cannot be read or written.
        """
        try:
            jsonPath = Path(Config.DATA_STORAGE,casename, GroupId+'.json')
            jsonData = File.readFile(jsonPath)

            for obj in jsonData[ParamId][ScId]:
                for k,v in obj.items():
                    if ((k == TechId if TechId is not None else True) and 
                        (k == EmisId if EmisId is not None else True)):
                        obj[k] = value
            File.writeFile( jsonData, jsonPath)
        except(IOError):
            raise IOError
