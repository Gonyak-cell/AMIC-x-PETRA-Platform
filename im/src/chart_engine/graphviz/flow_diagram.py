"""거래구조도 / 프로세스 플로우 다이어그램 — Graphviz DOT.

> 마지막 수정: 2026-02-10 13:45:13

M&A 프로세스 타임라인, 비즈니스 모델 흐름도 등을 시각화한다.
"""

from __future__ import annotations

from typing import Any

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import GraphvizError

# 노드 타입별 Graphviz shape 매핑
_NODE_SHAPES: dict[str, str] = {
    "process": "box",
    "decision": "diamond",
    "start": "oval",
    "end": "oval",
    "io": "parallelogram",
}


def create_flow_diagram(
    steps: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    rankdir: str = "LR",
) -> Any:
    """프로세스 플로우 다이어그램 생성.

    Args:
        steps: {
            "nodes": [
                {"id": "step1", "label": "인수 의향서", "type": "start"},
                {"id": "step2", "label": "실사 진행", "type": "process"},
                {"id": "step3", "label": "가격 협상", "type": "decision"},
                {"id": "step4", "label": "계약 체결", "type": "end"},
            ],
            "edges": [
                {"from": "step1", "to": "step2"},
                {"from": "step2", "to": "step3"},
                {"from": "step3", "to": "step4", "label": "합의"},
            ]
        }
        title: 그래프 제목.
        config: 차트 설정.
        rankdir: 방향. "LR" (왼→오른, 기본), "TB" (위→아래).

    Returns:
        graphviz.Digraph 객체.

    Raises:
        GraphvizError: 구조 데이터 오류 시.
    """
    import graphviz

    cfg = config or DEFAULT_CHART_CONFIG
    c = cfg.colors
    font = cfg.font

    nodes = steps.get("nodes", [])
    edges = steps.get("edges", [])

    if not nodes:
        raise GraphvizError("flow_diagram", "nodes는 비어 있을 수 없습니다.")

    dot = graphviz.Digraph(
        name="flow_diagram",
        format="svg",
        graph_attr={
            "rankdir": rankdir,
            "bgcolor": "transparent",
            "fontname": font,
            "nodesep": "0.6",
            "ranksep": "0.8",
            "margin": "0.2",
        },
        node_attr={
            "style": "filled,rounded",
            "fontname": font,
            "fontsize": "10",
            "margin": "0.15,0.08",
            "penwidth": "1.5",
        },
        edge_attr={
            "color": c.gray_medium,
            "penwidth": "1.5",
            "arrowsize": "0.7",
            "fontname": font,
            "fontsize": "9",
        },
    )

    if title:
        dot.attr(label=title, labelloc="t", fontsize="14", fontcolor=c.primary)

    for node in nodes:
        node_id = node.get("id", "")
        label = node.get("label", node_id)
        node_type = node.get("type", "process")
        shape = _NODE_SHAPES.get(node_type, "box")

        # 타입별 스타일
        if node_type in ("start", "end"):
            dot.node(
                node_id,
                label=label,
                shape=shape,
                fillcolor=c.primary,
                fontcolor=c.text_white,
                fontsize="11",
            )
        elif node_type == "decision":
            dot.node(
                node_id,
                label=label,
                shape=shape,
                fillcolor=c.caution,
                fontcolor=c.text_white,
                fontsize="10",
            )
        else:
            dot.node(
                node_id,
                label=label,
                shape=shape,
                fillcolor=c.bg_light_green,
                fontcolor=c.text_dark,
            )

    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        edge_label = edge.get("label", "")
        if from_id and to_id:
            dot.edge(from_id, to_id, label=edge_label)

    return dot
