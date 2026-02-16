import { cn } from "@/lib/cn";

export interface SectionHeaderProps {
  title: string;
  actions?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ title, actions, className }: SectionHeaderProps) {
  return (
    <div
      className={cn(
        "bg-amic text-white px-5 py-2.5 rounded-t-lg flex items-center justify-between",
        className
      )}
    >
      <h3 className="font-heading font-semibold">{title}</h3>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
