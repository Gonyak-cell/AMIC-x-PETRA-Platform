import { ExternalLink } from "lucide-react";
import type { VdrLink } from "@/modules/fdd/hooks/useChecklist";

interface Props {
  links: VdrLink[];
  dealId: string;
}

export default function VdrSourceLinks({ links, dealId }: Props) {
  if (!links.length) return null;

  return (
    <div className="mt-2 space-y-1">
      <p className="text-xs font-medium text-text-secondary">VDR Sources:</p>
      {links.map((link) => (
        <a
          key={link.id}
          href={`/fdd/deals/${dealId}/vdr`}
          className="flex items-center gap-1.5 text-xs text-accent-primary hover:underline"
        >
          <ExternalLink className="w-3 h-3 flex-shrink-0" />
          {link.description || "VDR Document"}
        </a>
      ))}
    </div>
  );
}
