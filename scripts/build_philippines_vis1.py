#!/usr/bin/env python3
"""Build the source-traceable Philippines vIS1.1 3+1 nodal power pilot from v36.

The script copies v36 without regenerable result/view files, performs the
structural edit in genData.json, runs MUIOGO's UpdateCase normalization, and
then writes only source parameter JSON. Historical generation is never used as
an activity bound or target.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
INPUT = ROOT / "scripts" / "data" / "philippines_vis1" / "spatial_inputs.json"
LOOKUP = ROOT / "scripts" / "data" / "philippines_vis1" / "province_node_lookup.csv"
YEARS = [str(y) for y in range(2020, 2054)]
HISTORY = [str(y) for y in range(2020, 2025)]
NODES = ("LUZ", "VIS", "MIN")
SC_BASE = "SC_0"
SC_COAL_PHASEOUT = "SC_3hgjb"
OFFGRID_SALES_2020 = 1286.0
OFFGRID_CONSUMPTION_2020 = 1481.0
NONNEGATIVE_TOLERANCE = 1e-9
BUNDLE_HEADROOM_FACTOR = 4.0

GENERATION = {
    "PHL_POW_CHP_NG_OLD": "gas",
    "PHL_POW_CHP_OIL_OLD": "oil",
    "PHL_POW_PP_WON": "wind",
    "PHL_POW_PP_WOF": "wind",
    "PHL_POW_PP_SPV": "solar",
    "PHL_POW_PP_NUSMR": "load",
    "PHL_POW_PP_NU": "load",
    "PHL_POW_PP_NGCC_CCS": "gas",
    "PHL_POW_PP_NGCC": "gas",
    "PHL_POW_PP_HY_LA": "hydro",
    "PHL_POW_PP_H2": "load",
    "PHL_POW_PP_COAL_CCS": "coal",
    "PHL_POW_PP_COAL": "coal",
    "PHL_POW_PP_BIOM_CCS": "biomass",
    "PHL_POW_GEO_OLD": "geothermal",
    "PHL_POW_CHP_COAL_OLD": "coal",
    "PHL_POW_CHP_BIOM_OLD": "biomass",
    "PHL_POW_CHP_BIOM_FIT_OLD": "biomass",
}
LEGACY = {
    "PHL_POW_CHP_NG_OLD": "gas",
    "PHL_POW_CHP_OIL_OLD": "oil",
    "PHL_POW_PP_WON": "wind",
    "PHL_POW_PP_SPV": "solar",
    "PHL_POW_PP_HY_LA": "hydro",
    "PHL_POW_GEO_OLD": "geothermal",
    "PHL_POW_CHP_COAL_OLD": "coal",
    "PHL_POW_CHP_BIOM_OLD": "biomass",
    "PHL_POW_CHP_BIOM_FIT_OLD": "biomass",
}
SECTOR_TD = {
    "PHL_POW_TD_HOU": "residential",
    "PHL_POW_TD_SER": "commercial",
    "PHL_POW_TD_INDU": "industrial",
    "PHL_POW_TD_AGR": "others",
    "PHL_POW_TD_TRA": "others",
    "PHL_POW_TD_FSH": "others",
}
DIRECT_GRID = (
    "PHL_POW_DAC",
    "PHL_POW_ELEC",
    "PHL_POW_TECH_AMMO",
)
COOLING = ("PHL_DEM_PWR_GWT_WAT", "PHL_DEM_PWR_SUR_WAT")
FUEL_COMMODITIES = {
    "COM_lej08": ("PHL_PRO_NG", "NG"),
    "COM_fbce3": ("PHL_PRO_OIL", "OIL"),
    "COM_8jkgl": ("PHL_PRO_COAL", "COAL"),
    "COM_0": ("PHL_PRO_BIOM", "BIOM"),
    "COM_v22fit": ("PHL_PRO_BIOM_FIT_RESIDUE", "FITRES"),
}
TECH_FILES = (
    "RYT.json", "RYTTs.json", "RYTCM.json", "RYTM.json", "RYTEM.json",
    "RYTC.json", "RYTCn.json", "RYTs.json", "RTSM.json",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def one(rows: list[dict], **coordinates: object) -> dict:
    found = [r for r in rows if all(r.get(k) == v for k, v in coordinates.items())]
    if len(found) != 1:
        raise RuntimeError(f"Expected one row at {coordinates}, found {len(found)}")
    return found[0]


def shares(values: dict[str, float]) -> dict[str, float]:
    raw = {n: max(0.0, float(values[n])) for n in NODES}
    total = sum(raw.values())
    if total <= 0:
        raise RuntimeError(f"Cannot normalize nonpositive node values: {values}")
    result = {n: raw[n] / total for n in NODES}
    # Put the floating-point closure on the largest positive member. This keeps
    # genuinely zero node allocations exactly zero instead of creating tiny
    # negative capacity bounds when national envelopes are split.
    anchor = max(NODES, key=lambda n: result[n])
    result[anchor] += 1.0 - sum(result.values())
    for node in NODES:
        if abs(result[node]) <= NONNEGATIVE_TOLERANCE:
            result[node] = 0.0
    return result


def adjusted_2020(inputs: dict, kind: str, field: str | None = None) -> dict[str, float]:
    table = inputs["sales_gwh"]["2020"] if kind == "sales" else inputs["consumption_gwh"]["2020"]
    broad = shares(inputs["offgrid_installed_mw_2020_by_broad_group"])
    off_total = OFFGRID_SALES_2020 if kind == "sales" else OFFGRID_CONSUMPTION_2020
    result = {}
    for node in NODES:
        if kind == "sales":
            total = float(table[node]["total"])
            value = float(table[node][field or "total"])
            result[node] = value * (total - off_total * broad[node]) / total
        else:
            result[node] = float(table[node]) - off_total * broad[node]
    return result


def history_values(inputs: dict, year: str, table: str, field: str | None = None) -> dict[str, float]:
    if year == "2020" and table in ("sales_gwh", "consumption_gwh"):
        return adjusted_2020(inputs, "sales" if table == "sales_gwh" else "consumption", field)
    if table == "sales_gwh":
        return {n: float(inputs[table][year][n][field or "total"]) for n in NODES}
    return {n: float(inputs[table][year][n]) for n in NODES}


def value_by_year(history: dict[str, float], year: str) -> float:
    return history[year] if year in history else history["2024"]


def clone_rows(payload: dict, old_id: str, new_id: str, comm_map: dict[str, str]) -> None:
    for parameter in payload.values():
        if not isinstance(parameter, dict):
            continue
        for rows in parameter.values():
            if not isinstance(rows, list):
                continue
            additions = []
            for row in rows:
                if row.get("TechId") != old_id:
                    continue
                new = copy.deepcopy(row)
                new["TechId"] = new_id
                if "CommId" in new and new["CommId"] in comm_map:
                    new["CommId"] = comm_map[new["CommId"]]
                additions.append(new)
            rows.extend(additions)


def remove_rows(payload: dict, tech_id: str) -> None:
    for parameter in payload.values():
        if not isinstance(parameter, dict):
            continue
        for scenario, rows in list(parameter.items()):
            if isinstance(rows, list):
                parameter[scenario] = [r for r in rows if r.get("TechId") != tech_id]


class Builder:
    def __init__(self, case: Path, inputs: dict, bundle_capacity_bound: float):
        self.case = case
        self.inputs = inputs
        self.gen = load(case / "genData.json")
        self.rt = load(case / "RT.json")
        self.payloads = {name: load(case / name) for name in TECH_FILES if (case / name).is_file()}
        self.tech_ids = {r["Tech"]: r["TechId"] for r in self.gen["osy-tech"]}
        self.comm_ids = {r["Comm"]: r["CommId"] for r in self.gen["osy-comm"]}
        self.next_tech = 1
        self.next_comm = 1
        self.next_con = 1
        self.clones: dict[str, dict[str, str]] = {}
        self.node_comms: dict[str, dict[str, str]] = {}
        self.bundle_capacity_bound = bundle_capacity_bound

    def new_tech_id(self) -> str:
        value = f"TEC_is1{self.next_tech:03d}"
        self.next_tech += 1
        return value

    def new_comm(self, name: str, description: str, unit: str = "PJ") -> str:
        cid = f"COM_is1{self.next_comm:03d}"
        self.next_comm += 1
        self.gen["osy-comm"].append({"CommId": cid, "Comm": name, "Desc": description, "UnitId": unit})
        self.comm_ids[name] = cid
        return cid

    def clone_tech(self, old_name: str, new_name: str, description: str,
                   comm_map: dict[str, str], scale: float = 1.0) -> str:
        old_id = self.tech_ids[old_name]
        new_id = self.new_tech_id()
        source = one(self.gen["osy-tech"], TechId=old_id)
        new = copy.deepcopy(source)
        new.update({"TechId": new_id, "Tech": new_name, "Desc": description})
        for key in ("IAR", "OAR", "INCR", "ITCR"):
            new[key] = [comm_map.get(cid, cid) for cid in new.get(key, [])]
        self.gen["osy-tech"].append(new)
        for parameter in self.rt.values():
            for rows in parameter.values():
                if rows and old_id in rows[0]:
                    rows[0][new_id] = rows[0][old_id]
        for payload in self.payloads.values():
            clone_rows(payload, old_id, new_id, comm_map)
        ryt = self.payloads["RYT.json"]
        for parameter in ("RC", "TAMaxC", "TAMaxCI", "TAMinC", "TAMinCI"):
            for rows in ryt[parameter].values():
                row = one(rows, TechId=new_id)
                for year in YEARS:
                    if row[year] is not None:
                        value = float(row[year]) * scale
                        row[year] = 0.0 if abs(value) <= NONNEGATIVE_TOLERANCE else value
        self.tech_ids[new_name] = new_id
        return new_id

    def remove_tech(self, name: str) -> None:
        tid = self.tech_ids[name]
        self.gen["osy-tech"] = [r for r in self.gen["osy-tech"] if r["TechId"] != tid]
        for parameter in self.rt.values():
            for rows in parameter.values():
                if rows:
                    rows[0].pop(tid, None)
        for payload in self.payloads.values():
            remove_rows(payload, tid)
        for con in self.gen["osy-constraints"]:
            con["CM"] = [x for x in con["CM"] if x != tid]

    def replace_constraint_member(self, old_name: str, new_ids: list[str]) -> None:
        old_id = self.tech_ids[old_name]
        for con in self.gen["osy-constraints"]:
            if old_id in con["CM"]:
                result = []
                for tid in con["CM"]:
                    result.extend(new_ids if tid == old_id else [tid])
                con["CM"] = result

    def prepare_commodities(self) -> None:
        gross = self.comm_ids["PHL_POW_ELE"]
        sales = self.comm_ids["PHL_POW_ELE1"]
        heat = self.comm_ids["PHL_PWR_WAT"]
        for node in NODES:
            self.node_comms[node] = {
                gross: self.new_comm(f"PHL_POW_ELE_{node}", f"Gross electricity at the {node} grid bus"),
                sales: self.new_comm(f"PHL_POW_ELE1_{node}", f"Post-loss electricity at the {node} grid bus"),
                heat: self.new_comm(f"PHL_PWR_WAT_{node}", f"Cooling-water service for {node} grid thermal generation", "10<sup>9</sup>m<sup>3</sup>"),
            }

    def resource_shares(self) -> dict[str, dict[str, float]]:
        result = {k: shares(v) for k, v in self.inputs["installed_mw_2020"].items()}
        result["gas"] = {"LUZ": 1.0, "VIS": 0.0, "MIN": 0.0}
        peak = self.inputs["peak_mw"]["2020"]
        result["load"] = shares(peak)
        return result

    def split_generation(self) -> None:
        gross = self.comm_ids["PHL_POW_ELE"]
        heat = self.comm_ids["PHL_PWR_WAT"]
        resource = self.resource_shares()
        for name, basis in GENERATION.items():
            ids = []
            self.clones[name] = {}
            for node in NODES:
                mapping = dict(self.node_comms[node])
                mapping[gross] = self.node_comms[node][gross]
                mapping[heat] = self.node_comms[node][heat]
                new_name = f"{name}_{node}"
                tid = self.clone_tech(
                    name, new_name,
                    f"{one(self.gen['osy-tech'], Tech=name)['Desc']} [{node} grid node]",
                    mapping, resource[basis][node],
                )
                ids.append(tid)
                self.clones[name][node] = tid
            self.replace_constraint_member(name, ids)
        for name in GENERATION:
            self.remove_tech(name)

    def split_grid_services(self) -> None:
        gross = self.comm_ids["PHL_POW_ELE"]
        sales = self.comm_ids["PHL_POW_ELE1"]
        load_share = shares(self.inputs["peak_mw"]["2020"])
        # Only the physical grid and genuinely sitable grid loads are cloned.
        # The six sector delivery technologies remain single accounting
        # devices and are converted below to fixed-proportion node bundles.
        names = ("PHL_POW_TD", *DIRECT_GRID)
        for name in names:
            ids = []
            self.clones[name] = {}
            for node in NODES:
                mapping = {gross: self.node_comms[node][gross], sales: self.node_comms[node][sales]}
                tid = self.clone_tech(name, f"{name}_{node}",
                                      f"{one(self.gen['osy-tech'], Tech=name)['Desc']} [{node} grid node]",
                                      mapping, load_share[node])
                ids.append(tid)
                self.clones[name][node] = tid
            self.replace_constraint_member(name, ids)
        for name in names:
            self.remove_tech(name)

        # Grid cooling is cloned by node; national cooling remains for OFF.
        for name in COOLING:
            self.clones[name] = {}
            for node in NODES:
                mapping = {
                    gross: self.node_comms[node][gross],
                    self.comm_ids["PHL_PWR_WAT"]: self.node_comms[node][self.comm_ids["PHL_PWR_WAT"]],
                }
                tid = self.clone_tech(name, f"{name}_{node}",
                                      f"{one(self.gen['osy-tech'], Tech=name)['Desc']} [{node} grid node]",
                                      mapping, load_share[node])
                self.clones[name][node] = tid

    def configure_sector_electricity_bundles(self) -> None:
        """Replace 18 tied node-sector paths and 12 ratio UDCs with six bundles.

        Each existing national sector T&D technology consumes LUZ, VIS and MIN
        post-loss electricity simultaneously in observed geographic
        proportions. Its national sector-electricity output and all downstream
        fuel/service choices remain unchanged and endogenous.
        """
        sales = self.comm_ids["PHL_POW_ELE1"]
        cm = self.payloads["RYTCM.json"]
        ryt = self.payloads["RYT.json"]
        self.bundle_techs = []
        for tech_name, field in SECTOR_TD.items():
            tid = self.tech_ids[tech_name]
            tech = one(self.gen["osy-tech"], TechId=tid)
            tech["IAR"] = [self.node_comms[node][sales] for node in NODES]
            self.bundle_techs.append(tid)
            for scenario in cm["IAR"]:
                original = [r for r in cm["IAR"][scenario]
                            if r.get("TechId") == tid and r.get("CommId") == sales]
                cm["IAR"][scenario] = [r for r in cm["IAR"][scenario]
                                        if not (r.get("TechId") == tid and r.get("CommId") == sales)]
                modes = sorted({int(r["MoId"]) for r in original}) or [1]
                for mode in modes:
                    source = next((r for r in original if int(r["MoId"]) == mode), None)
                    for node in NODES:
                        row = {"TechId": tid, "CommId": self.node_comms[node][sales], "MoId": mode}
                        for year in YEARS:
                            if scenario != SC_BASE:
                                row[year] = None
                                continue
                            source_year = year if year in HISTORY else "2024"
                            geographic = shares(history_values(self.inputs, source_year, "sales_gwh", field))[node]
                            base_ratio = float(source[year]) if source and source[year] is not None else 1.0
                            row[year] = base_ratio * geographic
                        cm["IAR"][scenario].append(row)

            # Accounting capacity is fixed and non-investable. The finite bound
            # is four times the largest canonical v36 annual grid-use witness;
            # the preflight proves it cannot bind that unchanged demand path.
            for parameter in ryt:
                for scenario, rows in ryt[parameter].items():
                    row = one(rows, TechId=tid)
                    for year in YEARS:
                        if scenario != SC_BASE:
                            continue
                        if parameter in ("RC", "TAMaxC"):
                            row[year] = self.bundle_capacity_bound
                        elif parameter in ("TAMaxCI", "TAMinC", "TAMinCI"):
                            row[year] = 0.0
                        elif parameter in ("CC", "FC"):
                            row[year] = 0.0
                        elif parameter == "AF":
                            row[year] = 1.0
    def add_interconnectors(self) -> None:
        gross = self.comm_ids["PHL_POW_ELE"]
        td_template = next(iter(self.clones["PHL_POW_TD"].values()))
        template_name = one(self.gen["osy-tech"], TechId=td_template)["Tech"]
        self.interconnector_ids = {}
        for key, spec in self.inputs["interconnectors"].items():
            a, b = spec["from"], spec["to"]
            aid, bid = self.node_comms[a][gross], self.node_comms[b][gross]
            tid = self.clone_tech(template_name, f"PHL_POW_INT_{key}",
                                  f"Bidirectional {a}-{b} interconnector; two modes share one capacity", {}, 1.0)
            self.interconnector_ids[key] = tid
            tech = one(self.gen["osy-tech"], TechId=tid)
            tech["IAR"], tech["OAR"] = [aid, bid], [aid, bid]
            cm = self.payloads["RYTCM.json"]
            for parameter in ("IAR", "OAR"):
                for scenario in cm[parameter]:
                    cm[parameter][scenario] = [r for r in cm[parameter][scenario] if r.get("TechId") != tid]
            loss = 1.0 - float(spec["loss_fraction"])
            relations = (("IAR", aid, 1, 1.0), ("OAR", bid, 1, loss),
                         ("IAR", bid, 2, 1.0), ("OAR", aid, 2, loss))
            for parameter, cid, mode, value in relations:
                for scenario in cm[parameter]:
                    row = {"TechId": tid, "CommId": cid, "MoId": mode}
                    row.update({y: (value if scenario == SC_BASE else None) for y in YEARS})
                    cm[parameter][scenario].append(row)
            ryt = self.payloads["RYT.json"]
            for parameter in ryt:
                row = one(ryt[parameter][SC_BASE], TechId=tid)
                for y in YEARS:
                    year = int(y)
                    if parameter == "RC":
                        row[y] = 0.44 if key == "LV" else (0.45 if year >= 2023 else 0.0)
                    elif parameter == "CC": row[y] = float(spec["capital_cost_musd_per_gw"])
                    elif parameter == "FC": row[y] = 0.0
                    elif parameter == "AF": row[y] = 1.0
                    elif parameter == "TAMaxCI": row[y] = float(spec["additional_limit_gw"]) if year >= int(spec["additional_from_year"]) else 0.0
                    elif parameter == "TAMaxC":
                        residual = 0.44 if key == "LV" else (0.45 if year >= 2023 else 0.0)
                        row[y] = residual + (float(spec["additional_limit_gw"]) if year >= int(spec["additional_from_year"]) else 0.0)
            for parameter, rows in self.payloads["RYTM.json"].items():
                for row in rows[SC_BASE]:
                    if row.get("TechId") == tid:
                        for y in YEARS:
                            if parameter == "VC": row[y] = 0.0
                            elif parameter in ("TAMUL", "TAIML"): row[y] = 99999.0
                            elif parameter in ("TAMLL", "TADML"): row[y] = 0.0

    def set_td_losses(self) -> None:
        cm = self.payloads["RYTCM.json"]
        gross = self.comm_ids["PHL_POW_ELE"]
        for node in NODES:
            tid = self.clones["PHL_POW_TD"][node]
            cid = self.node_comms[node][gross]
            row = one(cm["IAR"][SC_BASE], TechId=tid, CommId=cid, MoId=1)
            ratios = {}
            for y in HISTORY:
                sales = history_values(self.inputs, y, "sales_gwh")[node]
                consumption = history_values(self.inputs, y, "consumption_gwh")[node]
                ratios[y] = consumption / sales
            for y in YEARS:
                row[y] = value_by_year(ratios, y)

    def add_constraint(self, name: str, description: str, tag: int, members: list[str]) -> str:
        cid = f"CO_is1{self.next_con:03d}"
        self.next_con += 1
        self.gen["osy-constraints"].append({"ConId": cid, "Con": name, "Desc": description, "Tag": tag, "CM": members})
        return cid

    def add_reserve_constraints(self) -> None:
        old = next(c for c in self.gen["osy-constraints"] if c["Con"] == "PHL_POW_RESERVE_MARGIN")
        self.gen["osy-constraints"].remove(old)
        self.reserve_constraints = []
        reserve_members = [name for name in GENERATION if name not in (
            "PHL_POW_PP_WON", "PHL_POW_PP_WOF", "PHL_POW_PP_SPV", "PHL_POW_PP_H2"
        )]
        for node in NODES:
            members = [self.clones[name][node] for name in reserve_members]
            adjacent = [tid for key, tid in self.interconnector_ids.items()
                        if node in (self.inputs["interconnectors"][key]["from"], self.inputs["interconnectors"][key]["to"])]
            members += adjacent + [self.clones["PHL_POW_TD"][node]]
            cid = self.add_constraint(
                f"PHL_POW_RESERVE_MARGIN_{node}",
                f"DOE 25% {node} planning reserve with local dependable capacity and half-credit for adjacent interconnector capacity.",
                0, members,
            )
            self.reserve_constraints.append((cid, node, reserve_members, adjacent))

    def write_and_normalize(self) -> None:
        self.gen["osy-casename"] = "Philippines_vIS1.1"
        self.gen["osy-date"] = "2026-08-28"
        self.gen["osy-desc"] = (
            "Philippines vIS1.1: stabilized data-only Luzon-Visayas-Mindanao plus isolated OFF nodal power pilot. "
            "Generation is endogenous; installed stock, grid load geography, losses, transfer limits and adequacy are structural inputs."
        )
        dump(self.case / "genData.json", self.gen)
        dump(self.case / "RT.json", self.rt)
        for name, payload in self.payloads.items():
            dump(self.case / name, payload)
        sys.path.insert(0, str(ROOT / "API"))
        from Classes.Case.UpdateCaseClass import UpdateCase
        UpdateCase(self.case.name, self.gen).updateCase()

    def populate_constraints_after_normalize(self) -> None:
        rycn = load(self.case / "RYCn.json")
        rytcn = load(self.case / "RYTCn.json")
        # Every new equality/inequality uses a zero constant.
        for cid, *_ in self.reserve_constraints:
            for row in rycn["UCC"][SC_BASE]:
                if row["ConId"] == cid:
                    for y in YEARS: row[y] = 0.0
        # BASE has no nuclear policy target. Retain an explicit neutral RHS so
        # scenario overlays cannot inherit a preceding constraint value when
        # all active nuclear cells are null. Member coefficients remain absent,
        # so this is only 0 = 0 and does not force nuclear capacity or activity.
        nuclear = next(c for c in self.gen["osy-constraints"] if c["Con"] == "NUCLEAR_CAPACITY_TARGET")
        for row in rycn["UCC"][SC_BASE]:
            if row["ConId"] == nuclear["ConId"]:
                for y in YEARS: row[y] = 0.0
        for parameter in ("CAM", "CCM"):
            for row in rytcn[parameter][SC_BASE]:
                if row.get("ConId") == nuclear["ConId"]:
                    for y in YEARS: row[y] = 0.0
        # Capacity-credit coefficients use DOE dependable shares, normalized to
        # the inherited v36 capacity-credit total, without changing RC/AF totals.
        installed = {k: shares(v) for k, v in self.inputs["installed_mw_2020"].items()}
        dependable = {k: shares(v) for k, v in self.inputs["dependable_mw_2020"].items()}
        base_ryt = load(self.case / "RYT.json")
        national_af = {}
        # All clones retain the v36 national AF; use it as the exact control credit.
        for name, basis in LEGACY.items():
            national_af[name] = float(one(base_ryt["AF"][SC_BASE], TechId=self.clones[name]["LUZ"])["2020"])
        credit_basis = {
            **{name: basis for name, basis in LEGACY.items()},
            "PHL_POW_PP_COAL": "coal", "PHL_POW_PP_COAL_CCS": "coal",
            "PHL_POW_PP_NGCC": "gas", "PHL_POW_PP_NGCC_CCS": "gas",
            "PHL_POW_PP_NU": "load", "PHL_POW_PP_NUSMR": "load",
            "PHL_POW_PP_H2": "load", "PHL_POW_PP_BIOM_CCS": "biomass",
        }
        candidate_credit = {
            "PHL_POW_PP_COAL": .85, "PHL_POW_PP_COAL_CCS": .83,
            "PHL_POW_PP_NGCC": .90, "PHL_POW_PP_NGCC_CCS": .88,
            "PHL_POW_PP_NU": .90, "PHL_POW_PP_NUSMR": .90,
            "PHL_POW_PP_H2": .90, "PHL_POW_PP_BIOM_CCS": .80,
        }
        for cid, node, reserve_members, adjacent in self.reserve_constraints:
            for name in reserve_members:
                tid = self.clones[name][node]
                row = one(rytcn["CCM"][SC_BASE], TechId=tid, ConId=cid)
                basis = credit_basis[name]
                base_credit = national_af.get(name, candidate_credit.get(name, .80))
                if basis in installed:
                    coeff = base_credit * dependable[basis][node] / installed[basis][node] if installed[basis][node] else 0.0
                else:
                    coeff = base_credit
                for y in YEARS: row[y] = -coeff
            for tid in adjacent:
                row = one(rytcn["CCM"][SC_BASE], TechId=tid, ConId=cid)
                for y in YEARS: row[y] = -float(self.inputs["assumptions"]["interconnector_dependable_credit_each_end"])
            td = self.clones["PHL_POW_TD"][node]
            row = one(rytcn["CAM"][SC_BASE], TechId=td, ConId=cid)
            for y in YEARS:
                source_year = y if y in HISTORY else "2024"
                peak_gw = float(self.inputs["peak_mw"][source_year][node]) / 1000.0
                sales_pj = history_values(self.inputs, source_year, "sales_gwh")[node] * .0036
                row[y] = 1.25 * peak_gw / sales_pj
        dump(self.case / "RYCn.json", rycn)
        dump(self.case / "RYTCn.json", rytcn)

    def clamp_and_validate_capacity_parameters(self) -> None:
        path = self.case / "RYT.json"
        ryt = load(path)
        errors = []
        for parameter in ("RC", "TAMaxC", "TAMaxCI", "TAMinC", "TAMinCI"):
            for scenario, rows in ryt[parameter].items():
                for row in rows:
                    for year in YEARS:
                        value = row[year]
                        if value is None:
                            continue
                        numeric = float(value)
                        if abs(numeric) <= NONNEGATIVE_TOLERANCE:
                            row[year] = 0.0
                        elif numeric < 0:
                            errors.append([parameter, scenario, row["TechId"], year, numeric])
        if errors:
            raise RuntimeError(f"Negative capacity parameters survive tolerance clamp: {errors[:20]}")
        dump(path, ryt)

    def remove_unsupported_oil_import_floor(self) -> None:
        """Remove the inherited COAL_PHASEOUT minimum oil-import trajectory."""
        path = self.case / "RYT.json"
        ryt = load(path)
        oil_import = one(self.gen["osy-tech"], Tech="PHL_PRO_IMP_OIL")
        row = one(ryt["TAL"][SC_COAL_PHASEOUT], TechId=oil_import["TechId"])
        before = {year: row[year] for year in YEARS}
        if not any(value is not None and float(value) > 0 for value in before.values()):
            raise RuntimeError("Expected inherited positive COAL_PHASEOUT oil-import TAL was not found")
        for year in YEARS:
            row[year] = None
        base = one(ryt["TAL"][SC_BASE], TechId=oil_import["TechId"])
        if any(float(base[year]) != 0.0 for year in YEARS):
            raise RuntimeError("BASE oil-import lower bound is not neutral")
        dump(path, ryt)
        dump(self.case / "documentation/oil_import_floor_removal_vIS12.json", {
            "case": "Philippines_vIS1.2",
            "technology": "PHL_PRO_IMP_OIL",
            "parameter": "TotalTechnologyAnnualActivityLowerLimit",
            "scenario": "COAL_PHASEOUT",
            "before": before,
            "after": {year: None for year in YEARS},
            "effective_after": {year: 0.0 for year in YEARS},
            "classification": "open import backstop; activity remains endogenous",
            "reason": "No retained physical, legal or policy basis; inherited lower bound contradicted the provenance ledger and mechanically compelled imports.",
            "non_forcing": True,
            "optimizer_runs": 0,
        })

    def audit(self, parent_hashes: dict[str, str]) -> None:
        docs = self.case / "documentation"
        docs.mkdir(exist_ok=True)
        allocation = {
            "case": "Philippines_vIS1.1", "parent": "Philippines_v36",
            "non_forcing": True, "observed_generation_role": "benchmark_only",
            "nodes": [*NODES, "OFF"], "off_grid_technologies_unchanged": ["PHL_POW_CHP_OIL_OFFGRID", "PHL_POW_RE_OFFGRID"],
            "generation_clones": self.clones,
            "interconnectors": self.inputs["interconnectors"],
            "load_share_method": "six fixed-proportion node-electricity bundle technologies; total sector electricity and fuel choice remain endogenous",
            "bundle_capacity_bound": self.bundle_capacity_bound,
            "fuel_delivery_method": "applicable node generators consume national fuels directly; gas build envelopes remain Luzon-only",
            "timeslice_profile": self.inputs["assumptions"]["timeslice_profile"],
            "national_land_water_status": self.inputs["assumptions"]["water_and_land"],
            "parent_hashes": parent_hashes,
            "candidate_hashes": {p.name: sha256(p) for p in self.case.glob("*.json")},
        }
        dump(docs / "spatial_power_source_change_vIS11.json", allocation)


def derive_cluster_crosswalk(case: Path) -> None:
    source = case / "data_sources/evidence/v32_rice_spatial_yield/derived/phl_rice_province_cluster_allocation_2020.csv"
    lookup = {}
    with LOOKUP.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream): lookup[row["province"]] = row
    totals: dict[tuple[str, str], float] = {}
    with source.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            province = row["province"]
            if province not in lookup: raise RuntimeError(f"Missing province node: {province}")
            key = (row["clusters_yield"], lookup[province]["node"])
            # Each geometry is repeated for irrigated/rainfed; retain one area record.
            if row["regime"] == "irrigated": totals[key] = totals.get(key, 0.0) + float(row["allocated_sqkm"])
    out = case / "documentation/cluster_node_area_crosswalk_vIS11.csv"
    cluster_totals = {c: sum(v for (cc, _), v in totals.items() if cc == c) for c, _ in totals}
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["cluster", "node", "area_sqkm", "cluster_area_share", "model_status"])
        for (cluster, node), area in sorted(totals.items(), key=lambda x: (int(x[0][0]), x[0][1])):
            writer.writerow([cluster, node, f"{area:.12f}", f"{area / cluster_totals[cluster]:.15g}", "retained_crosswalk_not_applied_in_power_pilot"])


def append_model_fixes(case: Path) -> None:
    path = case / "MODEL_FIXES_ISLAND_POWER_VIS11_2026-08-28.md"
    path.write_text("""# Philippines vIS1.1 stabilized island-power pilot

## Source change

vIS1.1 is a clean data-only successor to v36. It retains one OSeMOSYS region, represents LUZ, VIS and MIN through node electricity commodities, and keeps OFF isolated. No MUIOGO or OSeMOSYS equation changed. Observed generation and post-2020 capacity additions remain benchmark-only.

Six national sector-delivery accounting technologies now consume the three node electricity commodities simultaneously in sourced geographic proportions. This replaces eighteen node-sector pass-throughs and twelve annual ratio equalities without fixing total electricity use. Fifteen zero-cost, lossless fuel-renaming technologies and their node fuel commodities are omitted; applicable generators consume existing national fuel commodities directly, while natural-gas build envelopes remain Luzon-only.

Capacity allocations below 1e-9 are clamped to exact zero. Sector-bundle capacity is fixed, finite and non-investable. Interconnector total capacity is capped cumulatively. The inactive BASE nuclear equality has explicit zero constants and zero member coefficients, preventing null scenario-overlay cells from inheriting another constraint's value without forcing nuclear capacity. Hydrogen generation receives no firm reserve credit pending a firm-fuel basis.

The inherited COAL_PHASEOUT lower activity bound on `PHL_PRO_IMP_OIL` is removed. It first appeared in the earliest retained v9 case as a linear 184.56-PJ-to-zero trajectory, had no retained source or policy rationale, and contradicted the later classification of oil imports as an open endogenous backstop. COAL_PHASEOUT now inherits BASE's zero lower bound; no import cap, target or share is introduced.

DOE annual grid sales and peaks are retained, but nodes still inherit v36's normalized timeslice shape. Coal, petroleum and biomass delivery remain provisionally national pending spatial delivery/resource evidence. Land and water remain national.

## Validation authorization

One BASE optimization is authorized after deterministic source, application-generation, preprocessing and `glpsol --check` gates, with a hard 360-second deadline. Stop after optimal, infeasible, failure or timeout. Policy scenarios are not authorized in this run.
""", encoding="utf-8")


def canonical_bundle_capacity_bound(source: Path) -> float:
    """Finite nonbinding accounting bound from the verified canonical witness."""
    path = source / "res/BASE_V36_POWER_GAS_HISTORY/csv/UseByTechnologyByMode.csv"
    annual = {year: 0.0 for year in YEARS}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["f"] == "PHL_POW_ELE":
                annual[row["y"]] += float(row["UseByTechnologyByMode"])
    if not all(value > 0 for value in annual.values()):
        raise RuntimeError("Canonical v36 electricity-use witness is incomplete")
    return BUNDLE_HEADROOM_FACTOR * max(annual.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=STORAGE / "Philippines_v36")
    parser.add_argument("--target", type=Path, default=STORAGE / ".Philippines_vIS11-candidate-20260828")
    args = parser.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    if target.exists(): raise RuntimeError(f"Target already exists: {target}")
    inputs = load(INPUT)
    if load(source / "genData.json").get("osy-casename") != "Philippines_v36":
        raise RuntimeError("Source is not Philippines_v36")
    parent_files = ("genData.json", "RT.json", *TECH_FILES, "RYC.json", "RYCTs.json", "RYCn.json")
    parent_hashes = {name: sha256(source / name) for name in parent_files if (source / name).is_file()}
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("res", "view", "SEALED_CANDIDATE.json", "PROMOTION_RECEIPT.json"))
    (target / "res").mkdir(exist_ok=True)
    (target / "view").mkdir(exist_ok=True)
    dump(target / "view/resData.json", {"osy-cases": []})
    builder = Builder(target, inputs, canonical_bundle_capacity_bound(source))
    builder.prepare_commodities()
    builder.split_generation()
    builder.split_grid_services()
    builder.configure_sector_electricity_bundles()
    builder.add_interconnectors()
    builder.set_td_losses()
    builder.add_reserve_constraints()
    builder.write_and_normalize()
    builder.populate_constraints_after_normalize()
    builder.remove_unsupported_oil_import_floor()
    builder.clamp_and_validate_capacity_parameters()
    derive_cluster_crosswalk(target)
    shutil.copy2(INPUT, target / "documentation/spatial_inputs_vIS11.json")
    shutil.copy2(LOOKUP, target / "documentation/province_node_lookup_vIS11.csv")
    append_model_fixes(target)
    builder.audit(parent_hashes)
    print(json.dumps({"status": "built", "target": str(target), "technologies": len(builder.gen["osy-tech"]), "commodities": len(builder.gen["osy-comm"]), "constraints": len(builder.gen["osy-constraints"])}, indent=2))


if __name__ == "__main__":
    main()
