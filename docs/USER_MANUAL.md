# Build and maintain the user manual

The user-facing source is [source/og-core/index.rst](source/og-core/index.rst).
It uses reStructuredText and Sphinx. The root configuration is
[.readthedocs.yml](../.readthedocs.yml). HTML includes search, a sidebar,
previous/next links and links to edit the source on GitHub.

## Preview locally

From the repository root, with `uv` installed:

```bash
uv run --with-requirements docs/requirementsrtd.txt python -m sphinx -b html -n -W --keep-going docs/source docs/build/html
```

Open `docs/build/html/index.html` in a browser. For search and normal browser
navigation, serve the output locally:

```bash
uv run python -m http.server 8000 --bind 127.0.0.1 --directory docs/build/html
```

Open <http://127.0.0.1:8000/>. Press Ctrl+C to stop the preview server.
The documentation build does not import MUIOGO, install country models or run
simulations. Build packages are listed separately in `requirementsrtd.txt`.

## Publish on GitHub Pages

The public manual is hosted at <https://eapd-drb.github.io/MUIOGO/>.
The `User manual` workflow builds and checks Sphinx, then deploys the HTML
to GitHub Pages. Pushes affecting the documentation on
`main` trigger publication. Pull requests
build an artifact without publishing it. The deployment environment is
`github-pages`.

Only `docs/build/html/` is uploaded. The app, country data and solver
environments are not part of the published site. Build packages are
installed from `docs/requirementsrtd.txt`.

The workflow sets `MUIOGO_DOCS_BRANCH` so the site's GitHub edit links
point to the branch that produced that build.

## Optional: host on Read the Docs

1. Commit and push the reviewed documentation to this repository.
2. In the organisation's Read the Docs account, import `EAPD-DRB/MUIOGO`,
   or use its existing project.
3. Use the repository's `.readthedocs.yml` configuration. If prompted for
   its path, enter `.readthedocs.yml`.
4. Build the chosen branch or tag. Check that the build passes and the
   published site opens at the MUIOGO manual.
5. Confirm that repository webhooks trigger builds after later changes.

See the official [configuration reference](https://docs.readthedocs.com/platform/stable/config-file/v2.html).
No hosted-site URL is assumed in the manual. Hosting requires the project
owner's account access; adding the files does not publish a site.

## Keep the two reading paths aligned

- **Quick Guide:** the shortest complete route from installation to exports.
- **Detailed guide:** the same example, with numbered screens and control tables.
- **Help:** short fixes and definitions for non-specialist readers.

Use the exact interface labels. Keep sentences short. Explain an unfamiliar
term at first use. Add a visible checkpoint after each main action. Keep
implementation notes here, outside the policymaker's workflow.

Both guides include the same installation instructions from
`source/_includes/install-git.rst` and `source/_includes/install-muiogo.rst`.
Edit these shared files when changing commands so the guides stay aligned.
The manual home page and Quick Guide share the complete installation section
from `source/_includes/install-and-open.rst`.

Earlier OSeMOSYS content is retained under `source/legacy-osemosys.rst`.
Its heading underlines were repaired for strict builds; its model guidance
has not been rewritten for the new CLEWs manual.

## Code used for this draft

The draft was checked against MUIOGO commit
`c904aa93739fd92e1ffafce59861081851607554` (8 September 2026).

| Manual page | Main implementation sources |
| --- | --- |
| Installation | `scripts/install.sh`, `scripts/install.ps1`, `scripts/start.sh`, `scripts/start.bat`, `scripts/setup_dev.py`, `API/app.py` |
| Country and navigation | `WebAPP/App/View/ModelPick.html`, `Navbar.html`, `Sidebar.html`, `OGCore.html`; `WebAPP/App/Controller/OGCore.js`; `WebAPP/Classes/OGWorkspace.Class.js`, `MuiogoShell.Class.js`; `API/Classes/OGCore/Installer.py`, `CalibrationCatalog.py`; `API/Classes/Base/Config.py` |
| Cases | `WebAPP/App/View/OGCases.html`, `WebAPP/App/Controller/OGCases.js`, `API/Classes/OGCore/OGCoreCase.py` |
| Parameters | `WebAPP/App/Controller/OGParameters.js`, `OGTableEditor.js`; `WebAPP/App/Model/OGParams.Overlay.js`, `OGParameters.Model.js`; `API/Classes/OGCore/OGSchema.py`; `WebAPP/Classes/NavigationGuard.Class.js` |
| Run | `WebAPP/App/View/OGRuns.html`, `WebAPP/App/Controller/OGRuns.js`, `API/Classes/OGCore/RunJob.py`, `OGRunner.py`, `ogc_worker.py` |
| Results and exports | `WebAPP/App/View/OGResults.html`, `WebAPP/App/Controller/OGResults.js`, `API/Routes/OGCore/OGCoreRunRoute.py`, `API/Classes/OGCore/OGTables.py`, `ogc_worker.py` |

The inspected local OG-PHL package is version `0.1.1`, commit
`c5516563a60075801d79354a4ef9df0e0b7dfd98`. Its
`ogphl/ogphl_default_parameters.json` supplies `cit_rate = [[0.25]]`.
The installed OG-Core parameter definition labels it **Corporate income tax
rate** and says that unspecified years use the last entered value. The example
sets every displayed year to `0.20`, a five-percentage-point cut (a 20%
reduction in the rate). These are model inputs, not claims about
current tax law. Country packages may change independently of MUIOGO.

## Validation and release follow-up

Draft checks on 28 October 2026:

- Strict Sphinx HTML build (`-n -W --keep-going`): passed without warnings.
- Generated documentation links, anchors and local assets: checked.
- `git diff --check`: passed.
- Browser visual check: not completed; the browser preview tools stalled.
- Fresh app installation and OG-PHL simulation: not run.
- The initial draft was checked locally; publication now uses the GitHub Actions
  workflow above. A hosted Read the Docs build has not been run.

The draft is based on code and parameter-file inspection. It does not claim
a successful simulation or include invented result values. The local retained
`Default Baseline` run is failed and contains a `gamma = [0.5]` override;
it is not evidence for the unchanged-default tutorial. It was not reused or
changed. No model or case files were edited for this documentation task.

Before calling the tutorial tested for training:

1. Follow installation on a clean supported computer.
2. Record the MUIOGO, OG-PHL and OG-Core versions.
3. Create a fresh baseline with unchanged country defaults, then the single
   `cit_rate` reform. Verify both reach Completed with Steady state.
4. Check the selected comparison, the one-parameter difference, chart export
   and CSV export. Record run times and any errors.
5. Capture screenshots of the five main screens from that successful exercise.
   Avoid unrelated user cases. Add short captions and alternative text.
6. Ask one non-specialist reader to follow the Quick Guide without coaching.

Current interface limits documented in the manual:

- Results needs a completed baseline and reform; no baseline-only dashboard.
- The active Results controller reads steady-state values. Transition paths can
  be calculated, but this screen does not plot them over time.
- Explore defaults are local to the browser and country.
- Wealth moments uses the baseline only and does not supply survey observations.
- Backend backup and restore routes exist, but current OG-Core screens have no
  corresponding buttons. The manual does not invent them.
- Keep Run open until its whole selection finishes: leaving can stop submission
  of later jobs even though an already submitted job continues.

The draft includes troubleshooting and a short glossary. Suggested next
improvements are real screenshots and the first-user walkthrough above.
