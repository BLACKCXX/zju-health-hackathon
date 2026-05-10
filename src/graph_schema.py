from __future__ import annotations

from typing import Literal, TypedDict


NodeType = Literal[
    "concept",
    "definition",
    "mechanism",
    "symptom",
    "disease",
    "diagnosis",
    "treatment",
    "risk_factor",
    "complication",
    "prevention",
    "book_specific",
]

NodeStatus = Literal["normal", "added", "updated", "deleted", "highlighted"]
EdgeRelation = Literal[
    "causes",
    "belongs_to",
    "associated_with",
    "diagnosed_by",
    "treated_by",
    "complicates",
    "prevents",
    "explains",
    "contrasts_with",
]


class GraphEvidence(TypedDict, total=False):
    evidence_id: str
    book: str
    source_file: str
    chapter: str
    page: int
    quote: str
    chunk_id: str


class GraphNode(TypedDict, total=False):
    id: str
    name: str
    type: NodeType
    level: int
    summary: str
    book_sources: list[str]
    evidence_ids: list[str]
    confidence: float
    status: NodeStatus
    x: float | None
    y: float | None


class GraphEdge(TypedDict, total=False):
    id: str
    source: str
    target: str
    relation: EdgeRelation
    label: str
    summary: str
    evidence_ids: list[str]
    confidence: float
    status: NodeStatus


class GraphJSON(TypedDict, total=False):
    topic: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    evidence: list[GraphEvidence]
    integration: dict
    feedback_records: list[dict]
