"""조직도 생성 — Graphviz DOT.

> 마지막 수정: 2026-02-10 13:45:13

design_renderer/components/org_chart.py의 create_org_chart()를 추출.
순수 그래프 생성 로직만 포함하며, PPTX/HTML 임베딩은 design_renderer에 남긴다.
"""

from __future__ import annotations

from typing import Any

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import GraphvizError


def create_org_chart(
    structure: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    rankdir: str = "TB",
) -> Any:
    """조직도 Graphviz Digraph 생성.

    Args:
        structure: {
            "nodes": [
                {"id": "ceo", "label": "홍길동\\nCEO", "level": 0},
                {"id": "cfo", "label": "김철수\\nCFO", "level": 1},
                ...
            ],
            "edges": [
                {"from": "ceo", "to": "cfo"},
                ...
            ]
        }
        title: 그래프 제목.
        config: 차트 설정.
        rankdir: 방향. "TB" (위→아래), "LR" (왼→오른).

    Returns:
        graphviz.Digraph 객체.

    Raises:
        GraphvizError: 구조 데이터 오류 시.
    """
    import graphviz

    cfg = config or DEFAULT_CHART_CONFIG
    c = cfg.colors
    font = cfg.font

    nodes = structure.get("nodes", [])
    edges = structure.get("edges", [])

    if not nodes:
        raise GraphvizError("org_chart", "nodes는 비어 있을 수 없습니다.")

    dot = graphviz.Digraph(
        name="org_chart",
        format="svg",
        graph_attr={
            "rankdir": rankdir,
            "bgcolor": "transparent",
            "fontname": font,
            "nodesep": "0.5",
            "ranksep": "0.6",
            "margin": "0.2",
        },
        node_attr={
            "shape": "box",
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
        },
    )

    if title:
        dot.attr(label=title, labelloc="t", fontsize="14", fontcolor=c.primary)

    # 노드 생성 (level에 따라 스타일 분기)
    for node in nodes:
        node_id = node.get("id", "")
        label = node.get("label", node_id)
        level = node.get("level", 1)

        if level == 0:
            # 최고경영진: AMIC 다크그린 배경, 흰 텍스트
            dot.node(
                node_id,
                label=label,
                fillcolor=c.primary,
                fontcolor=c.text_white,
                fontsize="11",
            )
        elif level == 1:
            # 임원: 밝은 그린 배경
            dot.node(
                node_id,
                label=label,
                fillcolor=c.bg_light_green,
                fontcolor=c.text_dark,
            )
        else:
            # 하위 조직: 쿨 그레이 배경
            dot.node(
                node_id,
                label=label,
                fillcolor=c.bg_cool_grey,
                fontcolor=c.text_body,
            )

    # 엣지 생성
    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        edge_label = edge.get("label", "")
        if from_id and to_id:
            dot.edge(from_id, to_id, label=edge_label)

    return dot
