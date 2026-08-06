"""Import a case archive into DataStorage: one implementation for every entry path.

This is the zip-processing core that used to live inline in UploadRoute's
handle_full_zip. It was extracted so the browser upload (/uploadCase) and any
programmatic installer (e.g. the CLEWs country install layer) run the exact same
pipeline: find genData.json, read the case's osy-version, extract, and apply the
version migration ladder. The route keeps the HTTP concerns (chunk assembly,
extension checks, path validation); this class knows nothing about flask.

Version ladder: a case declares its schema in genData.json's osy-version. Each
accepted version maps to the migrations that bring it to the current schema.
An unrecognised version is refused, never guessed at.
"""
import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.HelpersClass import Helpers

# The case-schema version this MUIOGO writes and fully understands. Matches the
# "MUIO ver.5.6.0" the UI reports (WebAPP/App/View/Versions.html); bump together
# with a new rung on the ladder in CaseImporter.import_zip.
CURRENT_CASE_VERSION = "5.6"

# Every osy-version import_zip accepts. Anything else is refused with the same
# "not valid OSEMOSYS" message the upload path has always produced.
ACCEPTED_CASE_VERSIONS = ("1.0", "2.0", "3.0", "4.0", "4.5", "4.9", "5.0", "5.6")

# Legacy case-backup arcname prefix. Backups created before PR #331 stored entries as
# 'WebAPP/DataStorage/<case>/<rel>'; backups since #331 store '<case>/<rel>'. We accept
# both formats on restore so users can still upload older archives.
_LEGACY_CASE_PREFIX = "WebAPP/DataStorage/"


def _extract_case_zip(zf, dest_dir):
    """Extract a case backup ZIP under dest_dir, handling both legacy and current arcname
    layouts. Each entry is rewritten to be case-rooted ('<case>/<rel>') and validated
    against path traversal before writing.
    """
    for zi in zf.infolist():
        if zi.is_dir():
            continue
        name = zi.filename.lstrip('/')
        if name.startswith(_LEGACY_CASE_PREFIX):
            name = name[len(_LEGACY_CASE_PREFIX):]
        if not name:
            continue
        target = Config.validate_path(dest_dir, name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with zf.open(zi) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)


def updateTimeslices(casename):
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
    genData = File.readParamFile(genDataPath)
    ns = int(genData["osy-ns"])
    nd = int(genData["osy-dt"])
    genData["osy-se"] = []
    genData["osy-se"].append({"SeId": "SE_0", "Se": "1", "Desc": "Default season"})

    genData["osy-dt"] = []
    genData["osy-dt"].append({"DtId": "DT_0", "Dt": "1", "Desc": "Default day type"})

    genData["osy-dtb"] = []
    genData["osy-dtb"].append({"DtbId": "DTB_0", "Dtb": "1", "Desc": "Default dialy time bracket"})

    genData["osy-ts"] = []
    for season in range(ns):
        for day in range(nd):
            chunk = {}
            s = str(season + 1)
            d = str(day + 1)
            chunk['TsId'] = "S"+s+d
            chunk['Ts'] = "S"+s+d
            chunk["SE"] = "SE_0"
            chunk["DT"] = "DT_0"
            chunk["DTB"] = "DTB_0"
            chunk['Desc'] = "Default year split"
            genData["osy-ts"].append(chunk)
    File.writeFile( genData, genDataPath)
    #rename json files with timeslices
    RYTsPath = Path(Config.DATA_STORAGE, casename, 'RYTs.json')
    RYTsPath.write_text(RYTsPath.read_text().replace('YearSplit', 'TsId'))
    RYTTsPath = Path(Config.DATA_STORAGE, casename, 'RYTTs.json')
    RYTTsPath.write_text(RYTTsPath.read_text().replace('Timeslice', 'TsId'))
    RYCTsPath = Path(Config.DATA_STORAGE, casename, 'RYCTs.json')
    RYCTsPath.write_text(RYCTsPath.read_text().replace('Timeslice', 'TsId'))


def updateStorageSet(casename):
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
    genData = File.readParamFile(genDataPath)

    genData["osy-stg"] = []

    File.writeFile( genData, genDataPath)


def updateGenData(casename, genData):
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')

    genData["osy-indicators"] = []

    File.writeFile( genData, genDataPath)


def updateViewDefintions(casename, genData):

    viewDataPath = Path(Config.DATA_STORAGE,casename,'view','viewDefinitions.json')

    if not viewDataPath.exists():
        viewDefExisting = {"osy-views": {} }
        File.writeFile(viewDefExisting, viewDataPath)
    else:
        viewDefExisting = File.readParamFile(viewDataPath)

    customIndicators = genData['osy-indicators']
    techsMap = {tech['TechId']: tech['Tech'] for tech in genData["osy-tech"] }
    storagePath = Path(Config.DATA_STORAGE)
    VARIABLES = File.readParamFile(storagePath / 'Variables.json')
    INDICATORS = File.readParamFile(storagePath / 'Indicators.json')

    IND_GROUPED = Helpers.merge_all_indicators_grouped(INDICATORS, customIndicators, techsMap)

    vars = Helpers.merge_groups(VARIABLES, IND_GROUPED)

    viewDef = {}
    for group, lists in vars.items():
        for list in lists:
            if list['id'] not in viewDefExisting["osy-views"]:
                # Ako postoji indicator_type → izbriši ključ (ako je ranije kreiran)
                if "indicator_type" in list and list["indicator_type"]:
                    if list['id'] in viewDef:
                        del viewDef[list['id']]
                    else:
                        viewDef[list['id']] = []
                else:
                    viewDef[list['id']] = []
            else:
                if "indicator_type" in list and list["indicator_type"]:
                    viewDef[list['id']] = viewDefExisting["osy-views"][list['id']]
                else:
                    viewDef[list['id']] = viewDefExisting["osy-views"][list['id']]

    viewData = {
        "osy-views": viewDef
    }
    File.writeFile( viewData, viewDataPath)


class CaseImporter:
    @staticmethod
    def import_zip(filepath, cleanup=True):
        """Import one case archive into DataStorage. Returns the response messages.

        ``filepath`` is an absolute path to a readable case ZIP; the caller owns any
        upload/path validation. Returns the same list of message dicts the upload
        route has always produced ({message, status_code[, casename]}), so the route
        can jsonify it unchanged and an installer can read casename/status from it.
        ``cleanup`` removes the archive afterwards (the upload flow's behavior);
        an installer that manages its own temp dir passes False.

        A corrupt/unreadable ZIP raises (zipfile.BadZipFile/OSError) -- the upload
        route turns that into its usual 500, an installer into a failed job.
        """
        msg = []
        case = os.path.splitext(os.path.basename(filepath))[0]

        with ZipFile(filepath) as zf:
            # --- Find first genData.json entry (single pass) ---
            target_info = next(
                (zi for zi in zf.infolist() if Path(zi.filename).name == "genData.json"),
                None
            )

            if not target_info:
                # No genData.json at all
                msg.append({
                    "message": f"ZIP archive {case} is not valid archive!",
                    "status_code": "error"
                })
                return msg

            zippedfilepath = Path(target_info.filename)
            casename = zippedfilepath.parent.name
            if not os.path.exists(Path(Config.DATA_STORAGE,casename)):
                data = json.loads(zf.read(target_info).decode('ISO-8859-1'))
                name = data.get('osy-version', None)

                if name == '1.0' or name == '2.0':
                    _extract_case_zip(zf, Config.DATA_STORAGE)

                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)

                    resPath = Path(Config.DATA_STORAGE,casename,'res')
                    viewPath = Path(Config.DATA_STORAGE,casename,'view')
                    resDataPath = Path(Config.DATA_STORAGE,casename,'view','resData.json')

                    if os.path.exists(resPath):
                        shutil.rmtree(resPath)
                    if os.path.exists(viewPath):
                        shutil.rmtree(viewPath)
                    os.makedirs(resPath, exist_ok=True)
                    os.makedirs(viewPath, exist_ok=True)
                    resData = {"osy-cases":[]}
                    File.writeFile(resData, resDataPath)

                    updateTimeslices(casename)
                    updateStorageSet(casename)
                    updateGenData(casename, genData)
                    updateViewDefintions(casename, genData)

                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name == '3.0':
                    _extract_case_zip(zf, Config.DATA_STORAGE)
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    genData["osy-techGroups"] = []
                    for dic in genData["osy-tech"]:
                        dic["TG"] = []
                    File.writeFile(genData, genDataPath)
                    updateTimeslices(casename)
                    updateStorageSet(casename)
                    updateGenData(casename, genData)
                    updateViewDefintions(casename, genData)

                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name in ['4.0', '4.5', '4.9']:
                    _extract_case_zip(zf, Config.DATA_STORAGE)
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    updateTimeslices(casename)
                    updateStorageSet(casename)
                    updateGenData(casename, genData)
                    updateViewDefintions(casename, genData)
                    msg.append({
                        "message_warning": "You have restored a model created in a earlier version...",
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "warning",
                        "casename": casename
                    })
                elif name == '5.0':
                    _extract_case_zip(zf, Config.DATA_STORAGE)
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    updateGenData(casename, genData)
                    updateViewDefintions(casename, genData)

                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name == '5.6':
                    _extract_case_zip(zf, Config.DATA_STORAGE)
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    updateViewDefintions(casename, genData)
                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                else:
                    msg.append({
                        "message": "Model " + casename +" is not valid OSEMOSYS!",
                        "status_code": "error"
                    })

            else:
                msg.append({
                    "message": "Model " + casename + " already exists!",
                    "status_code": "warning"
                })

        if cleanup:
            os.remove(filepath)

        return msg
