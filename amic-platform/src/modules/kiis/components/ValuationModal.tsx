import { useState, useEffect } from "react";
import { Modal, Input, Button } from "@/components/ui";
import type { PortfolioItem } from "@/modules/kiis/types/portfolio";
import { formatAmount } from "@/lib/format";

interface ValuationModalProps {
  open: boolean;
  onClose: () => void;
  item: PortfolioItem | null;
  onSubmit: (portfolioId: number, valuation: string) => void;
  isPending: boolean;
}

export default function ValuationModal({
  open,
  onClose,
  item,
  onSubmit,
  isPending,
}: ValuationModalProps) {
  const [valuation, setValuation] = useState("");

  useEffect(() => {
    if (open && item?.estimated_valuation) {
      setValuation(item.estimated_valuation);
    } else if (open) {
      setValuation("");
    }
  }, [open, item]);

  const handleSubmit = () => {
    if (!item || !valuation.trim()) return;
    onSubmit(item.id, valuation.trim());
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Update Valuation"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={isPending}
            disabled={!valuation.trim()}
          >
            Update
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {item && (
          <div className="text-sm text-text-secondary">
            <span className="font-medium text-text-dark">
              {item.target_company_name}
            </span>
            {item.estimated_valuation && (
              <span className="ml-2">
                (Current: {formatAmount(item.estimated_valuation, "KRW")})
              </span>
            )}
          </div>
        )}
        <Input
          label="Estimated Valuation (KRW)"
          placeholder="e.g. 1000000000000"
          value={valuation}
          onChange={(e) => setValuation(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />
      </div>
    </Modal>
  );
}
