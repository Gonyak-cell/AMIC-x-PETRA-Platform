import { useState } from "react";
import { FileText, Plus } from "lucide-react";
import {
  useEngagements,
  useCreateEngagement,
  useWorkingGroup,
  useAddMember,
} from "@/modules/ma/hooks/useTransactions";
import type { EngagementCreate } from "@/modules/ma/types/engagement";
import type { WorkingGroupMemberCreate } from "@/modules/ma/types/engagement";
import type { WorkingGroupMember } from "@/modules/ma/types/engagement";
import {
  ENGAGEMENT_TYPE_OPTIONS,
  WORKING_GROUP_ROLE_OPTIONS,
} from "@/modules/ma/constants";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Input,
  Modal,
  Select,
} from "@/components/ui";
import type { Column } from "@/components/ui";

interface EngagementTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function EngagementTab({ txnId, canWrite }: EngagementTabProps) {
  const { data: engagements } = useEngagements(txnId);
  const { data: members } = useWorkingGroup(txnId);
  const createEngagement = useCreateEngagement(txnId);
  const addMember = useAddMember(txnId);

  const [showEngModal, setShowEngModal] = useState(false);
  const [showMemberModal, setShowMemberModal] = useState(false);
  const [engForm, setEngForm] = useState<EngagementCreate>({
    type: "EXCLUSIVE",
  });
  const [memberForm, setMemberForm] = useState<WorkingGroupMemberCreate>({
    name: "",
    email: "",
    role: "LEAD_ADVISOR",
  });

  const memberColumns: Column<WorkingGroupMember>[] = [
    { key: "name", header: "이름" },
    {
      key: "role",
      header: "역할",
      render: (row) =>
        WORKING_GROUP_ROLE_OPTIONS.find((o) => o.value === row.role)?.label ||
        row.role,
    },
    { key: "organization", header: "소속" },
    { key: "email", header: "이메일" },
  ];

  return (
    <>
      <Card
        title="수임계약"
        headerBar
        padding="none"
        actions={
          canWrite ? (
            <Button
              icon={FileText}
              onClick={() => setShowEngModal(true)}
              variant="ghost"
            >
              추가
            </Button>
          ) : undefined
        }
      >
        {!engagements?.length ? (
          <EmptyState
            icon={FileText}
            title="수임계약 없음"
            description="수임계약을 등록하세요."
            actionLabel={canWrite ? "수임계약 추가" : undefined}
            onAction={canWrite ? () => setShowEngModal(true) : undefined}
          />
        ) : (
          <DataTable
            columns={[
              {
                key: "type",
                header: "유형",
                render: (r) => (
                  <Badge variant="info">
                    {ENGAGEMENT_TYPE_OPTIONS.find((o) => o.value === r.type)
                      ?.label ?? r.type}
                  </Badge>
                ),
              },
              { key: "signed_at", header: "체결일" },
              { key: "expires_at", header: "만료일" },
              { key: "notes", header: "비고" },
            ]}
            data={engagements}
            keyField="id"
          />
        )}
      </Card>

      {/* Working Group 멤버 */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-heading font-semibold text-text-dark">
            Working Group
          </h3>
          {canWrite && (
            <Button
              size="sm"
              variant="ghost"
              icon={Plus}
              onClick={() => setShowMemberModal(true)}
            >
              멤버 추가
            </Button>
          )}
        </div>
        {members && members.length > 0 ? (
          <DataTable columns={memberColumns} data={members} keyField="id" />
        ) : (
          <EmptyState
            title="등록된 멤버가 없습니다"
            description="Working Group 멤버를 추가하세요"
          />
        )}
      </Card>

      {/* Engagement 추가 모달 */}
      <Modal
        open={showEngModal}
        onClose={() => setShowEngModal(false)}
        title="수임계약 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createEngagement.mutate(engForm, {
              onSuccess: () => {
                setShowEngModal(false);
                setEngForm({ type: "EXCLUSIVE" });
              },
            });
          }}
          className="space-y-4"
        >
          <Select
            label="유형"
            options={ENGAGEMENT_TYPE_OPTIONS}
            value={engForm.type}
            onChange={(e) =>
              setEngForm({
                ...engForm,
                type: e.target.value as EngagementCreate["type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="체결일"
              type="date"
              value={engForm.signed_at ?? ""}
              onChange={(e) =>
                setEngForm({
                  ...engForm,
                  signed_at: e.target.value || undefined,
                })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={engForm.expires_at ?? ""}
              onChange={(e) =>
                setEngForm({
                  ...engForm,
                  expires_at: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="비고"
            value={engForm.notes ?? ""}
            onChange={(e) =>
              setEngForm({ ...engForm, notes: e.target.value || undefined })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowEngModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={createEngagement.isPending}>
              등록
            </Button>
          </div>
        </form>
      </Modal>

      {/* Member 추가 모달 */}
      <Modal
        open={showMemberModal}
        onClose={() => setShowMemberModal(false)}
        title="멤버 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMember.mutate(memberForm, {
              onSuccess: () => {
                setShowMemberModal(false);
                setMemberForm({ name: "", email: "", role: "LEAD_ADVISOR" });
              },
            });
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="이름"
              required
              value={memberForm.name}
              onChange={(e) =>
                setMemberForm({ ...memberForm, name: e.target.value })
              }
            />
            <Input
              label="이메일"
              type="email"
              required
              value={memberForm.email}
              onChange={(e) =>
                setMemberForm({ ...memberForm, email: e.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="소속"
              value={memberForm.organization ?? ""}
              onChange={(e) =>
                setMemberForm({
                  ...memberForm,
                  organization: e.target.value || undefined,
                })
              }
            />
            <Select
              label="역할"
              options={WORKING_GROUP_ROLE_OPTIONS}
              value={memberForm.role}
              onChange={(e) =>
                setMemberForm({
                  ...memberForm,
                  role: e.target.value as WorkingGroupMemberCreate["role"],
                })
              }
            />
          </div>
          <Input
            label="전화"
            value={memberForm.phone ?? ""}
            onChange={(e) =>
              setMemberForm({
                ...memberForm,
                phone: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowMemberModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={addMember.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
