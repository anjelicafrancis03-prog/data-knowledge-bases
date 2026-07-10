from __future__ import annotations

import json
import mimetypes
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(r"C:\RAG\corpora\memory-carry\graph\memory-carry-graph.sqlite")
REPORT_PATH = Path(
    r"C:\RAG\corpora\memory-carry\graph\dynamic-browser-closeout-20260609.md"
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8768
MAX_LIMIT = 100


def json_default(value):
    if isinstance(value, Path):
        return str(value)
    return value


def open_db() -> sqlite3.Connection:
    uri = f"file:{quote(str(DB_PATH), safe=':/\\\\')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def row_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def get_int(params: dict[str, list[str]], name: str, default: int, min_value: int, max_value: int) -> int:
    raw = params.get(name, [str(default)])[0]
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(min_value, min(max_value, value))


def get_text(params: dict[str, list[str]], name: str, default: str = "") -> str:
    return (params.get(name, [default])[0] or "").strip()


def parse_concepts_json(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def normalize_concept_token(token: str | None) -> str:
    if not token:
        return ""
    return token.replace("concept_", "").strip()


def where_text(filters: list[str], params: list, columns: list[str], query: str) -> None:
    if not query:
        return
    like = f"%{query}%"
    filters.append("(" + " OR ".join([f"{col} LIKE ?" for col in columns]) + ")")
    params.extend([like] * len(columns))


def where_value(filters: list[str], params: list, column: str, value: str) -> None:
    if value and value != "all":
        filters.append(f"{column} = ?")
        params.append(value)


def make_where(filters: list[str]) -> str:
    return " WHERE " + " AND ".join(filters) if filters else ""


def query_table(
    conn: sqlite3.Connection,
    *,
    select_sql: str,
    from_sql: str,
    filters: list[str],
    params: list,
    order_sql: str,
    limit: int,
    offset: int,
) -> dict:
    where = make_where(filters)
    count_sql = f"SELECT COUNT(*) FROM {from_sql}{where}"
    total = int(conn.execute(count_sql, params).fetchone()[0])
    sql = f"{select_sql} FROM {from_sql}{where} {order_sql} LIMIT ? OFFSET ?"
    rows = [dict(row) for row in conn.execute(sql, [*params, limit, offset])]
    return {"total": total, "items": rows, "limit": limit, "offset": offset}


def api_stats(conn: sqlite3.Connection, params: dict[str, list[str]] | None = None) -> dict:
    fk_rows = [dict(row) for row in conn.execute("PRAGMA foreign_key_check")]
    return {
        "db_path": str(DB_PATH),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "documents": row_count(conn, "documents"),
        "deep_read_docs": row_count(conn, "deep_read_docs"),
        "deep_read_passages": row_count(conn, "deep_read_passages_v2"),
        "deep_read_claims": row_count(conn, "passage_claim_candidates_v2"),
        "aggregate_passages": row_count(conn, "aggregate_passages_v2"),
        "aggregate_claims": row_count(conn, "aggregate_claim_candidates_v2"),
        "relation_candidates": row_count(conn, "graph_relation_candidates_v2"),
        "relation_evidence": row_count(conn, "graph_relation_candidate_evidence_v2"),
        "formal_relations": row_count(conn, "relations"),
        "multihop_staging": row_count(conn, "multihop_candidate_staging_v2"),
        "final_insert_proposals": row_count(conn, "final_insert_proposals_v2"),
        "foreign_key_check_rows": len(fk_rows),
        "read_only": True,
    }


def api_facets(conn: sqlite3.Connection, params: dict[str, list[str]] | None = None) -> dict:
    years = [
        row["year"]
        for row in conn.execute(
            """
            SELECT DISTINCT COALESCE(NULLIF(year, ''), 'unknown') AS year
            FROM documents
            ORDER BY year
            """
        )
        if row["year"]
    ]
    deep_concepts = [
        dict(row)
        for row in conn.execute(
            """
            SELECT concept_id, concept_label, COUNT(*) AS count
            FROM deep_read_passage_concepts_v2
            GROUP BY concept_id, concept_label
            ORDER BY count DESC, concept_label
            LIMIT 100
            """
        )
    ]
    aggregate_tokens = [
        dict(row)
        for row in conn.execute(
            """
            SELECT token AS concept_id, token AS concept_label, COUNT(*) AS count
            FROM (
              SELECT value AS token
              FROM aggregate_passages_v2,
                   json_each('["' || replace(trim(concept_tokens), ' ', '","') || '"]')
              WHERE trim(concept_tokens) <> ''
            )
            GROUP BY token
            ORDER BY count DESC, token
            LIMIT 100
            """
        )
    ]
    return {"years": years, "deep_concepts": deep_concepts, "aggregate_tokens": aggregate_tokens}


def api_documents(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    year = get_text(params, "year", "all")
    filters: list[str] = []
    values: list = []
    where_text(filters, values, ["source_title", "doc_id", "markdown_path", "graph_status"], query)
    if year != "all":
        filters.append("COALESCE(NULLIF(year, ''), 'unknown') = ?")
        values.append(year)
    return query_table(
        conn,
        select_sql="""
        SELECT doc_id, source_title, date, COALESCE(NULLIF(year, ''), 'unknown') AS year,
               markdown_path, text_quality, graph_status
        """,
        from_sql="documents",
        filters=filters,
        params=values,
        order_sql="ORDER BY date DESC, source_title",
        limit=limit,
        offset=offset,
    )


def api_deep_passages(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    year = get_text(params, "year", "all")
    concept = get_text(params, "concept", "all")
    filters: list[str] = []
    values: list = []
    where_text(filters, values, ["p.source_title", "p.doc_id", "p.passage_text"], query)
    if year != "all":
        filters.append("COALESCE(NULLIF(p.year, ''), 'unknown') = ?")
        values.append(year)
    if concept != "all":
        filters.append(
            """
            EXISTS (
              SELECT 1 FROM deep_read_passage_concepts_v2 pc
              WHERE pc.passage_id = p.passage_id
                AND (pc.concept_id = ? OR pc.concept_label = ?)
            )
            """
        )
        values.extend([concept, concept])
    result = query_table(
        conn,
        select_sql="""
        SELECT p.passage_id, p.doc_id, p.source_title, p.date,
               COALESCE(NULLIF(p.year, ''), 'unknown') AS year,
               p.passage_index, p.char_count, p.claim_score, p.concept_count,
               p.review_status, substr(p.passage_text, 1, 1200) AS excerpt,
               (
                 SELECT json_group_array(json_object(
                   'concept_id', pc.concept_id,
                   'concept_label', pc.concept_label,
                   'score', pc.score,
                   'top_aliases', pc.top_aliases_json
                 ))
                 FROM deep_read_passage_concepts_v2 pc
                 WHERE pc.passage_id = p.passage_id
               ) AS concepts_json
        """,
        from_sql="deep_read_passages_v2 p",
        filters=filters,
        params=values,
        order_sql="ORDER BY p.claim_score DESC, p.concept_count DESC, p.date DESC, p.passage_index",
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        item["concepts"] = parse_concepts_json(item.pop("concepts_json", None))
    return result


def api_deep_claims(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    year = get_text(params, "year", "all")
    concept = get_text(params, "concept", "all")
    filters: list[str] = []
    values: list = []
    where_text(filters, values, ["source_title", "doc_id", "evidence_excerpt", "concepts_json"], query)
    if year != "all":
        filters.append("COALESCE(NULLIF(year, ''), 'unknown') = ?")
        values.append(year)
    if concept != "all":
        filters.append("concepts_json LIKE ?")
        values.append(f"%{concept}%")
    result = query_table(
        conn,
        select_sql="""
        SELECT candidate_id, passage_id, doc_id, source_title, date,
               COALESCE(NULLIF(year, ''), 'unknown') AS year,
               passage_index, claim_score, concept_count, candidate_score,
               concepts_json, substr(evidence_excerpt, 1, 1200) AS excerpt, review_status
        """,
        from_sql="passage_claim_candidates_v2",
        filters=filters,
        params=values,
        order_sql="ORDER BY candidate_score DESC, date DESC, passage_index",
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        item["concepts"] = parse_concepts_json(item.pop("concepts_json", None))
    return result


def api_aggregate_passages(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    concept = get_text(params, "concept", "all")
    filters: list[str] = []
    values: list = []
    where_text(filters, values, ["source_doc_id", "chunk_doc_id", "passage_text", "concept_tokens"], query)
    if concept != "all":
        token = concept if concept.startswith("concept_") else f"concept_{concept}"
        filters.append("concept_tokens LIKE ?")
        values.append(f"%{token}%")
    result = query_table(
        conn,
        select_sql="""
        SELECT passage_id, source_doc_id, chunk_doc_id, chunk_index, passage_index,
               char_count, claim_score, concept_count, concept_tokens,
               substr(passage_text, 1, 1200) AS excerpt, review_status
        """,
        from_sql="aggregate_passages_v2",
        filters=filters,
        params=values,
        order_sql="ORDER BY claim_score DESC, concept_count DESC, chunk_index, passage_index",
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        tokens = [token for token in (item.get("concept_tokens") or "").split() if token]
        item["concepts"] = [
            {"concept_id": normalize_concept_token(token), "concept_label": token, "score": ""}
            for token in tokens
        ]
        item["source_title"] = "记忆承载 aggregate"
    return result


def api_aggregate_claims(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    concept = get_text(params, "concept", "all")
    filters: list[str] = []
    values: list = []
    where_text(filters, values, ["source_doc_id", "chunk_doc_id", "evidence_excerpt", "concepts_json"], query)
    if concept != "all":
        token = concept if concept.startswith("concept_") else f"concept_{concept}"
        filters.append("(concepts_json LIKE ? OR concepts_json LIKE ?)")
        values.extend([f"%{concept}%", f"%{token}%"])
    result = query_table(
        conn,
        select_sql="""
        SELECT candidate_id, passage_id, source_doc_id, chunk_doc_id, chunk_index,
               passage_index, candidate_score, concepts_json,
               substr(evidence_excerpt, 1, 1200) AS excerpt, review_status
        """,
        from_sql="aggregate_claim_candidates_v2",
        filters=filters,
        params=values,
        order_sql="ORDER BY candidate_score DESC, chunk_index, passage_index",
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        item["concepts"] = parse_concepts_json(item.pop("concepts_json", None))
        item["source_title"] = "记忆承载 aggregate"
    return result


def api_relation_candidates(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    concept = get_text(params, "concept", "all")
    bucket = get_text(params, "bucket", "all")
    filters: list[str] = []
    values: list = []
    where_text(
        filters,
        values,
        ["concept_a", "concept_b", "relation_label", "relation_candidate_id", "confidence_bucket"],
        query,
    )
    if concept != "all":
        filters.append("(concept_a = ? OR concept_b = ?)")
        values.extend([concept, concept])
    where_value(filters, values, "confidence_bucket", bucket)
    result = query_table(
        conn,
        select_sql="""
        SELECT relation_candidate_id, concept_a, concept_b, relation_label,
               support_passage_count, support_doc_count, max_candidate_score,
               avg_candidate_score, confidence_bucket, review_status
        """,
        from_sql="graph_relation_candidates_v2",
        filters=filters,
        params=values,
        order_sql="""
        ORDER BY
          CASE confidence_bucket
            WHEN 'strong_review_candidate' THEN 1
            WHEN 'medium_review_candidate' THEN 2
            ELSE 3
          END,
          support_doc_count DESC,
          support_passage_count DESC,
          max_candidate_score DESC
        """,
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        item["top_evidence"] = [
            dict(row)
            for row in conn.execute(
                """
                SELECT passage_id, doc_id, source_title, date, passage_index,
                       candidate_score, substr(evidence_excerpt, 1, 700) AS excerpt
                FROM graph_relation_candidate_evidence_v2
                WHERE relation_candidate_id = ?
                ORDER BY candidate_score DESC, date DESC
                LIMIT 5
                """,
                (item["relation_candidate_id"],),
            )
        ]
    return result


def api_relation_evidence(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    relation_id = get_text(params, "relation_id")
    filters: list[str] = []
    values: list = []
    where_text(filters, values, ["source_title", "doc_id", "evidence_excerpt", "relation_candidate_id"], query)
    if relation_id:
        filters.append("relation_candidate_id = ?")
        values.append(relation_id)
    return query_table(
        conn,
        select_sql="""
        SELECT evidence_id, relation_candidate_id, passage_id, doc_id, source_title,
               date, passage_index, candidate_score,
               substr(evidence_excerpt, 1, 1200) AS excerpt
        """,
        from_sql="graph_relation_candidate_evidence_v2",
        filters=filters,
        params=values,
        order_sql="ORDER BY candidate_score DESC, date DESC, relation_candidate_id",
        limit=limit,
        offset=offset,
    )


def api_multihop(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    filters: list[str] = []
    values: list = []
    where_text(
        filters,
        values,
        ["staging_id", "source_ref_id", "question_id", "candidate_type", "concept_path_json", "rationale"],
        query,
    )
    result = query_table(
        conn,
        select_sql="""
        SELECT staging_id, source_ref_id, question_id, candidate_type,
               concept_path_json, relation_ids_json, hop_count, promotion_status,
               confidence, evidence_doc_count, evidence_row_count, max_doc_share,
               rationale, required_next_step
        """,
        from_sql="multihop_candidate_staging_v2",
        filters=filters,
        params=values,
        order_sql="ORDER BY question_id, source_ref_id",
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        item["concept_path"] = parse_concepts_json(item.pop("concept_path_json", None))
        item["relation_ids"] = parse_concepts_json(item.pop("relation_ids_json", None))
    return result


def api_final_proposals(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 25, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    filters: list[str] = []
    values: list = []
    where_text(
        filters,
        values,
        [
            "final_proposal_id",
            "staging_id",
            "source_ref_id",
            "relation_text",
            "policy_decision",
            "policy_rationale",
        ],
        query,
    )
    return query_table(
        conn,
        select_sql="""
        SELECT final_proposal_id, staging_id, source_ref_id, proposed_operation,
               subject_entity_id, predicate, object_entity_id, relation_text,
               proposed_confidence, proposed_review_status, duplicate_relation_id,
               policy_decision, policy_confidence, policy_rationale,
               evidence_doc_count, evidence_row_count, required_user_or_review_action
        """,
        from_sql="final_insert_proposals_v2",
        filters=filters,
        params=values,
        order_sql="ORDER BY final_proposal_id",
        limit=limit,
        offset=offset,
    )


def api_graph(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    limit = get_int(params, "limit", 104, 1, 300)
    min_docs = get_int(params, "min_docs", 1, 0, 10_000)
    bucket = get_text(params, "bucket", "all")
    query = get_text(params, "q")
    filters: list[str] = ["support_doc_count >= ?"]
    values: list = [min_docs]
    if bucket != "all":
        filters.append("confidence_bucket = ?")
        values.append(bucket)
    where_text(
        filters,
        values,
        ["concept_a", "concept_b", "relation_label", "relation_candidate_id", "confidence_bucket"],
        query,
    )
    edge_rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT relation_candidate_id, concept_a, concept_b, relation_label,
                   support_passage_count, support_doc_count, max_candidate_score,
                   avg_candidate_score, confidence_bucket, review_status
            FROM graph_relation_candidates_v2
            {make_where(filters)}
            ORDER BY
              CASE confidence_bucket
                WHEN 'strong_review_candidate' THEN 1
                WHEN 'medium_review_candidate' THEN 2
                WHEN 'ocr_review_candidate' THEN 3
                WHEN 'edge_weak_review_candidate' THEN 4
                ELSE 5
              END,
              support_doc_count DESC,
              support_passage_count DESC,
              max_candidate_score DESC
            LIMIT ?
            """,
            [*values, limit],
        )
    ]
    nodes: dict[str, dict] = {}
    for edge in edge_rows:
        for key in ("concept_a", "concept_b"):
            concept = edge[key]
            node = nodes.setdefault(
                concept,
                {
                    "id": concept,
                    "label": concept,
                    "weight": 0,
                    "relation_count": 0,
                    "support_docs": 0,
                    "max_score": 0,
                    "bucket_counts": {},
                },
            )
            node["weight"] += edge["support_doc_count"]
            node["relation_count"] += 1
            node["support_docs"] += edge["support_doc_count"]
            node["max_score"] = max(node["max_score"], edge["max_candidate_score"])
            node["bucket_counts"][edge["confidence_bucket"]] = (
                node["bucket_counts"].get(edge["confidence_bucket"], 0) + 1
            )
        edge["top_evidence"] = [
            dict(row)
            for row in conn.execute(
                """
                SELECT passage_id, doc_id, source_title, date, passage_index,
                       candidate_score, substr(evidence_excerpt, 1, 520) AS excerpt
                FROM graph_relation_candidate_evidence_v2
                WHERE relation_candidate_id = ?
                ORDER BY candidate_score DESC, date DESC
                LIMIT 3
                """,
                (edge["relation_candidate_id"],),
            )
        ]
    bucket_counts = [
        dict(row)
        for row in conn.execute(
            """
            SELECT confidence_bucket, COUNT(*) AS count
            FROM graph_relation_candidates_v2
            GROUP BY confidence_bucket
            ORDER BY count DESC, confidence_bucket
            """
        )
    ]
    return {
        "nodes": sorted(nodes.values(), key=lambda item: (-item["weight"], item["label"])),
        "edges": edge_rows,
        "bucket_counts": bucket_counts,
        "filters": {"limit": limit, "min_docs": min_docs, "bucket": bucket, "q": query},
        "stats": api_stats(conn),
    }


def api_graph_insights(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    run_id = get_text(params, "run_id", "memory-carry-graph-insights-v2-20260609")
    limit = get_int(params, "limit", 50, 1, MAX_LIMIT)
    query = get_text(params, "q")
    priority = get_text(params, "priority", "all")
    node_filters: list[str] = ["run_id = ?"]
    node_params: list = [run_id]
    pair_filters: list[str] = ["run_id = ?"]
    pair_params: list = [run_id]
    community_filters: list[str] = ["run_id = ?"]
    community_params: list = [run_id]
    if query:
        where_text(node_filters, node_params, ["concept", "review_note", "top_neighbors_json"], query)
        where_text(
            pair_filters,
            pair_params,
            ["concept_a", "concept_b", "relation_candidate_id", "relation_label", "review_note"],
            query,
        )
        where_text(community_filters, community_params, ["concepts_json", "review_note", "threshold_name"], query)
    if priority != "all":
        pair_filters.append("review_priority = ?")
        pair_params.append(priority)
    node_rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT node_id, concept, degree, weighted_degree, relation_count,
                   strong_edge_count, medium_edge_count, ocr_edge_count,
                   edge_weak_count, weak_edge_count, max_candidate_score,
                   avg_candidate_score, top_neighbors_json, review_note
            FROM graph_insight_node_metrics_v2
            {make_where(node_filters)}
            ORDER BY weighted_degree DESC, relation_count DESC, concept
            LIMIT ?
            """,
            [*node_params, limit],
        )
    ]
    for row in node_rows:
        row["top_neighbors"] = parse_concepts_json(row.pop("top_neighbors_json", None))
    pair_rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT pair_id, concept_a, concept_b, relation_candidate_id, relation_label,
                   support_doc_count, support_passage_count, max_candidate_score,
                   avg_candidate_score, confidence_bucket, evidence_count,
                   top_evidence_json, review_priority, review_note
            FROM graph_insight_pair_summary_v2
            {make_where(pair_filters)}
            ORDER BY review_priority, support_doc_count DESC, support_passage_count DESC
            LIMIT ?
            """,
            [*pair_params, limit],
        )
    ]
    for row in pair_rows:
        row["top_evidence"] = parse_concepts_json(row.pop("top_evidence_json", None))
    bucket_rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT confidence_bucket, relation_count, total_support_docs,
                   total_support_passages, avg_support_docs, max_support_docs,
                   review_note
            FROM graph_insight_bucket_summary_v2
            WHERE run_id = ?
            ORDER BY relation_count DESC, confidence_bucket
            """,
            (run_id,),
        )
    ]
    community_rows = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT community_id, threshold_name, min_support_docs, node_count,
                   edge_count, concepts_json, strongest_pair_id,
                   total_support_docs, review_note
            FROM graph_insight_communities_v2
            {make_where(community_filters)}
            ORDER BY min_support_docs DESC, node_count DESC, edge_count DESC
            LIMIT ?
            """,
            [*community_params, limit],
        )
    ]
    for row in community_rows:
        row["concepts"] = parse_concepts_json(row.pop("concepts_json", None))
    run = conn.execute(
        """
        SELECT run_id, source_relation_count, source_evidence_count, status,
               started_at, finished_at, report_path
        FROM graph_insight_runs_v2
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    return {
        "run": dict(run) if run else None,
        "nodes": node_rows,
        "pairs": pair_rows,
        "buckets": bucket_rows,
        "communities": community_rows,
        "filters": {"run_id": run_id, "limit": limit, "q": query, "priority": priority},
        "stats": api_stats(conn),
    }


def api_pair_review_packets(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    run_id = get_text(params, "run_id", "memory-carry-graph-pair-review-packets-v2-20260609")
    limit = get_int(params, "limit", 50, 1, MAX_LIMIT)
    offset = get_int(params, "offset", 0, 0, 1_000_000)
    query = get_text(params, "q")
    tier = get_text(params, "tier", "all")
    action = get_text(params, "action", "all")
    filters: list[str] = ["run_id = ?"]
    values: list = [run_id]
    where_text(
        filters,
        values,
        [
            "packet_id",
            "pair_id",
            "relation_candidate_id",
            "concept_a",
            "concept_b",
            "relation_label",
            "review_priority",
            "packet_tier",
            "recommended_action",
            "risk_flags_json",
            "reviewer_prompt",
            "caveat",
        ],
        query,
    )
    where_value(filters, values, "packet_tier", tier)
    where_value(filters, values, "recommended_action", action)
    result = query_table(
        conn,
        select_sql="""
        SELECT packet_id, pair_id, relation_candidate_id, concept_a, concept_b,
               relation_label, support_doc_count, support_passage_count,
               max_candidate_score, avg_candidate_score, confidence_bucket,
               review_priority, packet_tier, recommended_action,
               risk_flags_json, source_diversity_json, temporal_span_json,
               sample_titles_json, reviewer_prompt, caveat
        """,
        from_sql="graph_pair_review_packets_v2",
        filters=filters,
        params=values,
        order_sql="""
        ORDER BY
          CASE packet_tier
            WHEN 'tier_1_promote_review_packet' THEN 1
            WHEN 'tier_2_semantic_review_packet' THEN 2
            WHEN 'tier_3_navigation_packet' THEN 3
            WHEN 'tier_3_general_review_packet' THEN 4
            WHEN 'tier_4_ocr_review_packet' THEN 5
            ELSE 6 END,
          support_doc_count DESC, support_passage_count DESC
        """,
        limit=limit,
        offset=offset,
    )
    for item in result["items"]:
        item["risk_flags"] = parse_concepts_json(item.pop("risk_flags_json", None))
        item["source_diversity"] = json.loads(item.pop("source_diversity_json", "{}") or "{}")
        item["temporal_span"] = json.loads(item.pop("temporal_span_json", "{}") or "{}")
        item["sample_titles"] = parse_concepts_json(item.pop("sample_titles_json", None))
        evidence = [
            dict(row)
            for row in conn.execute(
                """
                SELECT packet_evidence_id, evidence_rank, evidence_id, relation_candidate_id,
                       passage_id, doc_id, source_title, date, passage_index,
                       candidate_score, evidence_role, substr(evidence_excerpt, 1, 900) AS evidence_excerpt
                FROM graph_pair_review_packet_evidence_v2
                WHERE packet_id = ?
                ORDER BY evidence_rank
                LIMIT 8
                """,
                (item["packet_id"],),
            )
        ]
        item["evidence"] = evidence
    run = conn.execute(
        """
        SELECT run_id, source_pair_count, packet_count, evidence_count, status,
               started_at, finished_at, report_path
        FROM graph_pair_review_packet_runs_v2
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    tier_counts = [
        dict(row)
        for row in conn.execute(
            """
            SELECT packet_tier, COUNT(*) AS count
            FROM graph_pair_review_packets_v2
            WHERE run_id = ?
            GROUP BY packet_tier
            ORDER BY count DESC, packet_tier
            """,
            (run_id,),
        )
    ]
    action_counts = [
        dict(row)
        for row in conn.execute(
            """
            SELECT recommended_action, COUNT(*) AS count
            FROM graph_pair_review_packets_v2
            WHERE run_id = ?
            GROUP BY recommended_action
            ORDER BY count DESC, recommended_action
            """,
            (run_id,),
        )
    ]
    return {
        "run": dict(run) if run else None,
        "tier_counts": tier_counts,
        "action_counts": action_counts,
        "filters": {"run_id": run_id, "limit": limit, "offset": offset, "q": query, "tier": tier, "action": action},
        "result": result,
        "stats": api_stats(conn),
    }


def api_tier1_promotion(conn: sqlite3.Connection, params: dict[str, list[str]]) -> dict:
    run_id = get_text(params, "run_id", "memory-carry-tier1-promotion-reconciliation-v2-20260609")
    query = get_text(params, "q")
    status = get_text(params, "status", "all")
    filters: list[str] = ["run_id = ?"]
    values: list = [run_id]
    where_text(
        filters,
        values,
        [
            "reconciliation_id",
            "packet_id",
            "relation_candidate_id",
            "concept_a",
            "concept_b",
            "relation_label",
            "subject_entity_id",
            "object_entity_id",
            "p1_proposal_id",
            "spotcheck_id",
            "staging_id",
            "final_proposal_id",
            "readiness_status",
            "required_next_step",
            "rationale",
        ],
        query,
    )
    where_value(filters, values, "readiness_status", status)
    items = [
        dict(row)
        for row in conn.execute(
            f"""
            SELECT reconciliation_id, packet_id, relation_candidate_id,
                   concept_a, concept_b, relation_label,
                   subject_entity_id, predicate, object_entity_id,
                   support_doc_count, support_passage_count,
                   packet_source_diversity_json, packet_temporal_span_json,
                   p1_proposal_id, p1_decision, spotcheck_id, spotcheck_decision,
                   staging_id, staging_status, final_proposal_id, final_policy_decision,
                   duplicate_relation_id, readiness_status, required_next_step, rationale
            FROM tier1_promotion_reconciliation_v2
            {make_where(filters)}
            ORDER BY
              CASE readiness_status
                WHEN 'ready_for_user_or_llm_final_review' THEN 1
                WHEN 'needs_p1_proposal_and_spotcheck' THEN 2
                ELSE 3 END,
              support_doc_count DESC
            """,
            values,
        )
    ]
    for item in items:
        item["source_diversity"] = json.loads(item.pop("packet_source_diversity_json", "{}") or "{}")
        item["temporal_span"] = json.loads(item.pop("packet_temporal_span_json", "{}") or "{}")
    run = conn.execute(
        """
        SELECT run_id, tier1_packet_count, ready_final_review_count, missing_chain_count,
               status, started_at, finished_at, report_path
        FROM tier1_promotion_reconciliation_runs_v2
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    readiness_counts = [
        dict(row)
        for row in conn.execute(
            """
            SELECT readiness_status, COUNT(*) AS count
            FROM tier1_promotion_reconciliation_v2
            WHERE run_id = ?
            GROUP BY readiness_status
            ORDER BY count DESC, readiness_status
            """,
            (run_id,),
        )
    ]
    return {
        "run": dict(run) if run else None,
        "readiness_counts": readiness_counts,
        "filters": {"run_id": run_id, "q": query, "status": status},
        "items": items,
        "stats": api_stats(conn),
    }


API_HANDLERS = {
    "/api/stats": api_stats,
    "/api/facets": api_facets,
    "/api/graph": api_graph,
    "/api/graph-insights": api_graph_insights,
    "/api/pair-review-packets": api_pair_review_packets,
    "/api/tier1-promotion": api_tier1_promotion,
    "/api/documents": api_documents,
    "/api/deep-passages": api_deep_passages,
    "/api/deep-claims": api_deep_claims,
    "/api/aggregate-passages": api_aggregate_passages,
    "/api/aggregate-claims": api_aggregate_claims,
    "/api/relation-candidates": api_relation_candidates,
    "/api/relation-evidence": api_relation_evidence,
    "/api/multihop": api_multihop,
    "/api/final-proposals": api_final_proposals,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "MemoryCarryDynamicBrowser/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"{datetime.now().isoformat(timespec='seconds')} {self.client_address[0]} {fmt % args}")

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_json(404, {"error": "not_found"})
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix.lower() == ".html":
            content_type = "text/html; charset=utf-8"
        elif path.suffix.lower() == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix.lower() == ".css":
            content_type = "text/css; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        params = parse_qs(parsed.query, keep_blank_values=True)
        if route in API_HANDLERS:
            try:
                with open_db() as conn:
                    payload = API_HANDLERS[route](conn, params)
                self.send_json(200, payload)
            except Exception as exc:
                self.send_json(500, {"error": "api_error", "detail": str(exc)})
            return
        if route in ("", "/"):
            self.send_file(ROOT / "index.html")
            return
        candidate = (ROOT / unquote(route.lstrip("/"))).resolve()
        if ROOT not in candidate.parents and candidate != ROOT:
            self.send_json(403, {"error": "forbidden"})
            return
        self.send_file(candidate)

    def do_POST(self) -> None:
        self.send_json(405, {"error": "read_only_service", "allowed_methods": ["GET", "HEAD"]})

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST


def write_closeout(host: str, port: int) -> None:
    with open_db() as conn:
        stats = api_stats(conn)
    REPORT_PATH.write_text(
        f"""# Memory Carry Dynamic Browser Closeout

Completed: {datetime.now().isoformat(timespec="seconds")}

## Output

- URL: `http://{host}:{port}/index.html`
- App directory: `{ROOT}`
- Server: `{ROOT / "server.py"}`
- Launcher: `{ROOT / "start-server.ps1"}`
- Source database opened read-only: `{DB_PATH}`

## Contents

- documents: {stats["documents"]}
- deep_read_docs: {stats["deep_read_docs"]}
- deep_read_passages_v2: {stats["deep_read_passages"]}
- passage_claim_candidates_v2: {stats["deep_read_claims"]}
- aggregate_passages_v2: {stats["aggregate_passages"]}
- aggregate_claim_candidates_v2: {stats["aggregate_claims"]}
- graph_relation_candidates_v2: {stats["relation_candidates"]}
- graph_relation_candidate_evidence_v2: {stats["relation_evidence"]}
- multihop_candidate_staging_v2: {stats["multihop_staging"]}
- final_insert_proposals_v2: {stats["final_insert_proposals"]}
- formal relations: {stats["formal_relations"]}
- foreign key check rows: {stats["foreign_key_check_rows"]}

## Boundary

This phase adds a SQLite-backed read-only browser and API. SQLite is opened with URI `mode=ro` and `PRAGMA query_only=ON`; the HTTP service allows only GET/HEAD and exposes only whitelisted queries. It does not modify original PDFs, source `memory_carry.db`, R2R collection data, derived SQLite tables, or final `relations`.
""",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Read-only Memory Carry dynamic evidence browser")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    write_closeout(args.host, args.port)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"url": f"http://{args.host}:{args.port}/index.html", "db": str(DB_PATH), "read_only": True}, ensure_ascii=False))
    server.serve_forever()


if __name__ == "__main__":
    main()
