// UI Components - Barrel Export
export { Button } from "./Button";
export type { ButtonProps } from "./Button";

export { Badge } from "./Badge";
export type { BadgeProps, BadgeVariant } from "./Badge";
export { getStatusVariant } from "@/lib/statusVariant";

export { Card } from "./Card";
export type { CardProps, CardVariant } from "./Card";

export { KpiCard } from "./KpiCard";
export type { KpiCardProps } from "./KpiCard";

export { DataTable } from "./DataTable";
export type { DataTableProps, Column, SectionHeaderConfig } from "./DataTable";

export { Modal } from "./Modal";
export type { ModalProps } from "./Modal";

export { Input } from "./Input";
export type { InputProps } from "./Input";

export { Select } from "./Select";
export type { SelectProps, SelectOption } from "./Select";

export { SectionHeader } from "./SectionHeader";
export type { SectionHeaderProps } from "./SectionHeader";

export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  KpiCardSkeleton,
  PageSkeleton,
  ChartSkeleton,
  TableSkeleton,
} from "./Skeleton";
export type { SkeletonProps, ChartSkeletonProps, TableSkeletonProps } from "./Skeleton";

export { Spinner, LoadingOverlay } from "./Spinner";
export type { SpinnerProps } from "./Spinner";

export { Breadcrumbs } from "./Breadcrumbs";
export type { BreadcrumbsProps, BreadcrumbItem } from "./Breadcrumbs";

export { EmptyState } from "./EmptyState";
export type { EmptyStateProps } from "./EmptyState";

export { LiveRegionProvider, useLiveAnnounce } from "./LiveRegion";
export type { LiveRegionProviderProps } from "./LiveRegion";
