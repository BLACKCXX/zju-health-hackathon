export type GraphNodeType =
  | 'concept'
  | 'definition'
  | 'mechanism'
  | 'pathological_change'
  | 'cause'
  | 'disease'
  | 'symptom'
  | 'diagnosis'
  | 'treatment'
  | 'risk_factor'
  | 'complication'
  | 'prevention'
  | 'book_specific'

export type GraphStatus = 'normal' | 'added' | 'updated' | 'deleted' | 'highlighted'

export type GraphMode = 'single_book' | 'integrated'

export type EdgeRelation =
  | 'prerequisite'
  | 'parallel'
  | 'contains'
  | 'applies_to'
  | 'causes'
  | 'belongs_to'
  | 'is_a'
  | 'diagnosed_by'
  | 'treated_by'
  | 'complicates'
  | 'prevents'
  | 'contrasts_with'
  | 'associated_with'
  | 'explains'

export interface GraphEvidence {
  evidence_id: string
  textbook: string
  source_file: string
  chapter: string
  page: number
  quote: string
  chunk_id: string
}

export interface GraphNode {
  id: string
  name: string
  type: GraphNodeType
  level: number
  summary: string
  book_sources: string[]
  chapter?: string
  page?: number
  evidence_ids: string[]
  frequency: number
  confidence: number
  status: GraphStatus
  expandable?: boolean
  expanded?: boolean
  x?: number | null
  y?: number | null
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relation: EdgeRelation
  label: string
  summary: string
  evidence_ids: string[]
  confidence: number
  status: GraphStatus
}

export interface GraphDecision {
  decision_id: string
  action: 'merge' | 'keep' | 'remove'
  affected_nodes: string[]
  result_node?: string
  reason: string
  confidence: number
}

export interface GraphCompression {
  original_chars: number
  integrated_chars: number
  compression_ratio: number
}

export interface GraphIntegration {
  overlap_summary: string
  complement_summary: string
  missing_summary: string
  compression: GraphCompression
}

export interface GraphJSON {
  topic: string
  mode: GraphMode
  nodes: GraphNode[]
  edges: GraphEdge[]
  evidence: GraphEvidence[]
  decisions: GraphDecision[]
  integration: GraphIntegration
  feedback_records: Array<Record<string, unknown>>
}

// API request/response types

export interface SingleBookGraphRequest {
  textbook_id: string
  chapter_id?: string
  top_k?: number
}

export interface IntegratedGraphRequest {
  topic: string
  textbook_ids?: string[]
  top_k_per_book?: number
  global_top_k?: number
}

export interface GraphUpdateRequest {
  instruction: string
  current_graph: GraphJSON
}

export interface GraphUpdateResponse {
  graph: GraphJSON
  patch: {
    added_nodes: GraphNode[]
    added_edges: GraphEdge[]
    updated_nodes: GraphNode[]
    highlight_nodes: string[]
  }
  feedback_record: Record<string, unknown>
}

export interface FeedbackRequest {
  action: 'keep' | 'delete' | 'split' | 'merge' | 'edit'
  target_type: 'node' | 'edge' | 'decision'
  target_id: string
  comment: string
  graph: GraphJSON
}

export interface FeedbackResponse {
  success: boolean
  updated_graph: GraphJSON
  feedback_record: Record<string, unknown>
}

export interface ReportExportRequest {
  graph: GraphJSON
  format: 'markdown'
}

export interface ReportExportResponse {
  markdown: string
  filename: string
}
