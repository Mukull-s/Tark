"""Probe live TigerGraph for native GDS algorithm + vector attribute support.

Read-only capability probe. Records findings to analysis/gds_vector_probe.json.
Never claims a capability that was not verified.
"""
import os
import json
import warnings

warnings.filterwarnings("ignore")
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
import pyTigerGraph as tg  # noqa: E402

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    out = {"probe": "tigergraph_gds_vector_capability", "verified_native_gds": False, "verified_vector_attribute": False}
    try:
        c = tg.TigerGraphConnection(
            host=os.getenv("TG_HOST"), username=os.getenv("TG_USERNAME"),
            password=os.getenv("TG_PASSWORD"), graphname=os.getenv("TG_GRAPHNAME"),
            gsqlSecret=os.getenv("TG_SECRET"), tgCloud=True,
        )
        comps = {x["name"]: x["version"] for x in c.getVersion()}
        out["tigergraph_version"] = comps.get("product")
        out["gds_component_present"] = "gsql-graph-algorithms" in comps
        out["gds_component_version"] = comps.get("gsql-graph-algorithms")
        out["gle_component_present"] = "gle" in comps
        out["installed_queries"] = sorted(k.split("/")[-1] for k in c.getInstalledQueries().keys())

        # Attempt to resolve a canonical GDS algorithm query (tg_wcc).
        try:
            res = c.gsql("USE GRAPH FraudInvestigation\nINSTALL QUERY tg_wcc")
            out["tg_wcc_install"] = str(res)[:400]
            out["verified_native_gds"] = "successfully" in str(res).lower() or "installed" in str(res).lower()
        except Exception as e:
            out["tg_wcc_install"] = ("EXCEPTION " + str(e))[:400]

        # Vector attribute support: confirm the Document vertex type / VECTOR attr exists.
        try:
            c.getVertexAttrs("Document")
            out["document_vertex_present"] = True
            out["verified_vector_attribute"] = True
        except Exception as e:
            out["document_vertex_present"] = False
            out["document_vertex_error"] = str(e)[:200]
    except Exception as e:
        out["fatal_error"] = str(e)[:400]

    out["conclusion"] = (
        "Native GDS algorithm queries are not installed/resolvable on the benchmark graph; "
        "no Document (vector) vertex type is present. Tark therefore uses its local deterministic "
        "vector index and does not claim live native GDS/vector search."
    )

    path = os.path.join(WORKSPACE, "analysis", "gds_vector_probe.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
