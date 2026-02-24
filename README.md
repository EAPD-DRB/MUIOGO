# MUIOGO

<img src="assets/UN_Crest.png" width="75" align="left">

**M**odelling **U**ser **I**nterface for **OG**-Core and **O**SeMOSYS

The United Nations Department of Economic and Social Affairs (DESA) has applied open-source modelling tools during the last decade in more than 20 countries —particularly in Small Island Developing States, Land-Locked Countries, and Least Developed Countries— to support policies related to Nationally Determined Contributions (NDCs), climate adaptation, social protection, and fiscal sustainability:
- CLEWS, built on OSeMOSYS, analyzes interactions and trade-offs across land, energy, and water systems under climate scenarios.
- OG-Core is a dynamic overlapping-generations macroeconomic model that evaluates long-term fiscal, demographic, and economic policies.

By linking sectoral resource systems (climate, land, energy, and water) with a dynamic macroeconomic model, the unified framework will allow policymakers to assess both the physical feasibility and economy-wide impacts of climate and development policies in a transparent, reproducible, and low-cost way.

The project will create a standardized interface and shared execution system linking the two models, enabling integrated analyses that are not currently possible. The enhanced OG–CLEWS framework will be deployed in more than 10 countries, supporting evidence-based policymaking and helping countries advance toward their Sustainable Development Goals through 2030.

See the [Project Background & Vision](https://github.com/EAPD-DRB/MUIOGO/wiki/Project-Background-and-Vision)

MUIOGO is the integration project to bring the purely Python-based OG-Core model into MUIO, the GUI for OSeMOSYS (CLEWS).

At the moment, this repository starts from a direct copy baseline of MUIO. The
goal of MUIOGO is to evolve that baseline into an integrated OG–CLEWS model that is maintainable and
platform-independent.

If you are new to this repo, start with the current installation notes below.

## Resources

Beyond the purely technical aspects, it is important to get a basic understanding of what both models do:
- MUIO: https://muio-modelling-user-interface-for-osemosys.readthedocs.io/
- CLEWS/OSeMOSYS: https://osemosys.readthedocs.io/
- OG-Core: https://pslmodels.github.io/OG-Core/content/theory/intro.html

Free online trainings are available here:
- CLEWS: https://capacity.desa.un.org/article/introduction-clews
- OG-Core: https://capacity.desa.un.org/article/mastering-og-core-model-theory-technical-applications-and-policy-use-cases

## Current installation status

### Windows

MUIOGO is currently distributed primarily as a Windows desktop installer.

1. Download the latest `.exe` installer from [here](https://github.com/EAPD-DRB/MUIOGO/releases)
2. Move the `.exe` file to a folder where you have administrator permissions.
3. Right-click `MUIOGO.exe` and select **Run as administrator**.
4. Wait for installation to complete.
5. Open the app from the Start Menu if it does not open automatically.

### macOS

Use [MUIO-Mac](https://github.com/SeaCelo/MUIO-Mac) as the current macOS-capable path.

### Platform-independence goal

One of the core goals of MUIOGO is to become platform independent so separate
platform-specific ports are no longer required.

## What is in this repository

- `API/`: Flask backend and run/data endpoints
- `WebAPP/`: frontend assets served by Flask
- `WebAPP/DataStorage/`: model inputs, case data, and run outputs
- `docs/`: user and model documentation sources

## For new contributors

Start here:

- `CONTRIBUTING.md`
- `docs/GSoC-2026.md`
- `docs/ARCHITECTURE.md`
- `docs/DOCS_POLICY.md`

Issue and PR templates:

- `.github/ISSUE_TEMPLATE/`
- `.github/pull_request_template.md`

Contribution rule:

- Create (or use) an issue first.
- Implement in a feature branch (for example:
  `feature/<issue-number>-short-description`).

## Important project boundaries

This repository is downstream and separately managed from upstream `OSeMOSYS/MUIO`.

- Upstream: `https://github.com/OSeMOSYS/MUIO`
- This repo: `https://github.com/EAPD-DRB/MUIOGO`

Contributions upstream are welcome, but delivery in MUIOGO **cannot** depend on
upstream timelines or releases.

`MUIO-Mac` is a separate macOS port effort and can continue in parallel, but
MUIOGO **cannot** depend on it for delivery decisions.

## Wiki

The wiki is currently used only for high-level background context:

- [Project Background and Vision](https://github.com/EAPD-DRB/MUIOGO/wiki/Project-Background-and-Vision)

Setup, architecture, contribution process, and governance docs are maintained in
this repository.

## License

Apache License 2.0 (`LICENSE`).
