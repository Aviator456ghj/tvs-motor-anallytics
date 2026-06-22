# tvs-motor-anallytics

## Delta Exchange MCP server

This project is configured to use the official [Delta Exchange MCP server](https://github.com/delta-exchange/delta-exchange-mcp)
(`delta-exchange-mcp` on PyPI) via the project-scoped `.mcp.json` in the repo root. It runs locally over stdio
through `uvx delta-exchange-mcp` and exposes:

- **Public market-data tools** (no credentials required): product catalogs, tickers, options chains,
  orderbooks, trades, candles, reference data.
- **Authenticated read-only account tools**: positions, orders, fills, wallet balances, leverage,
  trading stats. The server cannot place, edit, or cancel orders.

### Credentials

`.mcp.json` reads `DELTA_API_KEY` / `DELTA_API_SECRET` / `DELTA_MCP_ENV` from the environment — it never
contains literal secret values, and nothing under `.env*` (see `.gitignore`) is committed.

1. Create an API key at https://delta.exchange/app/account/manageapikeys with **Read Data** permission only.
2. Set `DELTA_API_KEY`, `DELTA_API_SECRET`, and `DELTA_MCP_ENV` (`india_prod` or `india_testnet`) as environment
   variables in your Claude Code environment settings (or a local untracked `.env`, see `.env.example`) —
   never paste real keys into chat or commit them to a file.
3. Restart/reload the MCP session so `.mcp.json`'s `${VAR}` expansion picks up the new values.

If you only need public market data, no credentials are required at all.