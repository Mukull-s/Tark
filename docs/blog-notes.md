# Tark — Judge-Facing Notes (Blog Fragments)

Short, copy-ready paragraphs for the technical blog / judge Q&A. Each states a
capability honestly and names its limitation.

## 1. Custom MCP server vs. the official `tigergraph-mcp`

Tark ships its **own** MCP server (`src/mcp/server.py`) rather than wrapping the
official `tigergraph-mcp` package. The reason is safety, not NIH: the official server
exposes 69 general-purpose TigerGraph tools including raw `gsql`, `run_query`, and
destructive graph operations. Tark's threat model requires that an autonomous agent can
**only** invoke a small, schema-validated set of fraud-investigation evidence tools, with
every execution routed through the authoritative `EvidenceToolDispatcher` (no arbitrary
GSQL, no shell). To stay interoperable we implement the *same* contract the official
server speaks: JSON-RPC 2.0 with `initialize` / `tools/list` / `tools/call`, per-tool
JSON-Schema `inputSchema`, MCP `annotations` (`readOnlyHint`, `destructiveHint`,
`idempotentHint`, `openWorldHint`), protocol-version negotiation, the
`tigergraph__`-prefixed tool naming convention for graph-native tools, and the structured
`{success, operation, summary, data, suggestions, metadata}` response envelope. What we
did **not** do — and deliberately chose not to do pre-deadline — is swap in the upstream
package, because doing so would widen the agent's authority surface to raw GSQL
execution and break the deterministic-execution guarantee that the whole design rests on.
Adopting the official transport (stdio / streamable-HTTP) is a packaging change on top of
a contract that already matches; the authorization boundary is the part worth keeping.

## 2. Vector storage / GraphRAG — local deterministic index, no live vector claim

We probed the live benchmark instance before claiming anything. TigerGraph release
4.2.5 reports the `gsql-graph-algorithms` and `gle` components, but **no GDS algorithm
query is resolvable on our graph** (`INSTALL QUERY tg_wcc` fails: *"the specified query
tg_wcc could not be resolved within the provided graph"*), and there is **no vector
(`Document`) vertex type**. So Tark does **not** claim live native GDS or TigerGraph
vector search. Instead we implement a real, auditable **vector-storage + retrieval
contract locally** (`src/knowledge/vector_index.py`): every policy, typology, and statute
chunk is embedded into a fixed-dimension feature-hashing vector and retrieved by cosine
similarity to a case query, with an explicit `retrieval_path` (e.g.
`VectorIndex -> CosineSimilarity -> KNOW-POLICY-R5`) rendered in SAR §4. The same vectors
are portable to TigerGraph vector attributes the moment a vector index is provisioned —
the honest statement is "vector retrieval implemented, live TigerGraph vector search not
claimed." The capability probe is reproducible via `bench/probe_gds_vector.py` and its
output is recorded in `analysis/gds_vector_probe.json`.

## 3. Specificity / FPR — operational FPR is primary

We report **operational FPR as the primary specificity metric**: 0% of historically
cleared legitimate alerts received a customer-facing punitive action (`BLOCK_CARD` /
`DECLINE_TRANSACTION`). The higher **classification FPR (~0.68)** is disclosed as a
secondary, stricter diagnostic: it reflects a deliberately fraud-biased posterior on
sparse historical evidence, and operational safety is provided not by the raw posterior
threshold but by the **decision gate and corroboration contract**, which withhold punitive
action until evidence is corroborated across independent dimensions. Reporting both, with
operational FPR leading, is the honest framing: the posterior is conservative, and the
gate is what converts that conservatism into zero false punitive actions.

## 4. Coverage denominator — trigger-specific, not a fixed ratio

Evidence coverage uses a **per-trigger applicable checklist** as its denominator
(`src/belief/engine.py`): `risk_score` → 5 applicable dimensions, `customer_report` → 4
(dispute already established), `analyst_request` → 3 (no model score or dispute). Ruled-out
(`NO_MATCH`) dimensions are tracked separately as `probed_coverage` and never count toward
coverage or unlock the gate. This is why the benchmark exhibits genuine coverage variance
(0.20 / 0.40 / 0.50 / 0.67) rather than a single saturating value.
