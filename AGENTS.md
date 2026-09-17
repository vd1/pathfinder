# Agent Instructions

This project uses Shipshape, a context-isolated spec-driven workflow for coding agents.

Agent opening this project: ensure Shipshape is installed, then load the `shipshape` skill (`shipshape:shipshape` under the plugin channel) and follow its routing before other work. Decide how to involve the human per your configured preferences.

Tooling values such as stack, directories, and commands live in `RIGGING.md`.

Install with the open skills CLI:

```bash
npx skills add dmytri/shipshape --skill '*'
```
