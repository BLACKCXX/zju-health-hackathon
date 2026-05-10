from src.integration_agent import apply_teacher_feedback, compute_compression_ratio


def test_compute_compression_ratio():
    result = compute_compression_ratio(["abcd", "ef"], "abc")

    assert result["original_chars"] == 6
    assert result["integrated_chars"] == 3
    assert result["compression_ratio"] == 0.5


def test_apply_teacher_feedback_delete_or_edit():
    graph = {
        "nodes": [
            {"id": "n1", "name": "炎症", "summary": "原摘要", "status": "normal"},
            {"id": "n2", "name": "渗出", "summary": "原摘要", "status": "normal"},
        ],
        "edges": [],
        "feedback_records": [],
    }

    deleted_graph, delete_record = apply_teacher_feedback(
        graph,
        {"action": "delete", "target_type": "node", "target_id": "n1", "comment": "不展示"},
    )
    assert deleted_graph["nodes"][0]["status"] == "deleted"
    assert delete_record["after"]["status"] == "deleted"

    edited_graph, edit_record = apply_teacher_feedback(
        graph,
        {"action": "edit", "target_type": "node", "target_id": "n2", "comment": "补充机制解释"},
    )
    edited_node = next(node for node in edited_graph["nodes"] if node["id"] == "n2")
    assert edited_node["status"] == "updated"
    assert edited_node["teacher_note"] == "补充机制解释"
    assert edit_record["after"]["teacher_note"] == "补充机制解释"
