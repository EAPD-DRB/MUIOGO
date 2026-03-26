# 🎓 Applications for MUIOGO Are Now Open!

Please complete the following questionnaire so we can keep track of everybody’s application in a structured way:

🗓 **Deadline**: 16 March  
📄 **Apply** [here](https://forms.gle/8Yvw2H6Q7Qw6snSN9)

---
<p align="center"><img src="assets/MUIOGO_Logo.png" width="50%"></p>

<p><img src="assets/UN_Crest.png" width="75" align="left"></p>

**M**odelling **U**ser **I**nterface for **OG**-Core and **O**SeMOSYS

The United Nations Department of Economic and Social Affairs (DESA) has applied open-source modelling tools during the last decade in more than 20 countries —particularly in Small Island Developing States, Land-Locked Countries, and Least Developed Countries— to support policies related to Nationally Determined Contributions (NDCs), climate adaptation, social protection, and fiscal sustainability:
- CLEWS, built on OSeMOSYS, analyzes interactions and trade-offs across land, energy, and water systems under climate scenarios.
- OG-Core is a dynamic overlapping-generations macroeconomic model that evaluates long-term fiscal, demographic, and economic policies.

By linking sectoral resource systems (climate, land, energy, and water) with a dynamic macroeconomic model, the unified framework will allow policymakers to assess both the physical feasibility and economy-wide impacts of climate and development policies in a transparent, reproducible, and low-cost way.

The project will create a standardized interface and shared execution system linking the two models, enabling integrated analyses that are not currently possible. The enhanced OG-CLEWS framework will be deployed in more than 10 countries, supporting evidence-based policymaking and helping countries advance toward their Sustainable Development Goals through 2030.

See the [Project Background & Vision](https://github.com/EAPD-DRB/MUIOGO/wiki/Project-Background-and-Vision) and the programme's [Timeline](https://github.com/EAPD-DRB/MUIOGO/wiki/Timeline) for more information.

MUIOGO is the integration project to bring the purely Python-based OG-Core model into MUIO, the GUI for OSeMOSYS (CLEWS).

For now, the app will run locally on a user's machine. In the future, the app may be hosted on a server for public access, so scalability should remain a design consideration. Today, the initial target is a downloadable app that users can run locally without needing an internet connection.

At the moment, this repository starts from a direct copy baseline of MUIO. The goal of MUIOGO is to evolve that baseline into an integrated OG-CLEWS model that is maintainable and platform-independent.

## Requirements

- Git:
  - Install: [git-scm.com](https://git-scm.com/downloads)
- Python 3.11:
  - macOS (in Terminal): `brew install python@3.11`
  - Windows (in PowerShell or Command Prompt): `winget install -e --id Python.Python.3.11`
  - Installer downloads: [python.org macOS](https://www.python.org/downloads/macos/) / [python.org Windows](https://www.python.org/downloads/windows/)
- GLPK and CBC solvers:
  - Installed automatically by setup scripts (`./scripts/setup.sh` or `scripts\\setup.bat`)

## Installation

### macOS / Linux (in Terminal)

```bash
./scripts/setup.sh
./scripts/start.sh
```

### Windows (in PowerShell or Command Prompt)

```bat
scripts\setup.bat
scripts\start.bat
```

For setup options, use the "--help" flag:
- macOS / Linux: `./scripts/setup.sh --help`
- Windows: `scripts\setup.bat --help`

> **Note:** The setup scripts handle more than Python packages (venv creation,
> solver installation, demo data). Using them is the recommended onboarding path.
>
> Advanced users who want to manage dependencies or packaging manually can use
> the [Advanced Setup and Packaging](#advanced-setup-and-packaging) section
> below.

## Demo Data

The demo dataset (`CLEWs.Demo.zip`) is hosted as a [GitHub release asset](https://github.com/EAPD-DRB/MUIOGO/releases/tag/demo-data) and downloaded automatically during setup when not already cached locally.

- SHA-256: `facf4bda703f67b3c8b8697fea19d7d49be72bc2029fc05a68c61fd12ba7edde`

Setup installs demo data by default. The archive is downloaded once, cached in `assets/demo-data/`, and reused on subsequent runs.

One of the core goals of MUIOGO is to become platform independent so separate platform-specific ports are no longer required.

## Repository Layout

- `API/`: Flask backend and run/data endpoints
- `WebAPP/`: frontend assets served by Flask
- `WebAPP/DataStorage/`: model inputs, case data, and run outputs
- `docs/`: project and contributor documentation

## Contributing

Start with:
- `CONTRIBUTING.md`
- `docs/GSoC-2026.md`
- `docs/ARCHITECTURE.md`
- `docs/DOCS_POLICY.md`

Contribution rule:
- Create (or use) an issue first.
- Work in a feature branch (for example `feature/<issue-number>-short-description`).

Templates:
- `.github/ISSUE_TEMPLATE/`
- `.github/pull_request_template.md`

### Advanced Setup and Packaging

If you need to install Python dependencies without the setup scripts:

```bash
# All platforms — runtime
pip install -r requirements.txt
```

```bash
# Windows packaging dependencies (PyInstaller build only)
pip install -r requirements-build-win.txt
```

## Project Boundaries

This repository is downstream and separately managed from upstream:

- Upstream: `https://github.com/OSeMOSYS/MUIO`
- This repo: `https://github.com/EAPD-DRB/MUIOGO`

Delivery in MUIOGO cannot depend on upstream timelines or release cycles.

## License

Apache License 2.0 (`LICENSE`).
