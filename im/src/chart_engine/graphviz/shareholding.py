"""지배구조도 / 주주구조도 — Graphviz DOT.

> 마지막 수정: 2026-02-10 13:45:13

지분율 기반 지배구조를 시각화한다.
엔티티 타입(회사/개인/펀드)별 노드 스타일과 지분율 엣지 라벨을 지원.
"""

from __future__ import annotations

from typing import Any

from src.chart_engine.config import ChartConfig, DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import GraphvizError

# 엔티티 타입별 Graphviz shape 매핑
_ENTITY_SHAPES: dict[str, str] = {
    "company": "box",
    "person": "oval",
    "fund": "hexagon",
}


def create_shareholding_diagram(
    shareholders: dict[str, Any],
    *,
    title: str = "",
    config: ChartConfig | None = None,
    rankdir: str = "TB",
) -> Any:
    """지배구조도 생성.

    Args:
        shareholders: {
            "entities": [
                {"id": "parent", "label": "모회사", "type": "company", "level": 0},
                {"id": "sub1", "label": "자회사A", "type": "company", "level": 1},
                {"id": "founder", "label": "창업자", "type": "person", "level": 0},
            ],
            "stakes": [
                {"from": "parent", "to": "sub1", "pct": 70.0, "label": "70%"},
                {"from": "founder", "to": "parent", "pct": 51.0, "label": "51%"},
            ]
        }
        title: 그래프 제목.
        config: 차트 설정.
        rankdir: 방향. "TB" (위→아래, 기본).

    Returns:
        graphviz.Digraph 객체.

    Raises:
        GraphvizError: 구조 데이터 오류 시.
    """
    import graphviz

    cfg = config or DEFAULT_CHART_CONFIG
    c = cfg.colors
    font = cfg.font

    entities = shareholders.get("entities", [])
    stakes = shareholders.get("stakes", [])

    if not entities:
        raise GraphvizError("shareholding", "entities는 비어 있을 수 없습니다.")

    dot = graphviz.Digraph(
        name="shareholding",
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
            "penwidth": "1.5",
            "arrowsize": "0.7",
            "fontname": font,
            "fontsize": "9",
            "fontcolor": c.text_body,
        },
    )

    if title:
        dot.attr(label=title, labelloc="t", fontsize="14", fontcolor=c.primary)

    # 엔티티 노드 생성
    for entity in entities:
        entity_id = entity.get("id", "")
        label = entity.get("label", entity_id)
        entity_type = entity.get("type", "company")
        level = entity.get("level", 1)
        shape = _ENTITY_SHAPES.get(entity_type, "box")

        # 레벨별 배색 (org_chart와 동일 패턴)
        if level == 0:
            dot.node(
                entity_id,
                label=label,
                shape=shape,
                fillcolor=c.primary,
                fontcolor=c.text_white,
                fontsize="11",
            )
        elif level == 1:
            dot.node(
                entity_id,
                label=label,
                shape=shape,
                fillcolor=c.bg_light_green,
                fontcolor=c.text_dark,
            )
        else:
            dot.node(
                entity_id,
                label=label,
                shape=shape,
                fillcolor=c.bg_cool_grey,
                fontcolor=c.text_body,
            )

    # 지분 엣지 생성
    for stake in stakes:
        from_id = stake.get("from", "")
        to_id = stake.get("to", "")
        pct = stake.get("pct", 0.0)
        edge_label = stake.get("label", f"{pct:.0f}%")

        if not from_id or not to_id:
            continue

        # 지분율에 따라 선 굵기 조절
        pen_width = "2.5" if pct >= 50.0 else "1.5"
        color = c.primary if pct >= 50.0 else c.gray_medium

        dot.edge(
            from_id,
            to_id,
            label=edge_label,
            penwidth=pen_width,
            color=color,
        )

    return dot
