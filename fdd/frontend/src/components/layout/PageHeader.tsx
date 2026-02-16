import { Breadcrumbs, type BreadcrumbItem } from "@/components/ui";

export interface PageHeaderProps {
  breadcrumbs?: BreadcrumbItem[];
  title?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ breadcrumbs, title, actions }: PageHeaderProps) {
  return (
    <header className="bg-white border-b border-gray-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          {breadcrumbs && breadcrumbs.length > 0 && (
            <Breadcrumbs items={breadcrumbs} className="mb-1" />
          )}
          {title && (
            <h1 className="text-xl font-heading font-bold text-text-dark">
              {title}
            </h1>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </header>
  );
}
