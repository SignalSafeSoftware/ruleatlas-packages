# @ruleatlas/discovery

Reusable React components for Discovery workspace surfaces: directory explorer, line-count-by-file-type table, and file types table.

Components are **presentational** — they receive data and callbacks via props. They do not fetch from RuleAtlas APIs or depend on React Router.

## Install (monorepo workspace)

```bash
yarn install
```

## Development

```bash
yarn workspace @ruleatlas/discovery typecheck
yarn workspace @ruleatlas/discovery test
yarn workspace @ruleatlas/discovery build
```

See `docs/architecture/discovery-package-extraction.md`.
