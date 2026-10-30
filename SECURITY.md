# Security Policy

## Supported versions

Security fixes are applied to the active default branch (`main`).

## Case archive imports

Case backups must contain one case folder with `genData.json` directly inside it.
Both `<case>/...` and legacy `WebAPP/DataStorage/<case>/...` layouts are supported.
The importer checks every entry before extraction and rejects entries outside
that case, unsafe paths, duplicate file destinations, and archived symlinks.
All upload endpoints and country-model installations use the same importer.

Operator-created case symlinks under DataStorage remain supported, including
links into external country repositories. Their resolved case directory is the
containment boundary; importing a backup does not overwrite an existing case.

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities.

Report privately to project maintainers with:

- affected component/file,
- reproduction steps or proof of concept,
- impact assessment,
- any suggested remediation.

Maintainers will acknowledge receipt and coordinate next steps.

