import { useState } from "react";
import { UserPlus, Trash2, Building2 } from "lucide-react";
import {
  useDealClients,
  useAddDealClient,
  useRemoveDealClient,
} from "@/modules/ma/hooks/useDealClients";
import type { DealClientCreate } from "@/modules/ma/hooks/useDealClients";
import {
  Card,
  Button,
  DataTable,
  Modal,
  Input,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import type { DealClient } from "@/modules/ma/hooks/useDealClients";
import { formatDate } from "@/lib/format";

interface DealClientManagerProps {
  txnId: string;
}

const INITIAL_FORM: DealClientCreate = {
  email: "",
  display_name: "",
  organization: "",
};

export default function DealClientManager({ txnId }: DealClientManagerProps) {
  const { data: clients, isLoading } = useDealClients(txnId);
  const addClient = useAddDealClient(txnId);
  const removeClient = useRemoveDealClient(txnId);

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<DealClientCreate>(INITIAL_FORM);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    addClient.mutate(form, {
      onSuccess: () => {
        setForm(INITIAL_FORM);
        setShowModal(false);
      },
    });
  };

  const columns: Column<DealClient>[] = [
    {
      key: "display_name",
      header: "이름",
      render: (row) => (
        <span className="font-medium text-text-dark">{row.display_name}</span>
      ),
    },
    { key: "email", header: "이메일" },
    {
      key: "organization",
      header: "소속",
      render: (row) => row.organization || "—",
    },
    {
      key: "created_at",
      header: "배정일",
      align: "center" as const,
      width: "120px",
      render: (row) => formatDate(row.created_at),
    },
    {
      key: "actions" as keyof DealClient,
      header: "",
      width: "50px",
      align: "center" as const,
      render: (row) => (
        <Button
          variant="ghost"
          size="sm"
          icon={Trash2}
          onClick={(e) => {
            e.stopPropagation();
            removeClient.mutate(row.id);
          }}
          aria-label={`${row.display_name} 배정 해제`}
        />
      ),
    },
  ];

  return (
    <>
      <Card
        title="고객 접근 관리"
        headerBar
        padding="none"
        actions={
          <Button
            icon={UserPlus}
            size="sm"
            onClick={() => setShowModal(true)}
            variant="ghost"
          >
            고객 배정
          </Button>
        }
      >
        {!isLoading && (!clients || clients.length === 0) ? (
          <EmptyState
            icon={Building2}
            title="배정된 고객 없음"
            description="이 거래에 접근할 외부 고객을 배정하세요. 배정된 고객은 CLIENT 계정으로 로그인 시 이 거래만 열람할 수 있습니다."
          />
        ) : (
          <DataTable
            columns={columns}
            data={clients ?? []}
            keyField="id"
            loading={isLoading}
            striped
          />
        )}
      </Card>

      <Modal
        open={showModal}
        onClose={() => setShowModal(false)}
        title="고객 배정"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowModal(false)}>
              취소
            </Button>
            <Button
              variant="accent"
              onClick={handleAdd}
              loading={addClient.isPending}
            >
              배정
            </Button>
          </>
        }
      >
        <form onSubmit={handleAdd} className="space-y-4">
          <Input
            label="이메일"
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="client@company.com"
          />
          <Input
            label="이름"
            required
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            placeholder="홍길동"
          />
          <Input
            label="소속 (선택)"
            value={form.organization ?? ""}
            onChange={(e) => setForm({ ...form, organization: e.target.value })}
            placeholder="삼성전자"
          />
        </form>
      </Modal>
    </>
  );
}
