import { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { CheckboxGroup } from "@/components/ui/CheckboxGroup";
import { Button } from "@/components/ui/Button";
import { useBuyers } from "@/modules/ma/hooks/useTransactions";
import { useUpdateDistribution } from "@/modules/ma/hooks/useMarketingMaterials";
import type { MarketingMaterial } from "@/modules/ma/types/marketing_material";

interface DistributionModalProps {
  open: boolean;
  onClose: () => void;
  material: MarketingMaterial;
  txnId: string;
}

export default function DistributionModal({
  open,
  onClose,
  material,
  txnId,
}: DistributionModalProps) {
  const { data: buyers } = useBuyers(txnId);
  const updateDistribution = useUpdateDistribution(txnId);

  const [selected, setSelected] = useState<string[]>([]);

  // 모달 열릴 때 기존 배포 대상으로 초기화
  useEffect(() => {
    if (open) {
      setSelected(material.distributed_to ?? []);
    }
  }, [open, material.distributed_to]);

  const options = (buyers ?? []).map((b) => ({
    value: b.company_name,
    label: b.company_name,
  }));

  const handleSubmit = () => {
    updateDistribution.mutate(
      { matId: material.id, body: { distributed_to: selected } },
      { onSuccess: onClose },
    );
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="마케팅 자료 배포"
      size="md"
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onClose}>
            취소
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={selected.length === 0 || updateDistribution.isPending}
          >
            {updateDistribution.isPending ? "저장 중…" : "배포"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-text-muted">
          <strong>{material.title}</strong>을 배포할 매수자를 선택하세요.
        </p>
        {options.length === 0 ? (
          <p className="text-sm text-gray-400">등록된 매수자가 없습니다.</p>
        ) : (
          <CheckboxGroup
            label="배포 대상"
            options={options}
            selected={selected}
            onChange={setSelected}
          />
        )}
      </div>
    </Modal>
  );
}
