/**
 * TEST-3: DynamicVariableForm의 evalCondition 함수 테스트.
 *
 * evalCondition은 export되지 않은 모듈 내부 함수이므로,
 * DynamicVariableForm을 통해 간접 테스트한다 — 조건식에 따라 필드가 표시/숨김되는지 검증.
 *
 * 지원 패턴: ==, !=, >, >=, <, <=, and, or, not, 문자열/불리언/숫자
 */

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import DynamicVariableForm from "../DynamicVariableForm";
import type { TemplateVariable } from "@/modules/docs/types/contract_generation";

/** 테스트용 변수 팩토리 */
function makeVar(
  overrides: Partial<TemplateVariable> & { variable_key: string },
): TemplateVariable {
  return {
    id: `var-${overrides.variable_key}`,
    input_type: "TEXT",
    question_label: overrides.variable_key,
    description: null,
    default_value: null,
    is_required: false,
    select_options: null,
    display_order: 0,
    group_name: null,
    visible_condition: null,
    ...overrides,
  };
}

const noop = () => {};

describe("evalCondition (via DynamicVariableForm)", () => {
  it("visible_condition이 null이면 항상 표시된다", () => {
    const vars = [makeVar({ variable_key: "seller", question_label: "매도인" })];
    render(
      <DynamicVariableForm variables={vars} values={{}} onChange={noop} />,
    );
    expect(screen.getByLabelText("매도인")).toBeDefined();
  });

  it("불리언 조건 == True가 충족되면 표시된다", () => {
    const vars = [
      makeVar({
        variable_key: "escrow_amount",
        question_label: "에스크로 금액",
        visible_condition: "escrow_included == True",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: true }}
        onChange={noop}
      />,
    );
    expect(screen.getByLabelText("에스크로 금액")).toBeDefined();
  });

  it("불리언 조건 == True가 미충족이면 숨겨진다", () => {
    const vars = [
      makeVar({
        variable_key: "escrow_amount",
        question_label: "에스크로 금액",
        visible_condition: "escrow_included == True",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: false }}
        onChange={noop}
      />,
    );
    expect(screen.queryByLabelText("에스크로 금액")).toBeNull();
  });

  it("not 연산자: not escrow_included → false일 때 표시", () => {
    const vars = [
      makeVar({
        variable_key: "no_escrow_reason",
        question_label: "에스크로 미적용 사유",
        visible_condition: "not escrow_included",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: false }}
        onChange={noop}
      />,
    );
    expect(screen.getByLabelText("에스크로 미적용 사유")).toBeDefined();
  });

  it("숫자 비교: price > 1000 조건 충족 시 표시", () => {
    const vars = [
      makeVar({
        variable_key: "large_deal_note",
        question_label: "대형 거래 비고",
        visible_condition: "price > 1000",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ price: 5000 }}
        onChange={noop}
      />,
    );
    expect(screen.getByLabelText("대형 거래 비고")).toBeDefined();
  });

  it("숫자 비교: price > 1000 미충족 시 숨김", () => {
    const vars = [
      makeVar({
        variable_key: "large_deal_note",
        question_label: "대형 거래 비고",
        visible_condition: "price > 1000",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ price: 500 }}
        onChange={noop}
      />,
    );
    expect(screen.queryByLabelText("대형 거래 비고")).toBeNull();
  });

  it("and 조건: 양쪽 모두 참이면 표시", () => {
    const vars = [
      makeVar({
        variable_key: "escrow_details",
        question_label: "에스크로 상세",
        visible_condition: "escrow_included == True and price > 1000",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: true, price: 5000 }}
        onChange={noop}
      />,
    );
    expect(screen.getByLabelText("에스크로 상세")).toBeDefined();
  });

  it("and 조건: 한쪽이 거짓이면 숨김", () => {
    const vars = [
      makeVar({
        variable_key: "escrow_details",
        question_label: "에스크로 상세",
        visible_condition: "escrow_included == True and price > 1000",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: false, price: 5000 }}
        onChange={noop}
      />,
    );
    expect(screen.queryByLabelText("에스크로 상세")).toBeNull();
  });

  it("or 조건: 한쪽이 참이면 표시", () => {
    const vars = [
      makeVar({
        variable_key: "guarantee_clause",
        question_label: "보증 조항",
        visible_condition: "escrow_included == True or warranty_included == True",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: false, warranty_included: true }}
        onChange={noop}
      />,
    );
    expect(screen.getByLabelText("보증 조항")).toBeDefined();
  });

  it("or 조건: 양쪽 모두 거짓이면 숨김", () => {
    const vars = [
      makeVar({
        variable_key: "guarantee_clause",
        question_label: "보증 조항",
        visible_condition: "escrow_included == True or warranty_included == True",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ escrow_included: false, warranty_included: false }}
        onChange={noop}
      />,
    );
    expect(screen.queryByLabelText("보증 조항")).toBeNull();
  });

  it("문자열 비교: deal_type == \"SPA\" 조건", () => {
    const vars = [
      makeVar({
        variable_key: "spa_note",
        question_label: "SPA 비고",
        visible_condition: 'deal_type == "SPA"',
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{ deal_type: "SPA" }}
        onChange={noop}
      />,
    );
    expect(screen.getByLabelText("SPA 비고")).toBeDefined();
  });

  it("인식 불가 패턴은 숨김 처리된다", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

    const vars = [
      makeVar({
        variable_key: "hidden_field",
        question_label: "숨겨질 필드",
        visible_condition: "some_invalid_expression!!!",
      }),
    ];
    render(
      <DynamicVariableForm
        variables={vars}
        values={{}}
        onChange={noop}
      />,
    );
    expect(screen.queryByLabelText("숨겨질 필드")).toBeNull();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("인식할 수 없는 조건식"),
    );

    warnSpy.mockRestore();
  });
});
