"""Graphviz 다이어그램 (org_chart, flow_diagram, shareholding) 단위 테스트.

> 마지막 수정: 2026-02-10 13:45:13

graphviz Python 패키지 미설치 환경에서도 동작하도록 mock 사용.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.chart_engine.config import DEFAULT_CHART_CONFIG
from src.chart_engine.exceptions import GraphvizError


# graphviz 모듈을 mock하여 테스트
@pytest.fixture(autouse=True)
def mock_graphviz(monkeypatch):
    """graphviz 모듈 mock."""
    mock_module = MagicMock()

    class FakeDigraph:
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "")
            self.format = kwargs.get("format", "svg")
            self.graph_attr = dict(kwargs.get("graph_attr", {}))
            self.node_attr = dict(kwargs.get("node_attr", {}))
            self.edge_attr = dict(kwargs.get("edge_attr", {}))
            self._nodes: list[tuple[str, dict]] = []
            self._edges: list[tuple[str, str, dict]] = []
            self._attrs: dict[str, str] = {}

        def attr(self, **kwargs):
            self._attrs.update(kwargs)

        def node(self, name, label=None, **attrs):
            self._nodes.append((name, {"label": label, **attrs}))

        def edge(self, tail, head, label="", **attrs):
            self._edges.append((tail, head, {"label": label, **attrs}))

        def pipe(self, format="svg"):
            return b"<svg>mock</svg>"

        @property
        def source(self) -> str:
            """DOT source 문자열 생성 (간이)."""
            lines = [f"digraph {self.name} {{"]
            for k, v in self.graph_attr.items():
                lines.append(f"  {k}={v}")
            for k, v in self._attrs.items():
                lines.append(f"  {k}={v}")
            for name, attrs in self._nodes:
                attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items() if v)
                lines.append(f"  {name} [{attr_str}]")
            for tail, head, attrs in self._edges:
                label = attrs.get("label", "")
                extra = " ".join(
                    f'{k}="{v}"' for k, v in attrs.items() if v and k != "label"
                )
                all_attrs = f'label="{label}" {extra}'.strip()
                lines.append(f"  {tail} -> {head} [{all_attrs}]")
            lines.append("}")
            return "\n".join(lines)

    mock_module.Digraph = FakeDigraph
    monkeypatch.setitem(__import__("sys").modules, "graphviz", mock_module)


class TestOrgChart:
    """조직도."""

    def test_create_nodes(self, org_chart_structure):
        """노드 수 확인."""
        from src.chart_engine.graphviz.org_chart import create_org_chart

        dot = create_org_chart(org_chart_structure, title="조직도")
        source = dot.source
        assert "ceo" in source
        assert "cfo" in source
        assert "cto" in source
        assert "dev" in source

    def test_level_colors(self, org_chart_structure):
        """레벨별 색상 적용 확인."""
        from src.chart_engine.graphviz.org_chart import create_org_chart

        c = DEFAULT_CHART_CONFIG.colors
        dot = create_org_chart(org_chart_structure)
        source = dot.source
        assert c.primary in source
        assert c.bg_light_green in source

    def test_empty_nodes_raises(self):
        """빈 노드 시 GraphvizError."""
        from src.chart_engine.graphviz.org_chart import create_org_chart

        with pytest.raises(GraphvizError, match="org_chart"):
            create_org_chart({"nodes": [], "edges": []})

    def test_rankdir_lr(self, org_chart_structure):
        """LR 방향 설정."""
        from src.chart_engine.graphviz.org_chart import create_org_chart

        dot = create_org_chart(org_chart_structure, rankdir="LR")
        assert "LR" in dot.source


class TestFlowDiagram:
    """플로우 다이어그램."""

    def test_create(self, flow_steps):
        """플로우 다이어그램 생성."""
        from src.chart_engine.graphviz.flow_diagram import create_flow_diagram

        dot = create_flow_diagram(flow_steps, title="M&A 프로세스")
        source = dot.source
        assert "start" in source
        assert "dd" in source
        assert "nego" in source
        assert "close" in source

    def test_node_shapes(self, flow_steps):
        """노드 타입별 shape 확인."""
        from src.chart_engine.graphviz.flow_diagram import create_flow_diagram

        dot = create_flow_diagram(flow_steps)
        source = dot.source
        assert "diamond" in source

    def test_empty_nodes_raises(self):
        """빈 노드 시 GraphvizError."""
        from src.chart_engine.graphviz.flow_diagram import create_flow_diagram

        with pytest.raises(GraphvizError, match="flow_diagram"):
            create_flow_diagram({"nodes": [], "edges": []})


class TestShareholdingDiagram:
    """주주구조도."""

    def test_create(self, shareholding_data):
        """주주구조도 생성."""
        from src.chart_engine.graphviz.shareholding import create_shareholding_diagram

        dot = create_shareholding_diagram(shareholding_data, title="지배구조")
        source = dot.source
        assert "founder" in source
        assert "holding" in source
        assert "sub1" in source

    def test_stake_labels(self, shareholding_data):
        """지분율 라벨 표시."""
        from src.chart_engine.graphviz.shareholding import create_shareholding_diagram

        dot = create_shareholding_diagram(shareholding_data)
        source = dot.source
        assert "51%" in source
        assert "100%" in source
        assert "70%" in source

    def test_entity_shapes(self, shareholding_data):
        """엔티티 타입별 shape 확인."""
        from src.chart_engine.graphviz.shareholding import create_shareholding_diagram

        dot = create_shareholding_diagram(shareholding_data)
        source = dot.source
        assert "oval" in source

    def test_empty_entities_raises(self):
        """빈 엔티티 시 GraphvizError."""
        from src.chart_engine.graphviz.shareholding import create_shareholding_diagram

        with pytest.raises(GraphvizError, match="shareholding"):
            create_shareholding_diagram({"entities": [], "stakes": []})
