"""Application configuration module.

Defines paths, constants, and environment-based settings used throughout
the MUIOGO application. Values are resolved at import time so that every
module shares a single source of truth.
"""

from pathlib import Path
from typing import Dict, Final, List, Set, Tuple
import os
#from dotenv import load_dotenv
import platform

#load environment variables
#load_dotenv()

SYSTEM: Final[str] = platform.system()

# S3_BUCKET = os.environ.get("S3_BUCKET")
# S3_KEY = os.environ.get("S3_KEY")
# S3_SECRET = os.environ.get("S3_SECRET")

#S3 bucket is not used in Osemosys
S3_BUCKET: Final[str] = ""
S3_KEY: Final[str] = ""
S3_SECRET: Final[str] = ""

ALLOWED_EXTENSIONS: Final[Set[str]] = set(['zip', 'application/zip'])
ALLOWED_EXTENSIONS_XLS: Final[Set[str]] = set(['xls', 'xlsx'])
# -------------------------
# FIX: Make paths independent of working directory
# -------------------------

# This file is in: API/Classes/Base/Config.py
# So project root is 3 levels up
BASE_DIR: Final[Path] = Path(__file__).resolve().parents[3]

WEBAPP_PATH: Final[Path] = BASE_DIR / "WebAPP"

UPLOAD_FOLDER: Final[Path] = WEBAPP_PATH
DATA_STORAGE: Final[Path] = WEBAPP_PATH / "DataStorage"
CLASS_FOLDER: Final[Path] = WEBAPP_PATH / "Classes"
SOLVERs_FOLDER: Final[Path] = WEBAPP_PATH / "SOLVERs"
EXTRACT_FOLDER: Final[Path] = BASE_DIR

# Ensure DataStorage exists
DATA_STORAGE.mkdir(parents=True, exist_ok=True)

# Validate writability instead of forcing permissions
if not os.access(DATA_STORAGE, os.W_OK):
    raise PermissionError(f"Data storage path is not writable: {DATA_STORAGE}")
#absolute paths
# OSEMOSYS_ROOT = os.path.abspath(os.getcwd())
# UPLOAD_FOLDER = Path(OSEMOSYS_ROOT, 'WebAPP')
# WebAPP_PATH = Path(OSEMOSYS_ROOT, 'WebAPP')
# DATA_STORAGE = Path(OSEMOSYS_ROOT, "WebAPP", 'DataStorage')
# CLASS_FOLDER = Path(OSEMOSYS_ROOT, "WebAPP", 'Classes')
# EXTRACT_FOLDER = Path(OSEMOSYS_ROOT, "")
# SOLVERs_FOLDER = Path(OSEMOSYS_ROOT, 'WebAPP', 'SOLVERs')

HEROKU_DEPLOY: Final[int] = 0
AWS_SYNC: Final[int] = 0

# API base URL: configurable via MUIOGO_API_URL env var.
# Defaults to window.location.origin on the frontend when not set.
API_BASE_URL: Final[str] = os.environ.get("MUIOGO_API_URL", "")

# CORS allowed origins: configurable via MUIOGO_CORS_ORIGINS env var.
# Accepts a comma-separated list. Defaults to localhost origins for local dev.
CORS_ORIGINS: Final[List[str]] = [
    origin.strip()
    for origin in os.environ.get(
        "MUIOGO_CORS_ORIGINS",
        "http://127.0.0.1:5002,http://localhost:5002,http://127.0.0.1,http://localhost"
    ).split(",")
    if origin.strip()
]

PINNED_COLUMNS: Final[Tuple[str, ...]] = ('Sc', 'Tech', 'Comm', 'Emis','Stg', 'Ts', 'MoO', 'UnitId', 'Se','Dt', 'Dtb', 'paramName','TechName', 'CommName', 'EmisName', 'ConName', 'MoId')

TECH_GROUPS: Final[Tuple[str, ...]] = ('RYT', 'RYTM', 'RYTC', 'RYTCn', 'RYTCM', 'RYTE', 'RYTEM', 'RYTTs')
COMM_GROUPS: Final[Tuple[str, ...]] = ('RYC', 'RYTC', 'RYTCM','RYCTs')
EMIS_GROUPS: Final[Tuple[str, ...]] = ('RYE', 'RYTE', 'RYTEM')

SINGLE_TECH_GROUPS: Final[List[str]] = ['RT']
SINGLE_EMIS_GROUPS: Final[List[str]] = ['RE']

#full var list 38
VARIABLES_C: Final[Dict[str, List[str]]] = {
        'NewCapacity':['r','t','y'],
        'AccumulatedNewCapacity':['r','t','y'],
        'TotalCapacityAnnual':['r','t','y'],
        'CapitalInvestment':['r','t','y'],
        'AnnualVariableOperatingCost':['r','t','y'],
        'AnnualFixedOperatingCost':['r','t','y'],
        'SalvageValue':['r','t','y'],
        'DiscountedSalvageValue':['r','t','y'],
        'TotalTechnologyAnnualActivity':['r','t','y'],
        'RateOfActivity':['r','l','t','m','y'],
        'RateOfTotalActivity':['r','t','l','y'],
        'Demand':['r','l','f','y'],
        'TotalAnnualTechnologyActivityByMode':['r','t','m','y'],
        'TotalTechnologyModelPeriodActivity':['r','t'],
        'ProductionByTechnology':['r','l','t','f','y'],
        'ProductionByTechnologyAnnual':['r','t','f','y'],
        'AnnualTechnologyEmissionByMode':['r','t','e','m','y'],
        'EmissionByActivityChange':['r','t','e','m','y'],
        'AnnualTechnologyEmission':['r','t','e','y'],
        'AnnualEmissions':['r','e','y'],
        'DiscountedTechnologyEmissionsPenalty':['r','t','y'],
        'TechnologyEmissionsPenalty':['r','t','y'],
        'RateOfProductionByTechnology':['r','l','t','f','y'],
        'RateOfUseByTechnology':['r','l','t','f','y'],
        'UseByTechnology':['r','l','t','f','y'],
        'UseByTechnologyAnnual':['r','t','f','y'],
        'RateOfProductionByTechnologyByMode':['r','l','t','m','f','y'],
        'RateOfUseByTechnologyByMode':['r','l','t','m','f','y'],
        'TechnologyActivityChangeByMode':['r','t','m','y'],
        'TechnologyActivityChangeByModeCostTotal':['r','t','m','y'],
        'InputToNewCapacity':['r','t','f','y'],
        'InputToTotalCapacity':['r','t','f','y'],
        'DiscountedCapitalInvestment':['r','t','y'],
        'DiscountedOperatingCost':['r','t','y'],
        'TotalDiscountedCostByTechnology':['r','t','y'],
        'NewStorageCapacity':['r','s','y'],
        'SalvageValueStorage':['r','s','y'],
        'NumberOfNewTechnologyUnits':['r','t','y'],
        'Trade':['r','rr','l','f','y'],
        'RateOfNetStorageActivity':['r','s','ls','ld','lh','y'],
        'NetChargeWithinDay': ['r','s','ls','ld','lh','y'],
        'NetChargeWithinYear':['r','s','ls','ld','lh','y'],
        'StorageLevelYearStart': ['r','s','y'],
        'StorageLevelYearFinish': ['r','s','y'],
        'StorageLevelSeasonStart':['r','s','ls','y'],
        'StorageLevelSeasonFinish':['r','s','ls','y'],
        'StorageLevelDayTypeStart': ['r','s','ls','ld','y'],
        'StorageLevelDayTypeFinish': ['r','s','ls','ld','y'],
        'AccumulatedNewStorageCapacity':['r','s','y'],
        'StorageUpperLimit':['r','s','y'],
        'CapitalInvestmentStorage':['r','s','y'],
        'DiscountedCapitalInvestmentStorage':['r','s','y'],
        'DiscountedSalvageValueStorage':['r','s','y'],
        'TotalDiscountedStorageCost':['r','s','y'],
        'EBb4_EnergyBalanceEachYear4_ICR': ['r','f','y'],
        'E8_AnnualEmissionsLimit': ['r','e','y'],
        'UDC1_UserDefinedConstraintInequality': ['r','cn','y'],
        'UDC2_UserDefinedConstraintEquality': ['r','cn','y']
    }

DUALS: Final[Dict[str, List[str]]] = {
    'EBb4_EnergyBalanceEachYear4_ICR': ['r','f','y'],
    'E8_AnnualEmissionsLimit': ['r','e','y'],
    'UDC1_UserDefinedConstraintInequality': ['r','cn','y'],
    'UDC2_UserDefinedConstraintEquality': ['r','cn','y']
}

#needed for validation of inputs
PARAMETERS_C: Final[Dict[str, List[str]]] = {
        'DiscountRate': ['r'],
        'OutputActivityRatio':['r','f','t','y','m'],
        'InputActivityRatio':['r','f','t','y','m'],
        'EmissionActivityRatio':['r','e','t','y','m'],
        'TotalAnnualMaxCapacityInvestment':['r','t','y'],
        'TotalAnnualMinCapacityInvestment':['r','t','y'],
        'TotalTechnologyAnnualActivityUpperLimit':['r','t','y'],
        'TotalTechnologyAnnualActivityLowerLimit':['r','t','y'],
        'TotalAnnualMaxCapacity':['r','t','y'],
        'ResidualCapacity': ['r','t','y'],
        'AvailabilityFactor': ['r','t','y'],
        'CapacityToActivityUnit': ['r','t'],
        'DiscountRateIdv': ['r','t'],
        'OperationalLife': ['r','t'],
        'TotalTechnologyModelPeriodActivityLowerLimit': ['r','t'],
        'TotalTechnologyModelPeriodActivityUpperLimit': ['r','t'],
        'CapacityFactor': ['r','t', 'y', 'l'],
        'YearSplit': ['r','y', 'l'],
        'SpecifiedDemandProfile': ['r','f','y','l']
    }

PARAMETERS_C_full: Final[Dict[str, List[str]]] = {
        'DiscountRate': ['r', 'DiscountRate'],
        'OutputActivityRatio':['r','f','t','y','m','OutputActivityRatio'],
        'InputActivityRatio':['r','f','t','y','m','InputActivityRatio'],
        'EmissionActivityRatio':['r','e','t','y','m','EmissionActivityRatio'],
        'TotalAnnualMaxCapacityInvestment':['r','t','y','TotalAnnualMaxCapacityInvestment'],
        'TotalAnnualMinCapacityInvestment':['r','t','y','TotalAnnualMinCapacityInvestment'],
        'TotalTechnologyAnnualActivityUpperLimit':['r','t','y','TotalTechnologyAnnualActivityUpperLimit'],
        'TotalTechnologyAnnualActivityLowerLimit':['r','t','y','TotalTechnologyAnnualActivityLowerLimit'],
        'TotalAnnualMaxCapacity':['r','t','y','TotalAnnualMaxCapacity'],
        'ResidualCapacity': ['r','t','y','ResidualCapacity'],
        'AvailabilityFactor': ['r','t','y','AvailabilityFactor'],
        'CapacityToActivityUnit': ['r','t','CapacityToActivityUnit'],
        'DiscountRateIdv': ['r','t','DiscountRateIdv'],
        'OperationalLife': ['r','t','OperationalLife'],
        'TotalTechnologyModelPeriodActivityLowerLimit': ['r','t','TotalTechnologyModelPeriodActivityLowerLimit'],
        'TotalTechnologyModelPeriodActivityUpperLimit': ['r','t','TotalTechnologyModelPeriodActivityUpperLimit'],
        'CapacityFactor': ['r','t', 'y', 'l','CapacityFactor'],
        'YearSplit': ['r','y', 'l','YearSplit'],
        'SpecifiedDemandProfile': ['r','f','y','l','SpecifiedDemandProfile'],
        'ResidualStorageCapacity': ['r','s','y','ResidualStorageCapacity'],
    }
