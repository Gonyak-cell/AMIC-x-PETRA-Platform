import { cn } from "@/lib/cn";

export interface SectionHeaderProps {
  title: string;
  actions?: React.ReactNode;
  uppercase?: boolean;
  leftAccent?: boolean;
  className?: string;
}

export function SectionHeader({ title, actions, uppercase = false, leftAccent = false, className }: SectionHeaderProps) {
  return (
    <div
      className={cn(
        "bg-white border border-gray-border border-b-0 px-5 py-2.5 rounded-t-dr flex items-center justify-between",
        leftAccent && "border-accent-left",
        className
      )}
    >
      <h3 className={cn(
        "font-heading font-semibold text-amic flex items-center gap-2",
        uppercase && "label-uppercase text-sm"
      )}>
        <span className="inline-block w-1 h-4 bg-accent rounded-full" />
        {title}
      </h3>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
