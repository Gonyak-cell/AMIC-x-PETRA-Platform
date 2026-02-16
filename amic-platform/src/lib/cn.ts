/**
 * className 병합 유틸리티
 * Tailwind 클래스 충돌을 자동 해결 (tailwind-merge + clsx)
 */
import { twMerge } from "tailwind-merge";
import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
