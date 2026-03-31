import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import time

st.set_page_config(
    page_title="MUIOGO — OG-CLEWS Modelling",
    page_icon="assets/favicon.ico" if False else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Colours taken from the existing SmartAdmin palette used in osy.css:
# primary sidebar:  #1a3a5c (matches smart-style-4 dark nav)
# accent blue:      #009edb (UN blue)
# text-dark:        #3a3f51 (matches the jarviswidget header text colour)
# panel border:     #e4e4e4
# success green:    #40864a
# warning amber:    #da8826
# log bg:           #1e1e1e  (matches .log-output pre blocks in the app)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Open Sans', sans-serif;
        font-size: 13px;
    }

    /* Sidebar — matches smart-style-4 in the existing SmartAdmin theme */
    [data-testid="stSidebar"] {
        background: #1a3a5c;
    }
    [data-testid="stSidebar"] * {
        color: #c9d8e8 !important;
    }
    [data-testid="stSidebar"] h2 {
        color: #ffffff !important;
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    [data-testid="stSidebar"] .stRadio > label {
        font-size: 12px;
        color: #a0b8cc !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }

    /* Main area */
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1280px;
    }

    /* Panel header — matches .jarviswidget header style */
    .panel-header {
        background: #3a3f51;
        color: #ffffff;
        padding: 9px 15px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 4px 4px 0 0;
        margin-bottom: 0;
        border-bottom: 2px solid #009edb;
    }

    /* Metric strip — matches the top summary bar pattern from the existing UI */
    .metric-strip {
        background: #ffffff;
        border: 1px solid #e4e4e4;
        border-top: 3px solid #009edb;
        border-radius: 4px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .metric-strip .val {
        font-size: 22px;
        font-weight: 700;
        color: #3a3f51;
        line-height: 1.2;
    }
    .metric-strip .label {
        font-size: 11px;
        color: #8a8a8a;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .metric-strip .delta-up   { color: #40864a; font-size: 11px; }
    .metric-strip .delta-down { color: #c0392b; font-size: 11px; }

    /* Status badge */
    .badge-draft     { background: #8a8a8a; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
    .badge-running   { background: #da8826; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
    .badge-done      { background: #40864a; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
    .badge-error     { background: #c0392b; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; }

    /* Run log — matches .log-output pre in the DataFile view */
    .run-log {
        background: #1e1e1e;
        color: #c5c8c6;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        padding: 12px 14px;
        border-radius: 4px;
        max-height: 240px;
        overflow-y: auto;
        line-height: 1.55;
    }

    /* Mode tabs */
    .model-tag {
        display: inline-block;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 3px;
        margin-right: 4px;
    }
    .tag-clews      { background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
    .tag-ogcore     { background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9; }
    .tag-coupled    { background: #fff3e0; color: #bf360c; border: 1px solid #ffcc80; }
    .tag-converging { background: #f3e5f5; color: #6a1b9a; border: 1px solid #ce93d8; }

    /* Mode cards on home page */
    .mode-card {
        background: #ffffff;
        border: 1px solid #e4e4e4;
        border-left: 4px solid #009edb;
        border-radius: 4px;
        padding: 16px 18px;
        height: 100%;
        transition: box-shadow 0.15s;
    }
    .mode-card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.1); }
    .mode-card h4 { font-size: 14px; font-weight: 600; color: #3a3f51; margin-bottom: 6px; }
    .mode-card p  { font-size: 12px; color: #666; line-height: 1.5; margin-bottom: 8px; }

    /* Section heading — matches the .osy-second-color header pattern */
    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: #3a3f51;
        border-bottom: 2px solid #009edb;
        padding-bottom: 6px;
        margin: 18px 0 14px;
    }

    /* Param hint text */
    .param-hint {
        font-size: 11px;
        color: #999;
        font-style: italic;
        margin-top: -10px;
        margin-bottom: 10px;
    }

    /* Footer */
    .page-footer {
        font-size: 11px;
        color: #aaaaaa;
        text-align: center;
        border-top: 1px solid #e4e4e4;
        padding-top: 14px;
        margin-top: 40px;
    }

    /* Streamlit button override */
    .stButton > button {
        background: #009edb;
        color: white;
        border: none;
        border-radius: 3px;
        font-size: 13px;
        font-weight: 600;
        padding: 6px 20px;
    }
    .stButton > button:hover {
        background: #007bb0;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ── session state ───────────────────────────────────────────────────────────

def _init():
    defaults = {
        "scenarios": {},
        "run_log": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## MUIOGO")
    st.markdown("<small>OG-CLEWS Integrated Modelling</small>", unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["Home", "Configure Scenario", "Run", "Results", "Coupled Pipeline", "About"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**Scenarios**")

    if st.session_state.scenarios:
        for name, data in st.session_state.scenarios.items():
            status = data.get("status", "draft")
            mtype  = data.get("model_type", "CLEWS")
            colors = {"draft": "#8a8a8a", "running": "#da8826", "done": "#40864a", "error": "#c0392b"}
            dot = f'<span style="color:{colors.get(status,"#8a8a8a")}">&#9679;</span>'
            st.markdown(f"{dot} `{name}` <small>({mtype})</small>", unsafe_allow_html=True)
    else:
        st.markdown("<small>No scenarios yet.</small>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<small>UN DESA · EAPD</small>", unsafe_allow_html=True)


# ── mock result generators ──────────────────────────────────────────────────

def _clews_results(name):
    years = list(range(2025, 2051))
    rng = np.random.default_rng(hash(name) % 9999)
    g = 0.03 + rng.uniform(-0.01, 0.01)
    return {
        "years": years,
        "energy_demand":    [100 * (1+g)**(y-2025) + rng.normal(0, 1.5) for y in years],
        "renewable_share": [min(0.15 + 0.022*(y-2025) + rng.normal(0, 0.01), 0.90) for y in years],
        "co2_emissions":   [80 * (0.97**(y-2025)) + rng.normal(0, 0.8) for y in years],
        "water_demand":    [50 * (1.02**(y-2025)) + rng.normal(0, 0.4) for y in years],
    }


def _ogcore_results(name, clews=None):
    years = list(range(2025, 2051))
    rng = np.random.default_rng((hash(name) + 77) % 9999)
    gdp = [100.0 * (1.03**(y-2025)) + rng.normal(0, 0.4) for y in years]
    if clews:
        # green energy share feeds into TFP growth — simple coupling demonstration
        gdp = [g + clews["renewable_share"][i] * 12 for i, g in enumerate(gdp)]
    return {
        "years": years,
        "gdp":           gdp,
        "gdp_pct":       [(g/100 - 1)*100 for g in gdp],
        "wages":         [1.0 * (1.025**(y-2025)) + rng.normal(0, 0.015) for y in years],
        "interest":      [0.05 - 0.0005*(y-2025) + rng.normal(0, 0.002) for y in years],
        "tax_revenue":   [g * 0.18 + rng.normal(0, 0.15) for g in gdp],
        "consumption":   [g * 0.62 for g in gdp],
        "investment":    [g * 0.20 for g in gdp],
    }


# ── home ────────────────────────────────────────────────────────────────────

if page == "Home":
    st.markdown("""
    <div style="background:#3a3f51; color:#fff; padding:20px 24px; border-radius:4px; 
                border-left:4px solid #009edb; margin-bottom:20px;">
        <h2 style="margin:0; font-size:18px; font-weight:700;">MUIOGO — OG-CLEWS Policy Modelling</h2>
        <p style="margin:6px 0 0; font-size:12px; opacity:0.8;">
            Integrated Climate-Economy analysis for sustainable development planning &nbsp;|&nbsp; UN DESA · EAPD
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    total = len(st.session_state.scenarios)
    done  = sum(1 for s in st.session_state.scenarios.values() if s.get("status") == "done")

    for col, label, val in [
        (c1, "Active Scenarios", total),
        (c2, "Completed Runs",   done),
        (c3, "Model Modes",      4),
        (c4, "Target Countries", "10+"),
    ]:
        col.markdown(f"""
        <div class="metric-strip">
            <div class="val">{val}</div>
            <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Execution Modes</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown("""
        <div class="mode-card">
            <h4>CLEWS / OSeMOSYS</h4>
            <p>Climate, Land, Energy and Water systems analysis.
               Assess energy mix, emissions trajectories and water use under different policy scenarios.</p>
            <span class="model-tag tag-clews">CLEWS</span>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown("""
        <div class="mode-card" style="border-left-color:#1565c0;">
            <h4>OG-Core</h4>
            <p>Overlapping-Generations macroeconomic model. Evaluate fiscal, tax and
               demographic policy effects on GDP, wages, interest rates and inequality.</p>
            <span class="model-tag tag-ogcore">OG-Core</span>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown("""
        <div class="mode-card" style="border-left-color:#bf360c;">
            <h4>Coupled Mode</h4>
            <p>Run CLEWS first, then pipe energy-sector outputs into OG-Core.
               One-way CLEWS → OG-Core exchange for integrated climate-economy analysis.</p>
            <span class="model-tag tag-coupled">Coupled</span>
        </div>
        """, unsafe_allow_html=True)

    with m4:
        st.markdown("""
        <div class="mode-card" style="border-left-color:#6a1b9a;">
            <h4>Converging Mode</h4>
            <p>Iterative CLEWS &harr; OG-Core feedback until convergence.
               Full-loop equilibrium suitable for long-run policy assessment.</p>
            <span class="model-tag tag-converging">Converging</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Use the sidebar to navigate to **Configure Scenario**, set your model parameters, then run.")

    if st.session_state.run_log:
        st.markdown('<div class="section-title">Recent Activity</div>', unsafe_allow_html=True)
        for entry in reversed(st.session_state.run_log[-5:]):
            st.markdown(f"&nbsp;&nbsp;{entry}")


# ── configure ───────────────────────────────────────────────────────────────

elif page == "Configure Scenario":
    st.markdown('<div class="section-title">Configure Scenario</div>', unsafe_allow_html=True)

    with st.form("scenario_form"):
        left, right = st.columns(2)

        with left:
            name = st.text_input(
                "Scenario Name",
                placeholder="e.g. PHL_2030_carbon_tax",
                help="Alphanumeric, hyphens and underscores only.",
            )
            model_type = st.selectbox(
                "Model Type",
                ["CLEWS", "OG-Core", "Coupled", "Converging"],
            )
            country = st.selectbox(
                "Country",
                ["Philippines (PHL)", "South Africa (ZAF)", "Indonesia (IDN)",
                 "Ethiopia (ETH)", "India (IND)", "Malaysia (MYS)", "Custom"],
            )
            base_year = st.number_input("Base Year", min_value=2020, max_value=2030, value=2025, step=1)
            horizon   = st.number_input("Planning Horizon (years)", min_value=10, max_value=50, value=25, step=5)

        with right:
            desc = st.text_area("Description", placeholder="Describe the policy scenario...", height=70)

            if model_type in ("OG-Core", "Coupled", "Converging"):
                st.markdown("**OG-Core Parameters**")
                st.markdown('<div class="param-hint">Key parameters from default_parameters.json</div>',
                            unsafe_allow_html=True)

                tab_hh, tab_fiscal, tab_econ = st.tabs(["Household", "Fiscal Policy", "Economic"])

                with tab_hh:
                    frisch = st.slider(
                        "Frisch Elasticity of Labor Supply",
                        min_value=0.20, max_value=0.62, value=0.40, step=0.01,
                        help="Controls how responsive labor supply is to wages. Valid range: 0.2 – 0.62",
                    )
                    st.markdown('<div class="param-hint">See Altonji (JPE 1986) for calibration guidance.</div>',
                                unsafe_allow_html=True)
                    S = st.slider("S — Max economic life periods", 3, 80, 80,
                                  help="Maximum number of periods an agent lives in the model.")
                    J = st.slider("J — Labor productivity types", 1, 10, 7,
                                  help="Number of heterogeneous household income groups.")

                with tab_fiscal:
                    income_tax = st.slider("Effective Income Tax Rate (%)", 0, 60, 25)
                    corp_tax   = st.slider("Corporate Tax Rate (%)", 0, 50, 30)
                    govt_gdp   = st.slider("Government Spending (% of GDP)", 10, 60, 20)

                with tab_econ:
                    g_y = st.slider("Annual TFP Growth Rate (%)", -1.0, 8.0, 3.0, 0.1,
                                    help="Exogenous growth rate of labor augmenting technological change.")
                    T   = st.slider("T — Periods to steady state", 3, 500, 320,
                                    help="Number of periods until the model reaches steady state.")

            else:
                st.markdown("**CLEWS / OSeMOSYS Parameters**")
                renewable_target = st.slider("Renewable Energy Target (%)", 10, 100, 40)
                carbon_price     = st.slider("Carbon Price ($/tCO2)", 0, 200, 50)
                discount_rate    = st.slider("Discount Rate (%)", 1, 15, 5,
                                             help="Maps to OSeMOSYS DiscountRate parameter.")
                st.markdown('<div class="param-hint">These map directly to OSeMOSYS model parameters.</div>',
                            unsafe_allow_html=True)

        saved = st.form_submit_button("Save Scenario")

        if saved:
            if not name.strip():
                st.error("Scenario name is required.")
            else:
                params = {
                    "country": country,
                    "base_year": base_year,
                    "horizon": horizon,
                    "desc": desc,
                }
                if model_type in ("OG-Core", "Coupled", "Converging"):
                    params.update({
                        "frisch": frisch, "S": S, "J": J,
                        "income_tax": income_tax, "corp_tax": corp_tax,
                        "govt_gdp": govt_gdp, "g_y": g_y / 100, "T": T,
                    })
                else:
                    params.update({
                        "renewable_target": renewable_target,
                        "carbon_price": carbon_price,
                        "discount_rate": discount_rate,
                    })

                st.session_state.scenarios[name] = {
                    "model_type": model_type,
                    "params": params,
                    "status": "draft",
                    "results": None,
                }
                st.session_state.run_log.append(f"Scenario **{name}** ({model_type}) configured")
                st.success(f"Scenario **{name}** saved. Navigate to **Run** to execute.")


# ── run ─────────────────────────────────────────────────────────────────────

elif page == "Run":
    st.markdown('<div class="section-title">Run Model</div>', unsafe_allow_html=True)

    if not st.session_state.scenarios:
        st.warning("No scenarios configured. Go to **Configure Scenario** first.")
    else:
        sel = st.selectbox("Select scenario", list(st.session_state.scenarios.keys()))
        sd  = st.session_state.scenarios[sel]
        mt  = sd["model_type"]
        status = sd["status"]

        tag_cls = {
            "CLEWS": "tag-clews", "OG-Core": "tag-ogcore",
            "Coupled": "tag-coupled", "Converging": "tag-converging",
        }.get(mt, "tag-clews")

        badge_cls = f"badge-{status}"

        st.markdown(f"""
        <div style="background:#fff; border:1px solid #e4e4e4; border-top:3px solid #3a3f51;
                    border-radius:4px; padding:12px 16px; margin-bottom:14px;">
            <b>Scenario:</b> {sel} &nbsp;
            <span class="model-tag {tag_cls}">{mt}</span> &nbsp;
            <span class="{badge_cls}">{status.upper()}</span><br>
            <span style="font-size:12px; color:#666;">
                Country: {sd['params'].get('country','—')} &nbsp;|&nbsp;
                Horizon: {sd['params'].get('horizon','—')} years
            </span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Pre-run validation**")
        checks = {
            "Scenario name set": bool(sel),
            "Parameters configured": bool(sd["params"]),
            "Model type selected": bool(mt),
            "Country specified": bool(sd["params"].get("country")),
        }
        for label, ok in checks.items():
            st.markdown(f"{'+ ' if ok else '- '} {label}"
                        .replace("+ ", "&#10003; ").replace("- ", "&#10007; "),
                        unsafe_allow_html=True)

        if all(checks.values()):
            if st.button("Run Simulation", disabled=(status == "running")):
                st.session_state.scenarios[sel]["status"] = "running"
                st.session_state.run_log.append(f"Started **{sel}** ({mt})")

                prog  = st.progress(0)
                stat  = st.empty()
                log   = st.empty()

                steps_map = {
                    "CLEWS": [
                        (10, "Loading OSeMOSYS model parameters..."),
                        (28, "Validating energy system data..."),
                        (50, "Solving LP problem (GLPK)..."),
                        (72, "Post-processing results..."),
                        (90, "Generating output files..."),
                        (100, "Done."),
                    ],
                    "OG-Core": [
                        (10, "Initialising OG-Core parameters..."),
                        (22, "Estimating tax functions..."),
                        (42, "Solving steady-state equilibrium..."),
                        (65, "Computing transition path (TPI)..."),
                        (85, "Generating macro aggregates..."),
                        (100, "Done."),
                    ],
                    "Coupled": [
                        (10, "[CLEWS] Loading OSeMOSYS model..."),
                        (27, "[CLEWS] Solving energy system (GLPK)..."),
                        (42, "[CLEWS] Extracting energy outputs..."),
                        (50, "Data exchange: CLEWS → OG-Core..."),
                        (62, "[OG-Core] Loading macroeconomic parameters..."),
                        (76, "[OG-Core] Solving steady state..."),
                        (90, "[OG-Core] Computing TPI solution..."),
                        (100, "Done."),
                    ],
                    "Converging": [
                        (8,  "Iteration 1: CLEWS run..."),
                        (18, "Iteration 1: data exchange CLEWS → OG-Core..."),
                        (28, "Iteration 1: OG-Core run..."),
                        (38, "Iteration 2: feedback OG-Core → CLEWS..."),
                        (50, "Iteration 2: CLEWS run (updated macro inputs)..."),
                        (62, "Iteration 2: OG-Core run (updated energy inputs)..."),
                        (70, "Convergence check: delta = 0.0041 (above threshold)..."),
                        (82, "Iteration 3: running coupled models..."),
                        (92, "Convergence check: delta = 0.00004 (below threshold)"),
                        (100, "Converged. Saving results..."),
                    ],
                }

                steps = steps_map.get(mt, steps_map["CLEWS"])
                logged = []
                for pct, msg in steps:
                    prog.progress(pct)
                    stat.markdown(f"**Status:** `{msg}`")
                    logged.append(f"[{pct:>3}%] {msg}")
                    log.markdown(
                        '<div class="run-log">' + "<br>".join(logged) + "</div>",
                        unsafe_allow_html=True,
                    )
                    time.sleep(0.35)

                cl = _clews_results(sel)   if mt in ("CLEWS", "Coupled", "Converging") else None
                og = _ogcore_results(sel, clews=cl) if mt in ("OG-Core", "Coupled", "Converging") else None

                st.session_state.scenarios[sel]["status"]  = "done"
                st.session_state.scenarios[sel]["results"] = {"clews": cl, "ogcore": og}
                st.session_state.run_log.append(f"Completed **{sel}**")
                st.success("Run complete. Navigate to **Results** to explore outputs.")


# ── results ─────────────────────────────────────────────────────────────────

elif page == "Results":
    st.markdown('<div class="section-title">Results</div>', unsafe_allow_html=True)

    done = {k: v for k, v in st.session_state.scenarios.items() if v["status"] == "done"}
    if not done:
        st.warning("No completed runs yet. Run a scenario first.")
    else:
        sel     = st.selectbox("Scenario", list(done.keys()))
        sd      = st.session_state.scenarios[sel]
        results = sd["results"]
        mt      = sd["model_type"]

        st.markdown(
            f"Model: `{mt}` &nbsp;|&nbsp; Country: {sd['params'].get('country','—')} "
            f"&nbsp;|&nbsp; Horizon: {sd['params'].get('horizon')} years",
            unsafe_allow_html=True,
        )

        # CLEWS results block
        if results.get("clews"):
            c  = results["clews"]
            yr = c["years"]

            st.markdown('<div class="section-title">CLEWS / OSeMOSYS Results</div>',
                        unsafe_allow_html=True)

            k1, k2, k3, k4 = st.columns(4)
            kw = [
                (k1, "Final Energy Demand", f"{c['energy_demand'][-1]:.1f} PJ",
                 f"+{c['energy_demand'][-1]-c['energy_demand'][0]:.1f} PJ", True),
                (k2, "Renewable Share (2050)", f"{c['renewable_share'][-1]*100:.1f}%",
                 f"+{(c['renewable_share'][-1]-c['renewable_share'][0])*100:.1f}%", True),
                (k3, "CO2 Emissions (2050)", f"{c['co2_emissions'][-1]:.1f} MtCO2",
                 f"{c['co2_emissions'][-1]-c['co2_emissions'][0]:.1f} MtCO2", False),
                (k4, "Water Demand (2050)", f"{c['water_demand'][-1]:.1f} km3", None, None),
            ]
            for col, lbl, val, delta, up in kw:
                delta_html = ""
                if delta:
                    cls = "delta-up" if up else "delta-down"
                    delta_html = f'<div class="{cls}">{delta}</div>'
                col.markdown(f"""
                <div class="metric-strip">
                    <div class="label">{lbl}</div>
                    <div class="val">{val}</div>
                    {delta_html}
                </div>
                """, unsafe_allow_html=True)

            tab_e, tab_em, tab_w = st.tabs(["Energy", "Emissions", "Water"])

            with tab_e:
                ren = [d * r for d, r in zip(c["energy_demand"], c["renewable_share"])]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=yr, y=c["energy_demand"], name="Total Demand",
                    line=dict(color="#009edb", width=2),
                    fill="tozeroy", fillcolor="rgba(0,158,219,0.07)",
                ))
                fig.add_trace(go.Scatter(
                    x=yr, y=ren, name="Renewable",
                    line=dict(color="#40864a", width=1.5, dash="dash"),
                ))
                fig.update_layout(
                    title="Energy Demand (PJ)", xaxis_title="Year",
                    yaxis_title="PJ", template="plotly_white", height=320,
                    margin=dict(t=40, b=40), legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab_em:
                colors = ["#c0392b" if v > 60 else "#da8826" if v > 35 else "#40864a"
                          for v in c["co2_emissions"]]
                fig2 = go.Figure(go.Bar(x=yr, y=c["co2_emissions"], marker_color=colors, name="CO2"))
                fig2.update_layout(
                    title="CO2 Emissions (MtCO2)", xaxis_title="Year",
                    yaxis_title="MtCO2", template="plotly_white", height=320, margin=dict(t=40, b=40),
                )
                st.plotly_chart(fig2, use_container_width=True)

            with tab_w:
                fig3 = px.area(
                    x=yr, y=c["water_demand"], title="Water Demand (km3)",
                    labels={"x": "Year", "y": "km3"}, color_discrete_sequence=["#29b6f6"],
                )
                fig3.update_layout(template="plotly_white", height=320, margin=dict(t=40, b=40))
                st.plotly_chart(fig3, use_container_width=True)

        # OG-Core results block
        if results.get("ogcore"):
            o  = results["ogcore"]
            yr = o["years"]

            st.markdown('<div class="section-title">OG-Core Macroeconomic Results</div>',
                        unsafe_allow_html=True)

            if mt in ("Coupled", "Converging"):
                st.info("Results incorporate CLEWS energy-sector outputs as OG-Core inputs.")

            k1, k2, k3, k4 = st.columns(4)
            for col, lbl, val, delta, up in [
                (k1, "GDP (2050)", f"{o['gdp'][-1]:.1f}",
                 f"{'+' if o['gdp_pct'][-1]>0 else ''}{o['gdp_pct'][-1]:.1f}%", True),
                (k2, "Wage Index (2050)", f"{o['wages'][-1]:.3f}",
                 f"+{o['wages'][-1]-1:.3f}", True),
                (k3, "Interest Rate (2050)", f"{o['interest'][-1]*100:.2f}%", None, None),
                (k4, "Tax Revenue (2050)", f"{o['tax_revenue'][-1]:.1f}", None, None),
            ]:
                delta_html = ""
                if delta:
                    cls = "delta-up" if up else "delta-down"
                    delta_html = f'<div class="{cls}">{delta}</div>'
                col.markdown(f"""
                <div class="metric-strip">
                    <div class="label">{lbl}</div>
                    <div class="val">{val}</div>
                    {delta_html}
                </div>
                """, unsafe_allow_html=True)

            tab_gdp, tab_macro, tab_table = st.tabs(["GDP", "Macro Aggregates", "Data Table"])

            with tab_gdp:
                fig4 = go.Figure()
                for series, lbl, col, dash in [
                    (o["gdp"],         "GDP",        "#1a3a5c", "solid"),
                    (o["consumption"], "Consumption","#009edb",  "dash"),
                    (o["investment"],  "Investment", "#40864a",  "dot"),
                ]:
                    fig4.add_trace(go.Scatter(
                        x=yr, y=series, name=lbl,
                        line=dict(color=col, width=2, dash=dash),
                    ))
                fig4.update_layout(
                    title="GDP & Components (Base = 100)", xaxis_title="Year",
                    yaxis_title="Index", template="plotly_white", height=340,
                    margin=dict(t=40, b=40), legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig4, use_container_width=True)

            with tab_macro:
                wa, wb = st.columns(2)
                with wa:
                    fig5 = px.line(x=yr, y=o["wages"], title="Wage Index",
                                   labels={"x": "Year", "y": "Index"},
                                   color_discrete_sequence=["#da8826"])
                    fig5.update_layout(template="plotly_white", height=280, margin=dict(t=40, b=30))
                    st.plotly_chart(fig5, use_container_width=True)
                with wb:
                    fig6 = px.line(x=yr, y=[r * 100 for r in o["interest"]],
                                   title="Interest Rate (%)",
                                   labels={"x": "Year", "y": "%"},
                                   color_discrete_sequence=["#6a1b9a"])
                    fig6.update_layout(template="plotly_white", height=280, margin=dict(t=40, b=30))
                    st.plotly_chart(fig6, use_container_width=True)

            with tab_table:
                df = pd.DataFrame({
                    "Year":          yr,
                    "GDP":           [f"{v:.2f}" for v in o["gdp"]],
                    "GDP % change":  [f"{v:.2f}%" for v in o["gdp_pct"]],
                    "Wages":         [f"{v:.4f}" for v in o["wages"]],
                    "Interest (%)":  [f"{v*100:.2f}" for v in o["interest"]],
                    "Tax Revenue":   [f"{v:.2f}" for v in o["tax_revenue"]],
                })
                st.dataframe(df, use_container_width=True, height=320)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    file_name=f"{sel}_ogcore.csv",
                    mime="text/csv",
                )


# ── coupled pipeline ─────────────────────────────────────────────────────────

elif page == "Coupled Pipeline":
    st.markdown('<div class="section-title">Coupled & Converging Mode</div>', unsafe_allow_html=True)

    st.markdown("""
    The coupled pipeline is how MUIOGO bridges the CLEWS energy model and the OG-Core
    macroeconomic model. Two modes are supported:

    - **One-way (Coupled):** CLEWS runs first; selected energy outputs are transformed
      into OG-Core inputs via a JSON exchange schema, then OG-Core runs once.
    - **Iterative (Converging):** CLEWS and OG-Core run alternately, with outputs feeding
      back into the next iteration, until model outputs converge below a threshold delta.
    """)

    tab1, tab2 = st.tabs(["One-way Coupled", "Converging Mode"])

    with tab1:
        st.code("""
CLEWS / OSeMOSYS
  inputs : energy demand, land use, water availability, emission limits
  outputs: energy_mix.csv, emissions.csv, capital_cost.csv
       |
       |  data exchange pipeline  (exchange_schema.json)
       v
OG-Core
  inputs : + energy capital cost  --> adjusts firm cost structure
           + renewable share      --> adjusts TFP growth assumption
           + CO2 cost             --> adjusts effective tax burden
  outputs: gdp.csv, wages.csv, interest.csv, tax_revenue.csv
""", language="text")

        with st.expander("Configure exchange pipeline"):
            st.selectbox("CLEWS variable → OG-Core parameter", [
                "capital_cost_energy  →  firm_cost_adjustment",
                "renewable_share      →  tfp_growth_rate",
                "co2_emissions_cost   →  effective_tax_rate",
            ])
            st.slider("Scaling factor", 0.1, 2.0, 1.0, 0.1)
            st.checkbox("Validate exchange schema before run", value=True)

    with tab2:
        st.code("""
Iteration 1 :  CLEWS run  ->  OG-Core run   (delta large)
Iteration 2 :  OG-Core output feeds CLEWS  ->  CLEWS run  ->  OG-Core run
  ...
Iteration N :  delta < epsilon  =>  converged
""", language="text")

        eps      = st.slider("Convergence threshold (epsilon)", 0.0001, 0.01, 0.0005, 0.0001,
                             format="%.4f")
        max_iter = st.slider("Maximum iterations", 3, 20, 10)
        st.info(f"Model will iterate up to **{max_iter}** times or until delta falls below **{eps:.4f}**.")


# ── about ────────────────────────────────────────────────────────────────────

elif page == "About":
    st.markdown('<div class="section-title">About MUIOGO</div>', unsafe_allow_html=True)

    left, right = st.columns([2, 1])

    with left:
        st.markdown("""
        **MUIOGO** — *Modelling User Interface for OG-Core and OSeMOSYS* — is a UN DESA tool
        that makes two widely used open-source policy models accessible to government analysts
        in developing countries.

        | Model | Purpose |
        |-------|---------|
        | **CLEWS / OSeMOSYS** | Energy transition planning, emissions, land and water |
        | **OG-Core** | Fiscal policy, GDP, wages, inequality across generations |

        The frameworks have been deployed in over 20 countries, supporting NDC planning under
        the Paris Agreement, social protection assessments, and pension reform analysis.

        **Deployment context:** 10+ countries by 2030 under a USD 2M UN Peace and Development
        Trust Fund programme.

        ---

        **This prototype** explores whether Streamlit is a suitable UI layer for the
        OG-CLEWS coupled module frontend, as described in the GSoC 2026 project scope.
        It demonstrates scenario management, OG-Core parameter entry (using the actual
        `default_parameters.json` structure), and a coupled CLEWS → OG-Core results view.

        GSoC 2026 Mentors: Alfonso Acosta Gonçalves · Marcelo LaFleur (UN DESA · EAPD)
        """)

    with right:
        st.markdown("""
        **Stack used in this prototype**

        - Python 3.11
        - Streamlit
        - Plotly
        - pandas / numpy

        **Existing MUIOGO stack**

        - Flask (API)
        - Vanilla JS / jQuery
        - SmartAdmin template
        - Wijmo grids
        - Plotly 2.27

        **Links**

        - [MUIOGO repo](https://github.com/EAPD-DRB/MUIOGO)
        - [OG-Core docs](https://pslmodels.github.io/OG-Core)
        - [OSeMOSYS](http://www.osemosys.org)
        """)


# ── footer ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="page-footer">
    MUIOGO · OG-CLEWS Modelling Suite · UN DESA EAPD ·
    <a href="https://github.com/EAPD-DRB/MUIOGO" style="color:#009edb;">GitHub</a>
</div>
""", unsafe_allow_html=True)
