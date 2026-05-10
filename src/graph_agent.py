from __future__ import annotations

import re

from .integration_agent import summarize_integration


TYPE_KEYWORDS = [
    ("mechanism", ["机制", "病理", "生理", "发生", "发展"]),
    ("diagnosis", ["诊断", "检查", "指标"]),
    ("treatment", ["治疗", "用药", "处理"]),
    ("complication", ["并发症", "后果"]),
    ("risk_factor", ["危险因素", "因素", "病因"]),
    ("symptom", ["症状", "表现"]),
    ("prevention", ["预防", "控制"]),
]


def build_graph(topic: str, evidence: list[dict]) -> dict:
    topic = topic.strip() or "主题"
    graph_evidence = [_graph_evidence(item) for item in evidence]
    nodes = [
        {
            "id": "node_001",
            "name": topic,
            "type": "concept",
            "level": 0,
            "summary": f"{topic} 的跨教材整合主题节点。",
            "book_sources": sorted({item.get("book", "") for item in evidence if item.get("book")}),
            "evidence_ids": [item["evidence_id"] for item in graph_evidence[: min(5, len(graph_evidence))]],
            "confidence": 0.85 if evidence else 0.2,
            "status": "normal",
            "x": None,
            "y": None,
        }
    ]
    edges = []
    concepts = _extract_concepts(topic, evidence)
    for idx, concept in enumerate(concepts, start=2):
        ev_ids = concept["evidence_ids"]
        node_id = f"node_{idx:03d}"
        nodes.append(
            {
                "id": node_id,
                "name": concept["name"],
                "type": concept["type"],
                "level": 1 if idx <= 7 else 2,
                "summary": concept["summary"],
                "book_sources": concept["books"],
                "evidence_ids": ev_ids,
                "confidence": concept["confidence"],
                "status": "normal",
                "x": None,
                "y": None,
            }
        )
        edges.append(
            {
                "id": f"edge_{idx - 1:03d}",
                "source": "node_001",
                "target": node_id,
                "relation": concept["relation"],
                "label": concept["label"],
                "summary": f"{concept['name']} 与 {topic} 相关。",
                "evidence_ids": ev_ids[:2],
                "confidence": concept["confidence"],
                "status": "normal",
            }
        )
    integrated_text = "；".join(node.get("summary", "") for node in nodes)
    return {
        "topic": topic,
        "nodes": nodes,
        "edges": edges,
        "evidence": graph_evidence,
        "integration": summarize_integration(topic, graph_evidence, integrated_text),
        "feedback_records": [],
    }


def update_graph(topic: str, followup: str, current_graph: dict, evidence: list[dict]) -> tuple[dict, dict]:
    graph = dict(current_graph or build_graph(topic, evidence))
    graph["nodes"] = [dict(node) for node in graph.get("nodes", [])]
    graph["edges"] = [dict(edge) for edge in graph.get("edges", [])]
    existing_names = {node.get("name") for node in graph["nodes"]}
    graph_evidence = list(graph.get("evidence", []))
    known_ev = {item.get("evidence_id") for item in graph_evidence}
    for item in evidence:
        ge = _graph_evidence(item)
        if ge["evidence_id"] not in known_ev:
            graph_evidence.append(ge)
    graph["evidence"] = graph_evidence
    added_nodes = []
    added_edges = []
    concepts = _extract_concepts(followup or topic, evidence)[:4]
    for concept in concepts:
        if concept["name"] in existing_names:
            continue
        node_id = f"node_{len(graph['nodes']) + 1:03d}"
        node = {
            "id": node_id,
            "name": concept["name"],
            "type": concept["type"],
            "level": 2,
            "summary": concept["summary"],
            "book_sources": concept["books"],
            "evidence_ids": concept["evidence_ids"],
            "confidence": concept["confidence"],
            "status": "added",
            "x": None,
            "y": None,
        }
        edge = {
            "id": f"edge_{len(graph['edges']) + 1:03d}",
            "source": "node_001",
            "target": node_id,
            "relation": "associated_with",
            "label": "补充",
            "summary": f"根据追问补充 {concept['name']} 节点。",
            "evidence_ids": concept["evidence_ids"][:2],
            "confidence": concept["confidence"],
            "status": "added",
        }
        graph["nodes"].append(node)
        graph["edges"].append(edge)
        added_nodes.append(node)
        added_edges.append(edge)
    patch = {
        "added_nodes": added_nodes,
        "added_edges": added_edges,
        "updated_nodes": [],
        "highlight_nodes": [node["id"] for node in added_nodes],
    }
    return graph, patch


def _graph_evidence(item: dict) -> dict:
    return {
        "evidence_id": item.get("evidence_id", ""),
        "book": item.get("book", ""),
        "source_file": item.get("source_file", ""),
        "chapter": item.get("chapter", "章节待识别"),
        "page": int(item.get("page", 0) or 0),
        "quote": item.get("quote") or item.get("text", "")[:260],
        "chunk_id": item.get("chunk_id", ""),
    }


def _extract_concepts(topic: str, evidence: list[dict]) -> list[dict]:
    concepts: dict[str, dict] = {}
    seed_names = ["定义", "病因与危险因素", "发生机制", "临床表现", "诊断依据", "治疗与干预", "并发症", "预防管理"]
    for idx, name in enumerate(seed_names):
        concepts[name] = {
            "name": name,
            "type": _type_for_name(name),
            "relation": _relation_for_type(_type_for_name(name)),
            "label": _label_for_type(_type_for_name(name)),
            "summary": f"从教材证据中整合“{topic}”的{name}。",
            "books": [],
            "evidence_ids": [],
            "confidence": 0.55,
        }
    for item in evidence:
        text = item.get("quote") or item.get("text", "")
        target = _classify_text(text)
        data = concepts.setdefault(
            target,
            {
                "name": target,
                "type": _type_for_name(target),
                "relation": _relation_for_type(_type_for_name(target)),
                "label": _label_for_type(_type_for_name(target)),
                "summary": text[:90],
                "books": [],
                "evidence_ids": [],
                "confidence": 0.6,
            },
        )
        if item.get("book") and item["book"] not in data["books"]:
            data["books"].append(item["book"])
        if item.get("evidence_id") and item["evidence_id"] not in data["evidence_ids"]:
            data["evidence_ids"].append(item["evidence_id"])
        data["confidence"] = min(0.92, data["confidence"] + 0.04)
    return [item for item in concepts.values() if item["evidence_ids"]][:10] or list(concepts.values())[:5]


def _classify_text(text: str) -> str:
    for name, words in [
        ("治疗与干预", ["治疗", "用药", "干预", "处理"]),
        ("诊断依据", ["诊断", "检查", "指标", "标准"]),
        ("并发症", ["并发", "损害", "衰竭"]),
        ("病因与危险因素", ["病因", "危险", "因素", "遗传"]),
        ("发生机制", ["机制", "病理", "生理", "导致"]),
        ("临床表现", ["症状", "表现", "体征"]),
        ("预防管理", ["预防", "控制", "管理"]),
    ]:
        if any(word in text for word in words):
            return name
    return "定义"


def _type_for_name(name: str) -> str:
    for node_type, words in TYPE_KEYWORDS:
        if any(word in name for word in words):
            return node_type
    return "definition" if "定义" in name else "book_specific"


def _relation_for_type(node_type: str) -> str:
    return {
        "mechanism": "explains",
        "diagnosis": "diagnosed_by",
        "treatment": "treated_by",
        "risk_factor": "causes",
        "complication": "complicates",
        "prevention": "prevents",
    }.get(node_type, "associated_with")


def _label_for_type(node_type: str) -> str:
    return {
        "mechanism": "解释",
        "diagnosis": "诊断",
        "treatment": "干预",
        "risk_factor": "影响",
        "complication": "并发",
        "prevention": "预防",
    }.get(node_type, "相关")
