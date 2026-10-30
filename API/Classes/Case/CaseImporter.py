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
import logging
import os
import shutil
import stat
from pathlib import Path
from zipfile import ZipFile

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.HelpersClass import Helpers
from Classes.Clews.Provenance import Provenance

# The case-schema version this MUIOGO writes and fully understands. Matches the
# "MUIO ver.5.7.0" the UI reports (WebAPP/App/View/Versions.html); bump together
# with a new rung on the ladder in CaseImporter.import_zip.
CURRENT_CASE_VERSION = "5.7"

# Every osy-version import_zip accepts. Anything else is refused with the same
# "not valid OSEMOSYS" message the upload path has always produced.
ACCEPTED_CASE_VERSIONS = ("1.0", "2.0", "3.0", "4.0", "4.5", "4.9", "5.0", "5.6", "5.7")

# Legacy case-backup arcname prefix. Backups created before PR #331 stored entries as
# 'WebAPP/DataStorage/<case>/<rel>'; backups since #331 store '<case>/<rel>'. We accept
# both formats on restore so users can still upload older archives.
_LEGACY_CASE_PREFIX = "WebAPP/DataStorage/"


def _case_zip_parts(zi):
    """Read portable relative ZIP names without silently removing unsafe components."""
    name = zi.orig_filename  # ZipInfo.filename silently truncates names at a NUL.
    parts = tuple(name.rstrip('/').split('/'))
    if ('\\' in name or '\x00' in name
            or any(part in ('', '.', '..') or ':' in part for part in parts)):
        raise PermissionError("Invalid case archive path")
    # Some legacy ZIP tools include the two harmless parent directory records.
    if zi.is_dir() and parts in (('WebAPP',), ('WebAPP', 'DataStorage')):
        return None
    if name.startswith(_LEGACY_CASE_PREFIX):
        parts = parts[2:]
    return parts


def _plan_case_zip(zf, dest_dir):
    """Validate every member against one case root before creating any files.

    An operator-placed case symlink may resolve outside DataStorage. Its resolved
    directory is the boundary; a member may never select another case or shared
    configuration. Archive members themselves cannot create symlinks.
    """
    members = [(zi, _case_zip_parts(zi)) for zi in zf.infolist()]
    members = [(zi, parts) for zi, parts in members if parts is not None]
    metadata = [(zi, parts) for zi, parts in members
                if not zi.is_dir() and parts[-1] == 'genData.json']
    if not metadata:
        return None, None, None, []
    if len(metadata) != 1 or len(metadata[0][1]) != 2:
        raise PermissionError("Case archive must contain one case-root genData.json")
    target_info, metadata_parts = metadata[0]
    casename = metadata_parts[0]
    case_root = Path(Config.validate_path(dest_dir, casename))
    planned_files = []
    seen = set()
    for zi, parts in members:
        if parts[0] != casename or stat.S_ISLNK(zi.external_attr >> 16):
            raise PermissionError("Archive entry is outside its case or is a symlink")
        if len(parts) == 1:
            if not zi.is_dir():
                raise PermissionError("Invalid case archive root")
            continue
        relative = str(Path(*parts[1:]))
        target = Path(Config.validate_path(case_root, relative))
        # Config also supports first-component operator symlinks. Inside a case,
        # those must not widen the already approved case-directory boundary.
        if not target.is_relative_to(case_root):
            raise PermissionError("Archive entry escapes its case directory")
        if zi.is_dir():
            continue
        key = tuple(part.casefold() for part in parts)
        if key in seen:
            raise PermissionError("Duplicate case archive member")
        seen.add(key)
        planned_files.append((zi, target))
    return target_info, casename, case_root, planned_files


def _extract_case_zip(zf, case_root, planned_files):
    """Write only the fully checked plan, reserving a new case directory first."""
    case_root.mkdir()  # Refuse a case created concurrently after the duplicate check.
    for zi, target in planned_files:
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


def updateCommodityBalanceLevel(casename):
    """MUIO 5.7: every commodity carries a BalanceLevel (Ts, Se or An).

    Cases from earlier versions have none; they are balanced per timeslice, as
    before. Reads genData from disk (not the caller's copy) so it never undoes
    an earlier migration step's write.
    """
    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
    genData = File.readParamFile(genDataPath)

    genData["osy-version"] = CURRENT_CASE_VERSION
    for c in genData.get("osy-comm", []):
        if "BalanceLevel" not in c:
            c["BalanceLevel"] = "Ts"

    File.writeFile( genData, genDataPath)

class CaseImporter:
    @staticmethod
    def import_zip(filepath, cleanup=True, source=None, sha256_declared=None):
        """Import one case archive into DataStorage. Returns the response messages.

        ``filepath`` is an absolute path to a readable case ZIP; the caller owns any
        upload/path validation. Returns the same list of message dicts the upload
        route has always produced ({message, status_code[, casename]}), so the route
        can jsonify it unchanged and an installer can read casename/status from it.
        ``cleanup`` removes the archive afterwards (the upload flow's behavior);
        an installer that manages its own temp dir passes False.

        Every imported case gets a provenance sidecar (clews-provenance.json):
        ``source`` describes where the archive came from (default: a plain upload)
        and ``sha256_declared`` is the checksum the source published for it, so the
        sidecar records whether the archive matched. Sidecar writing is best-effort;
        the import stands even if it cannot be written.

        Unsafe or multi-case archives raise PermissionError before extraction.
        A corrupt/unreadable ZIP raises (zipfile.BadZipFile/OSError) -- the upload
        route turns that into its usual 500, an installer into a failed job.
        """
        msg = []
        case = os.path.splitext(os.path.basename(filepath))[0]

        with ZipFile(filepath) as zf:
            target_info, casename, case_root, planned_files = _plan_case_zip(zf, Config.DATA_STORAGE)

            if not target_info:
                # No genData.json at all
                msg.append({
                    "message": f"ZIP archive {case} is not valid archive!",
                    "status_code": "error"
                })
                return msg

            if not os.path.exists(Path(Config.DATA_STORAGE,casename)):
                data = json.loads(zf.read(target_info).decode('ISO-8859-1'))
                name = data.get('osy-version', None)
                if name in ACCEPTED_CASE_VERSIONS:
                    _extract_case_zip(zf, case_root, planned_files)

                if name == '1.0' or name == '2.0':

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
                    updateCommodityBalanceLevel(casename)

                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name == '3.0':
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
                    updateCommodityBalanceLevel(casename)

                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name in ['4.0', '4.5', '4.9']:
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    updateTimeslices(casename)
                    updateStorageSet(casename)
                    updateGenData(casename, genData)
                    updateViewDefintions(casename, genData)
                    updateCommodityBalanceLevel(casename)
                    msg.append({
                        "message_warning": "You have restored a model created in a earlier version...",
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "warning",
                        "casename": casename
                    })
                elif name == '5.0':
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    updateGenData(casename, genData)
                    updateViewDefintions(casename, genData)
                    updateCommodityBalanceLevel(casename)

                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name == '5.6':
                    genDataPath = Path(Config.DATA_STORAGE, casename, 'genData.json')
                    genData = File.readParamFile(genDataPath)
                    updateViewDefintions(casename, genData)
                    updateCommodityBalanceLevel(casename)
                    msg.append({
                        "message": "Model " + casename +" have been uploaded!",
                        "status_code": "success",
                        "casename": casename
                    })
                elif name == '5.7':
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

        # Provenance sidecar: only when a case actually landed (those messages carry
        # a casename). Written while the archive still exists so it can be hashed.
        imported_case = msg[0].get("casename") if msg else None
        if imported_case:
            try:
                if source is None and Provenance.read(imported_case) is not None:
                    # A restored backup travels with the case's original sidecar
                    # (backupCase zips the whole case dir). A plain upload must not
                    # overwrite that record with "upload" -- it still says where the
                    # case originally came from. Just note the restore event.
                    # An installer's explicit source stays authoritative.
                    Provenance.mark_restored(imported_case,
                                             os.path.basename(filepath))
                else:
                    record = Provenance.build(
                        source=source if source is not None else {"type": "upload"},
                        archive_path=filepath,
                        archive_name=os.path.basename(filepath),
                        sha256_declared=sha256_declared,
                        case_version=_installed_case_version(imported_case),
                    )
                    Provenance.write(imported_case, record)
            except OSError as exc:
                logging.getLogger(__name__).warning(
                    "Case %s imported, but its provenance sidecar could not be "
                    "written: %s", imported_case, exc)

        if cleanup:
            os.remove(filepath)

        return msg


def _installed_case_version(casename):
    """The osy-version of the case as it now sits on disk, or None."""
    try:
        genData = File.readFile(Path(Config.DATA_STORAGE, casename, 'genData.json'))
        return genData.get('osy-version')
    except (OSError, ValueError, IndexError, AttributeError):
        return None
