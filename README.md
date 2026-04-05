# SciQLop Plugin Registry

A static plugin registry for [SciQLop](https://github.com/SciQLop/SciQLop). Each plugin is described by a YAML file in `plugins/`. A GitHub Actions workflow merges them into a single `index.json` published on GitHub Pages.

## Adding a plugin

Create a YAML file in `plugins/` and open a pull request. The file name should match your plugin name (e.g. `my-plugin.yaml`).

### Minimal example (pip-installable)

```yaml
name: My Plugin
description: What it does
author: Your Name
license: MIT
tags: [analysis]

versions:
  - version: "0.1.0"
    sciqlop: ">=0.10"
    pip: my-sciqlop-plugin==0.1.0
```

### Wheel from a bundle repo

For plugins built as wheels by a bundle repo's CI:

```yaml
name: CDF Workbench
description: Multi-function CDF file explorer
author: Alexis Jeandet
license: MIT
tags: [cdf, inspector]

versions:
  - version: "0.1.0"
    sciqlop: ">=0.10"
    pip: https://github.com/SciQLop/sciqlop-plugins/releases/download/v0.1.0/sciqlop_cdf_workbench-0.1.0-py3-none-any.whl
```

### Version entries

Each entry in `versions` declares:

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Plugin version (semver) |
| `sciqlop` | yes | Compatible SciQLop version range (PEP 440) |
| `pip` | yes | pip requirement specifier, PyPI package, or direct URL to a wheel |

SciQLop picks the newest version entry compatible with the running SciQLop version.

## Alternative stores

SciQLop can be configured to look at multiple store URLs. Any repo following the same structure (YAML files + CI producing `index.json` on GitHub Pages) works as an alternative store.
