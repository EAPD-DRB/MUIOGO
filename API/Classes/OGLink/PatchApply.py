"""Materialize an OG-link patch into a runnable caserun of a case COPY.

The OG side of the OG-CLEWS coupling emits a ``clews_patch.json``:

    {"source": "<og run manifest path>", "case": "<case name>",
     "changes": [{"group": "Demand", "code": "PHL_HOU_ELEF", "year": 2030,
                  "value": 123.4, "scenario": "SC_0"}, ...]}

``group`` names a parameter (a friendly alias like "Demand", a Parameters.json
display name like "Specified Annual Demand", or the raw id "SAD"); ``code`` is
the human commodity/technology/emission code; ``value`` is the absolute value to
set for that year. This module turns such a patch into a solved caserun:

    copy the case -> translate codes to the copy's own per-case ids via its
    genData.json -> set the values through the same read-merge the /updateData
    route uses -> create a caserun cloned from a named base caserun -> generate
    the datafile -> solve with MUIOGO's own pipeline -> return the csv dir.

Rules (docs: .claude/OGLINK-HANDOFF.md):
  * NEVER mutate a live case; every patch lands in a fresh copy.
  * Codes translate through the copy's own genData.json and fail loudly,
    listing what exists, on a miss.
  * All changes are validated before any file is written (all-or-nothing).
  * A change the read-merge cannot express (an unsupported parameter shape, a
    row the case does not carry) is a reported blocker, never a bypass write.
  * The generated datafile is the structure guard: it is generated before and
    after the patch and a changed line count is a reported finding (the patch
    silently added/dropped rows), not something to patch around.
"""
import json
import random
import shutil
from datetime import datetime, timezone, UTC
from pathlib import Path

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.Case.DataFileClass import DataFile


class OGLinkPatchError(Exception):
    """A structured failure: message for humans, details for the caller."""

    def __init__(self, message, http=400, details=None):
        super().__init__(message)
        self.message = message
        self.http = http
        self.details = details or {}


# Parameter groups the read-merge can express for a patch: rows keyed by ONE
# entity id plus year columns. Anything else (RYTCM's tech+comm+mode rows,
# timeslice-keyed groups, ...) is a reported blocker.
SUPPORTED_GROUPS = {
    "RYC": ("CommId", "comm"),
    "RYE": ("EmisId", "emis"),
    "RYT": ("TechId", "tech"),
}

# Friendly names the link may use, on top of raw ids ("SAD") and the
# Parameters.json display names ("Specified Annual Demand").
GROUP_ALIASES = {
    "demand": "SAD",
    "specifiedannualdemand": "SAD",
    "accumulatedannualdemand": "AAD",
    "emissionspenalty": "EP",
    "annualemissionlimit": "AEL",
}


class OGLinkPatch:

    # ── registries ────────────────────────────────────────────────────────────
    @staticmethod
    def param_index():
        """Parameters.json as lookup tables: param id -> dimension group, and
        normalized display name -> param id."""
        params = File.readParamFile(Path(Config.DATA_STORAGE, "Parameters.json"))
        by_id, by_name = {}, {}
        for group, entries in params.items():
            for entry in entries:
                by_id[entry["id"]] = group
                name = str(entry.get("value", "")).replace(" ", "").lower()
                if name:
                    by_name[name] = entry["id"]
        return by_id, by_name

    @staticmethod
    def case_registry(gen_data):
        """The case's code -> per-case-id tables from its own genData.json."""
        return {
            "comm": {c["Comm"]: c["CommId"] for c in gen_data.get("osy-comm", [])},
            "tech": {t["Tech"]: t["TechId"] for t in gen_data.get("osy-tech", [])},
            "emis": {e["Emis"]: e["EmisId"] for e in gen_data.get("osy-emis", [])},
            "scenarios": [s["ScenarioId"] for s in gen_data.get("osy-scenarios", [])],
            "years": [str(y) for y in gen_data.get("osy-years", [])],
        }

    @classmethod
    def resolve_param(cls, group, by_id, by_name):
        """A change's ``group`` -> (param_id, dimension_group). Blocker on an
        unknown name or an unsupported dimension shape."""
        key = str(group).replace(" ", "").lower()
        param = GROUP_ALIASES.get(key) or by_name.get(key) or (
            group if group in by_id else None)
        if param is None:
            raise OGLinkPatchError(
                f"Unknown parameter group {group!r}. Use a parameter id, its "
                "display name, or an alias.",
                details={"known_aliases": sorted(GROUP_ALIASES),
                         "known_ids": sorted(by_id)})
        dim = by_id[param]
        if dim not in SUPPORTED_GROUPS:
            raise OGLinkPatchError(
                f"Parameter {param!r} lives in group {dim!r}, whose rows the "
                "patch read-merge cannot express (only single-entity year "
                "tables are supported). This is a reported blocker by design.",
                http=422,
                details={"param": param, "dimension": dim,
                         "supported": sorted(SUPPORTED_GROUPS)})
        return param, dim

    # ── change resolution (no writes) ─────────────────────────────────────────
    @classmethod
    def resolve_changes(cls, case_dir, changes, active_scenarios):
        """Validate every change against the copied case; return a work plan
        grouped by file. Raises with ALL blockers listed, never a partial plan."""
        gen_data = File.readFile(Path(case_dir, "genData.json"))
        registry = cls.case_registry(gen_data)
        by_id, by_name = cls.param_index()
        plan, blockers = {}, []
        for i, change in enumerate(changes):
            try:
                for field in ("group", "code", "year", "value"):
                    if change.get(field) in (None, ""):
                        raise OGLinkPatchError(f"change is missing {field!r}")
                param, dim = cls.resolve_param(change["group"], by_id, by_name)
                id_key, kind = SUPPORTED_GROUPS[dim]
                table = registry[kind]
                code = change["code"]
                if code not in table:
                    known = sorted(table)
                    raise OGLinkPatchError(
                        f"{kind} code {code!r} is not in this case; present: "
                        f"{known[:20]}{' ...' if len(known) > 20 else ''}")
                year = str(change["year"])
                if year not in registry["years"]:
                    raise OGLinkPatchError(
                        f"year {year} is outside the case's years "
                        f"({registry['years'][0]}..{registry['years'][-1]}); "
                        "a value there would silently never reach the model")
                scenario = change.get("scenario") or "SC_0"
                if scenario not in registry["scenarios"]:
                    raise OGLinkPatchError(
                        f"scenario {scenario!r} is not in this case; present: "
                        f"{registry['scenarios']}")
                if scenario not in active_scenarios:
                    raise OGLinkPatchError(
                        f"scenario {scenario!r} is not active in the target "
                        f"caserun (active: {sorted(active_scenarios)}); the "
                        "change would silently not reach the solve")
                try:
                    value = float(change["value"])
                except (TypeError, ValueError):
                    raise OGLinkPatchError(
                        f"value {change['value']!r} is not numeric")
                plan.setdefault(dim, []).append({
                    "param": param, "scenario": scenario, "id_key": id_key,
                    "entity_id": table[code], "code": code, "year": year,
                    "value": value})
            except OGLinkPatchError as exc:
                blockers.append({"change_index": i, "change": change,
                                 "reason": exc.message, **exc.details})
        if blockers:
            raise OGLinkPatchError(
                f"{len(blockers)} of {len(changes)} changes cannot be applied; "
                "nothing was written.",
                http=422, details={"blocked": blockers})
        return plan

    # ── application (the /updateData read-merge idiom) ────────────────────────
    @staticmethod
    def apply_plan(case_dir, plan):
        """Write the resolved changes: one read-merge-write per group file.
        Returns per-change provenance (before/after)."""
        provenance = []
        for dim, items in plan.items():
            path = Path(case_dir, f"{dim}.json")
            data = File.readFile(path)
            for item in items:
                rows = data.get(item["param"], {}).get(item["scenario"])
                if rows is None:
                    raise OGLinkPatchError(
                        f"{dim}.json has no {item['param']}[{item['scenario']}] "
                        "table in this case",
                        http=422, details={"change": item})
                row = next((r for r in rows
                            if r.get(item["id_key"]) == item["entity_id"]), None)
                if row is None:
                    raise OGLinkPatchError(
                        f"{item['param']}[{item['scenario']}] has no row for "
                        f"{item['code']} ({item['entity_id']}); creating rows "
                        "is a blocker by design (it changes model structure)",
                        http=422, details={"change": item})
                before = row.get(item["year"])
                row[item["year"]] = item["value"]
                provenance.append({
                    "file": f"{dim}.json", "param": item["param"],
                    "scenario": item["scenario"], "code": item["code"],
                    "id": item["entity_id"], "year": item["year"],
                    "before": before, "after": item["value"]})
            File.writeFile(data, path)
        return provenance

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def validate_name(name, what):
        """A case-copy or caserun name must be a single path segment inside
        DataStorage: no separators, no traversal, no null bytes."""
        Config.validate_path(Config.DATA_STORAGE, name)
        if Path(name).name != name or name in (".", ".."):
            raise OGLinkPatchError(
                f"{what} {name!r} must be a plain name (no path separators)")

    @staticmethod
    def copy_case(src_case, dst_case, overwrite=False):
        Config.validate_path(Config.DATA_STORAGE, src_case)
        src = Path(Config.DATA_STORAGE, src_case)
        dst = Path(Config.DATA_STORAGE, dst_case)
        if not (src / "genData.json").is_file():
            raise OGLinkPatchError(
                f"{src_case!r} is not a case (no genData.json)", http=404)
        if dst.resolve() == src.resolve():
            raise OGLinkPatchError(
                f"copy name {dst_case!r} is the source case itself; a patch "
                "never lands in a live case", http=409)
        if dst.exists():
            # Overwrite may only ever delete a dir THIS module created: the
            # birth marker is written the moment a copy is made. Anything
            # else (a live case, a hand-made dir) is refused, overwrite or not.
            if not overwrite:
                raise OGLinkPatchError(
                    f"case copy {dst_case!r} already exists; pass "
                    "overwrite_copy to replace it", http=409)
            if not (dst / "oglink" / "created.json").is_file():
                raise OGLinkPatchError(
                    f"{dst_case!r} exists but is not an OG-link copy (no "
                    "oglink/created.json marker); refusing to overwrite it",
                    http=409)
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        gd_path = dst / "genData.json"
        gen_data = File.readFile(gd_path)
        gen_data["osy-casename"] = dst_case
        File.writeFile(gen_data, gd_path)
        (dst / "oglink").mkdir(exist_ok=True)
        File.writeFile(
            {"copied_from": src_case,
             "created_at": datetime.now(UTC).isoformat()},
            dst / "oglink" / "created.json")
        return dst

    @staticmethod
    def base_caserun_record(case, base_caserun):
        res_data = File.readFile(
            Path(Config.DATA_STORAGE, case, "view", "resData.json"))
        record = next((c for c in res_data.get("osy-cases", [])
                       if c["Case"] == base_caserun), None)
        if record is None:
            present = [c["Case"] for c in res_data.get("osy-cases", [])]
            raise OGLinkPatchError(
                f"caserun {base_caserun!r} does not exist in case {case!r}; "
                f"present: {present}", http=404)
        return record

    @staticmethod
    def datafile_lines(case, caserun):
        path = Path(Config.DATA_STORAGE, case, "res", caserun, "data.txt")
        with open(path, encoding="utf-8") as handle:
            return sum(1 for _ in handle)

    # ── the orchestrator ──────────────────────────────────────────────────────
    @classmethod
    def apply(cls, patch, base_caserun, caserun_name=None, copy_name=None,
              solver="CBC", overwrite_copy=False):
        """The W1 entry point. Returns the result dict; raises OGLinkPatchError
        with structured details on any blocker, finding, or solve failure."""
        case = patch.get("case")
        changes = patch.get("changes")
        if not case or not isinstance(changes, list) or not changes:
            raise OGLinkPatchError(
                "patch must carry 'case' and a non-empty 'changes' list")

        Config.validate_path(Config.DATA_STORAGE, case)
        if not Path(Config.DATA_STORAGE, case, "genData.json").is_file():
            raise OGLinkPatchError(
                f"{case!r} is not a case (no genData.json)", http=404)
        base_record = cls.base_caserun_record(case, base_caserun)
        active = {s["ScenarioId"] for s in base_record["Scenarios"] if s["Active"]}

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        copy_name = copy_name or f"{case}_oglink_{stamp}"
        caserun_name = caserun_name or f"OGLink_{base_caserun}"
        cls.validate_name(copy_name, "copy name")
        cls.validate_name(caserun_name, "caserun name")

        copy_dir = cls.copy_case(case, copy_name, overwrite=overwrite_copy)
        try:
            plan = cls.resolve_changes(copy_dir, changes, active)
        except OGLinkPatchError:
            shutil.rmtree(copy_dir)  # nothing applied, nothing to inspect
            raise

        # Caserun first, then the UNPATCHED datafile: its line count is the
        # structure baseline the patched regeneration must reproduce.
        record = {
            "Case": caserun_name,
            "CaseId": "CS_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5)),
            "Desc": (f"OG link patch of {base_caserun!r}: {len(changes)} "
                     f"changes from {patch.get('source', 'unknown source')}"),
            "Runtime": datetime.now(UTC).strftime(
                "%a %b %d %Y %H:%M:%S GMT+0000 (UTC)"),
            "Scenarios": [dict(s) for s in base_record["Scenarios"]],
        }
        created = DataFile(copy_name).createCaseRun(caserun_name, record)
        if created.get("status_code") != "success":
            shutil.rmtree(copy_dir)
            raise OGLinkPatchError(
                f"could not create caserun {caserun_name!r} in the copy: "
                f"{created.get('message')}", details={"response": created})

        DataFile(copy_name).generateDatafile(caserun_name)
        lines_before = cls.datafile_lines(copy_name, caserun_name)

        try:
            provenance = cls.apply_plan(copy_dir, plan)
        except OGLinkPatchError:
            shutil.rmtree(copy_dir)
            raise

        # Fresh DataFile: the generator must see the patched group files.
        DataFile(copy_name).generateDatafile(caserun_name)
        lines_after = cls.datafile_lines(copy_name, caserun_name)
        if lines_after != lines_before:
            # The finding the handoff brief warns about: the patch changed the
            # datafile's structure. Keep the copy as evidence; do not solve.
            raise OGLinkPatchError(
                f"patched datafile has {lines_after} lines vs {lines_before} "
                f"unpatched -- the patch changed model structure. The copy "
                f"{copy_name!r} is kept for inspection.",
                http=422,
                details={"finding": "datafile_structure_changed",
                         "case_copy": copy_name, "caserun": caserun_name,
                         "lines_before": lines_before,
                         "lines_after": lines_after})

        # Audit trail inside the copy: the patch and what it touched.
        oglink_dir = copy_dir / "oglink"
        oglink_dir.mkdir(exist_ok=True)
        File.writeFile(
            {"patch": patch, "base_caserun": base_caserun,
             "caserun": caserun_name, "applied": provenance,
             "applied_at": datetime.now(UTC).isoformat()},
            oglink_dir / "patch_applied.json")

        solve = DataFile(copy_name).run(solver, caserun_name)
        if solve.get("status_code") != "success":
            # Solver logs live in the copy's res dir; keep it for diagnosis.
            raise OGLinkPatchError(
                f"solve did not succeed (status {solve.get('status_code')!r}); "
                f"the copy {copy_name!r} is kept, logs in res/{caserun_name}/.",
                http=500,
                details={"case_copy": copy_name, "caserun": caserun_name,
                         "timer": solve.get("timer"),
                         "cbc_tail": (solve.get("cbc_message") or "")[-2000:],
                         "glpk_tail": (solve.get("glpk_message") or "")[-2000:]})

        csv_dir = Path(Config.DATA_STORAGE, copy_name, "res", caserun_name, "csv")
        if not csv_dir.is_dir():
            raise OGLinkPatchError(
                f"solve reported success but {csv_dir} does not exist -- "
                "result layout changed?", http=500,
                details={"case_copy": copy_name, "caserun": caserun_name})

        no_ops = [p for p in provenance if p["before"] == p["after"]]
        return {
            "case": case,
            "case_copy": copy_name,
            "caserun": caserun_name,
            "caserun_id": record["CaseId"],
            "csv_dir": str(csv_dir),
            "solver": solver,
            "timer": solve.get("timer"),
            "changes_applied": provenance,
            "datafile_lines": lines_after,
            "warnings": ([f"{len(no_ops)} changes set a value equal to the "
                          "existing one (no-op)"] if no_ops else []),
        }
