# OG-CLEWS UI Prototype

A Streamlit-based prototype exploring a Python-native frontend for the
MUIOGO OG-CLEWS integrated modelling suite.

This prototype covers the four execution modes described in the project scope:

| Mode | Description |
|------|-------------|
| **CLEWS** | Climate, Land, Energy and Water systems (OSeMOSYS) |
| **OG-Core** | Overlapping-Generations macroeconomic model |
| **Coupled** | One-way CLEWS → OG-Core data exchange pipeline |
| **Converging** | Iterative CLEWS ↔ OG-Core feedback until convergence |

## Running locally

```bash
cd ogcore_ui_prototype
pip install -r requirements.txt
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

## Notes

- OG-Core parameter inputs are based on the actual structure of
  [`default_parameters.json`](https://github.com/PSLmodels/OG-Core/blob/master/ogcore/default_parameters.json).
- Model runs in this prototype use simulated outputs. Connecting
  `ogcore.runner` and the OSeMOSYS solver is the next integration step.
- The UI colour scheme is intentionally aligned with the existing MUIOGO
  SmartAdmin palette (`#1a3a5c`, `#009edb`, `#3a3f51`).

## Context

The existing MUIOGO frontend is a jQuery/SmartAdmin SPA. This prototype
explores whether Streamlit is a practical UI layer for the new OG-Core
and coupled modules, given that the GSoC project scope lists Streamlit,
Dash and Gradio as preferred frameworks for the Contributor 2 role.
