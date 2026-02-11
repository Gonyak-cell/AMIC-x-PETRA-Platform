---
name: new-component
description: 새 UI 컴포넌트 생성. 디자인 시스템 일관성과 접근성 보장.
---
# 새 UI 컴포넌트 생성 가이드

대상 컴포넌트: $ARGUMENTS

## 위치 결정
- 전역 재사용: `src/components/ui/{Component}.tsx`
- 모듈 전용: `src/modules/{mod}/components/{Component}.tsx`

## 표준 구조
```tsx
import { type ComponentPropsWithoutRef, forwardRef } from "react";
import { cn } from "@/lib/cn";

export interface {Component}Props extends ComponentPropsWithoutRef<"div"> {
  variant?: "default" | "accent";
  size?: "sm" | "md" | "lg";
}

export const {Component} = forwardRef<HTMLDivElement, {Component}Props>(
  ({ variant = "default", size = "md", className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "base-classes",
          variant === "accent" && "accent-classes",
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);
{Component}.displayName = "{Component}";
```

## 필수 사항
- `cn()` 유틸리티로 클래스 합성 (`@/lib/cn`)
- Props 인터페이스를 named export
- 접근성: ARIA 속성, 키보드 이벤트
- Tailwind 전용 (인라인 스타일 금지)

## 공유 컴포넌트 시 추가 작업
- `src/components/ui/index.ts`에 barrel export 추가

## 참조 파일
- `src/components/ui/Button.tsx` — 다형성 컴포넌트
- `src/components/ui/Card.tsx` — 컨테이너 컴포넌트
- `src/components/ui/DataTable.tsx` — 제네릭 컴포넌트
- `src/components/ui/Modal.tsx` — 오버레이 + focus trap
