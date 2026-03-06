from pathlib import Path
import os
from dotenv import load_dotenv
import platform

# Central path validation utility (prevents path traversal)
def validate_path(base_dir, user_input):
    base_raw = os.fspath(base_dir)
    user_raw = "" if user_input is None else os.fspath(user_input)

    if isinstance(base_raw, (bytes, bytearray)):
        base_raw = base_raw.decode("utf-8", "surrogateescape")
    if isinstance(user_raw, (bytes, bytearray)):
        user_raw = user_raw.decode("utf-8", "surrogateescape")

    if "\x00" in base_raw or "\x00" in user_raw:
        raise PermissionError("Path Traversal Attempt Detected")

    base_abs = os.path.realpath(os.path.abspath(os.path.normpath(base_raw)))
    target_abs = os.path.realpath(
        os.path.abspath(os.path.normpath(os.path.join(base_abs, user_raw)))
    )

    try:
        common = os.path.commonpath([base_abs, target_abs])
    except ValueError:
        raise PermissionError("Path Traversal Attempt Detected")

    if common != base_abs or target_abs == base_abs:
        raise PermissionError("Path Traversal Attempt Detected")

    return target_abs

#load environment variables
load_dotenv()

SYSTEM = platform.system()

# S3_BUCKET = os.environ.get("S3_BUCKET")
# S3_KEY = os.environ.get("S3_KEY")
# S3_SECRET = os.environ.get("S3_SECRET")

#S3 bucket is not used in Osemosys
S3_BUCKET = ""
S3_KEY = ""
S3_SECRET = ""

ALLOWED_EXTENSIONS = set(['zip', 'application/zip'])
ALLOWED_EXTENSIONS_XLS = set(['xls', 'xlsx'])
# -------------------------
# FIX: Make paths independent of working directory
# -------------------------

# This file is in: API/Classes/Base/Config.py
# So project root is 3 levels up
BASE_DIR = Path(__file__).resolve().parents[3]

WEBAPP_PATH = BASE_DIR / "WebAPP"

UPLOAD_FOLDER = WEBAPP_PATH
DATA_STORAGE = WEBAPP_PATH / "DataStorage"
CLASS_FOLDER = WEBAPP_PATH / "Classes"
SOLVERs_FOLDER = WEBAPP_PATH / "SOLVERs"
EXTRACT_FOLDER = BASE_DIR

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

HEROKU_DEPLOY = 0
AWS_SYNC = 0

PINNED_COLUMNS = ('Sc', 'Tech', 'Comm', 'Emis','Stg', 'Ts', 'MoO', 'UnitId', 'Se','Dt', 'Dtb', 'paramName','TechName', 'CommName', 'EmisName', 'ConName', 'MoId')

TECH_GROUPS = ('RYT', 'RYTM', 'RYTC', 'RYTCn', 'RYTCM', 'RYTE', 'RYTEM', 'RYTTs')
COMM_GROUPS = ('RYC', 'RYTC', 'RYTCM','RYCTs')
EMIS_GROUPS = ('RYE', 'RYTE', 'RYTEM')

SINGLE_TECH_GROUPS = ['RT']
SINGLE_EMIS_GROUPS = ['RE']

#full var list 38
VARIABLES_C = {
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

DUALS = {
    'EBb4_EnergyBalanceEachYear4_ICR': ['r','f','y'],
    'E8_AnnualEmissionsLimit': ['r','e','y'],
    'UDC1_UserDefinedConstraintInequality': ['r','cn','y'],
    'UDC2_UserDefinedConstraintEquality': ['r','cn','y']
}

#needed for validation of inputs
PARAMETERS_C = {
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

PARAMETERS_C_full = {
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
