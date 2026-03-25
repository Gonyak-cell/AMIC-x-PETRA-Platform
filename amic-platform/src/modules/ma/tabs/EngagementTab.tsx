import { useRef, useState } from "react";
import { Pencil, Plus, Upload, Users } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import FileUploadZone from "@/modules/ma/components/FileUploadZone";
import ExtractionReviewModal from "@/modules/ma/components/extraction/ExtractionReviewModal";
import { useAttachmentExtractionFlow } from "@/modules/ma/hooks/useAttachmentExtractionFlow";
import {
  useEngagements,
  useCreateEngagement,
  useWorkingGroup,
  useAddMember,
  useUpdateMember,
} from "@/modules/ma/hooks/useTransactions";
import type {
  EngagementCreate,
  WorkingGroupMember,
  WorkingGroupMemberCreate,
  WorkingGroupMemberUpdate,
  WorkingGroupRole,
} from "@/modules/ma/types/engagement";
import {
  ENGAGEMENT_TYPE_OPTIONS,
  WORKING_GROUP_ROLE_OPTIONS,
} from "@/modules/ma/constants";
import ClientNdaSection from "@/modules/ma/components/engagement/ClientNdaSection";

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

interface MemberEditFormState {
  name: string;
  organization: string;
  role: WorkingGroupRole;
  phone: string;
}

const WORKING_GROUP_MANAGER_ROLES = new Set(["ADMIN", "MANAGER"]);

function normalizePersonName(value: string | undefined) {
  return value?.trim().replace(/\s+/g, " ").toLowerCase() ?? "";
}

function toOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function createEmptyMemberForm(): WorkingGroupMemberCreate {
  return {
    name: "",
    email: "",
    role: "LEAD_ADVISOR",
  };
}

function createMemberEditForm(member: WorkingGroupMember): MemberEditFormState {
  return {
    name: member.name,
    organization: member.organization ?? "",
    role: member.role,
    phone: member.phone ?? "",
  };
}

export default function EngagementTab({ txnId, canWrite }: EngagementTabProps) {
  const { user } = useAuth();
  const { data: engagements } = useEngagements(txnId);
  const { data: members } = useWorkingGroup(txnId);
  const { activeReview, closeReview, startExtractionFromUpload } =
    useAttachmentExtractionFlow(txnId);
  const createEngagement = useCreateEngagement(txnId);
  const addMember = useAddMember(txnId);
  const updateMember = useUpdateMember(txnId);

  const [showEngModal, setShowEngModal] = useState(false);
  const [showMemberModal, setShowMemberModal] = useState(false);
  const [editingMember, setEditingMember] = useState<WorkingGroupMember | null>(
    null,
  );
  const [engForm, setEngForm] = useState<EngagementCreate>({
    type: "EXCLUSIVE",
  });
  const [memberForm, setMemberForm] = useState<WorkingGroupMemberCreate>(
    createEmptyMemberForm(),
  );
  const [memberEditForm, setMemberEditForm] = useState<MemberEditFormState>({
    name: "",
    organization: "",
    role: "LEAD_ADVISOR",
    phone: "",
  });
  const openEngagementUploadPickerRef = useRef<(() => void) | null>(null);

  const canManageWorkingGroup = user
    ? WORKING_GROUP_MANAGER_ROLES.has(user.role)
    : false;

  const isOwnWorkingGroupMember = (member: WorkingGroupMember) => {
    if (!user) return false;

    if (user.email.trim().toLowerCase() === member.email.trim().toLowerCase()) {
      return true;
    }

    return (
      normalizePersonName(user.display_name) === normalizePersonName(member.name)
    );
  };

  const canEditWorkingGroupMember = (member: WorkingGroupMember) =>
    canManageWorkingGroup || isOwnWorkingGroupMember(member);
  const hasEngagements = Boolean(engagements?.length);
  const showMemberActions = Boolean(
    members?.some((member) => canEditWorkingGroupMember(member)),
  );

  const handleOpenMemberEditor = (member: WorkingGroupMember) => {
    setEditingMember(member);
    setMemberEditForm(createMemberEditForm(member));
  };

  const handleCloseMemberEditor = () => {
    setEditingMember(null);
  };

  const memberColumns: Column<WorkingGroupMember>[] = [
    { key: "name", header: "이름" },
    {
      key: "role",
      header: "역할",
      render: (row) =>
        WORKING_GROUP_ROLE_OPTIONS.find((option) => option.value === row.role)
          ?.label ?? row.role,
    },
    { key: "organization", header: "소속" },
    { key: "email", header: "이메일" },
  ];

  if (showMemberActions) {
    memberColumns.push({
      key: "actions",
      header: "관리",
      align: "right",
      width: "120px",
      render: (row) =>
        canEditWorkingGroupMember(row) ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            icon={Pencil}
            aria-label={`${row.name} 수정`}
            onClick={() => handleOpenMemberEditor(row)}
          >
            수정
          </Button>
        ) : null,
    });
  }

  return (
    <>
      <div className="space-y-6">
        <Card
          title="계약"
          headerBar
          padding="none"
          actions={
            <div className="flex flex-wrap items-center justify-end gap-1">
              <Button
                icon={Upload}
                size="sm"
                onClick={() => openEngagementUploadPickerRef.current?.()}
                variant="ghost"
              >
                계약 업로드
              </Button>
              {canWrite ? (
                <Button
                  icon={Plus}
                  size="sm"
                  onClick={() => setShowEngModal(true)}
                  variant="ghost"
                >
                  계약 추가
                </Button>
              ) : null}
            </div>
          }
        >
          {hasEngagements ? (
            <DataTable
              columns={[
                {
                  key: "type",
                  header: "유형",
                  render: (row) => (
                    <Badge variant="info">
                      {ENGAGEMENT_TYPE_OPTIONS.find(
                        (option) => option.value === row.type,
                      )?.label ?? row.type}
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
          ) : null}

          <FileUploadZone
            txnId={txnId}
            entityType="ENGAGEMENT"
            embedded
            embeddedLabel={hasEngagements ? "Engagement Files" : "Engagement Upload"}
            uploadLabel="Upload Files"
            emptyDescription="Drop the engagement contract PDF here to run OCR and prefill the review form."
            emptyHint="OCR runs for PDF uploads after VDR sync completes. Non-PDF files stay attached without auto-fill."
            embeddedSeparator={hasEngagements}
            showUploadAction={false}
            registerOpenPicker={(openPicker) => {
              openEngagementUploadPickerRef.current = openPicker;
            }}
            onUploaded={(attachment, file) =>
              startExtractionFromUpload({
                attachment,
                file,
                docCategoryHint: "ENGAGEMENT_CONTRACT",
                reviewContext: { source: "engagement" },
              })
            }
          />
        </Card>

        <ClientNdaSection txnId={txnId} canWrite={canWrite} />

        <Card
          title="Working Group List"
          headerBar
          padding="none"
          actions={
            canManageWorkingGroup ? (
              <Button
                size="sm"
                variant="ghost"
                icon={Plus}
                onClick={() => setShowMemberModal(true)}
              >
                멤버 추가
              </Button>
            ) : undefined
          }
        >
          {members && members.length > 0 ? (
            <DataTable columns={memberColumns} data={members} keyField="id" />
          ) : (
            <EmptyState
              icon={Users}
              title="등록된 멤버가 없습니다"
              description={
                canManageWorkingGroup
                  ? "워킹 그룹 멤버를 추가하세요."
                  : "워킹 그룹 멤버가 등록되면 여기에서 확인할 수 있습니다."
              }
            />
          )}
        </Card>
      </div>

      <Modal
        open={showEngModal}
        onClose={() => setShowEngModal(false)}
        title="계약 추가"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
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
            onChange={(event) =>
              setEngForm({
                ...engForm,
                type: event.target.value as EngagementCreate["type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="체결일"
              type="date"
              value={engForm.signed_at ?? ""}
              onChange={(event) =>
                setEngForm({
                  ...engForm,
                  signed_at: event.target.value || undefined,
                })
              }
            />
            <Input
              label="만료일"
              type="date"
              value={engForm.expires_at ?? ""}
              onChange={(event) =>
                setEngForm({
                  ...engForm,
                  expires_at: event.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="비고"
            value={engForm.notes ?? ""}
            onChange={(event) =>
              setEngForm({
                ...engForm,
                notes: event.target.value || undefined,
              })
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

      <Modal
        open={showMemberModal}
        onClose={() => setShowMemberModal(false)}
        title="멤버 추가"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            addMember.mutate(memberForm, {
              onSuccess: () => {
                setShowMemberModal(false);
                setMemberForm(createEmptyMemberForm());
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
              onChange={(event) =>
                setMemberForm({ ...memberForm, name: event.target.value })
              }
            />
            <Input
              label="이메일"
              type="email"
              required
              value={memberForm.email}
              onChange={(event) =>
                setMemberForm({ ...memberForm, email: event.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="소속"
              value={memberForm.organization ?? ""}
              onChange={(event) =>
                setMemberForm({
                  ...memberForm,
                  organization: event.target.value || undefined,
                })
              }
            />
            <Select
              label="역할"
              options={WORKING_GROUP_ROLE_OPTIONS}
              value={memberForm.role}
              onChange={(event) =>
                setMemberForm({
                  ...memberForm,
                  role: event.target.value as WorkingGroupMemberCreate["role"],
                })
              }
            />
          </div>
          <Input
            label="전화"
            value={memberForm.phone ?? ""}
            onChange={(event) =>
              setMemberForm({
                ...memberForm,
                phone: event.target.value || undefined,
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

      <ExtractionReviewModal
        txnId={txnId}
        extraction={activeReview?.extraction ?? null}
        reviewContext={activeReview?.context}
        open={activeReview !== null}
        onClose={closeReview}
      />

      <Modal
        open={Boolean(editingMember)}
        onClose={handleCloseMemberEditor}
        title={canManageWorkingGroup ? "멤버 수정" : "내 정보 수정"}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!editingMember) return;

            const updateBody: WorkingGroupMemberUpdate = canManageWorkingGroup
              ? {
                  name: memberEditForm.name.trim(),
                  organization: toOptionalText(memberEditForm.organization),
                  role: memberEditForm.role,
                  phone: toOptionalText(memberEditForm.phone),
                }
              : {
                  organization: toOptionalText(memberEditForm.organization),
                  phone: toOptionalText(memberEditForm.phone),
                };

            updateMember.mutate(
              {
                memberId: editingMember.id,
                body: updateBody,
              },
              {
                onSuccess: () => {
                  handleCloseMemberEditor();
                },
              },
            );
          }}
          className="space-y-4"
        >
          {!canManageWorkingGroup && (
            <p className="rounded-dr-sm bg-bg-cool px-3 py-2 text-sm text-text-secondary">
              본인 항목에서는 소속과 연락처만 수정할 수 있습니다.
            </p>
          )}

          {canManageWorkingGroup && (
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="이름"
                required
                value={memberEditForm.name}
                onChange={(event) =>
                  setMemberEditForm({
                    ...memberEditForm,
                    name: event.target.value,
                  })
                }
              />
              <Select
                label="역할"
                options={WORKING_GROUP_ROLE_OPTIONS}
                value={memberEditForm.role}
                onChange={(event) =>
                  setMemberEditForm({
                    ...memberEditForm,
                    role: event.target.value as WorkingGroupRole,
                  })
                }
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="소속"
              value={memberEditForm.organization}
              onChange={(event) =>
                setMemberEditForm({
                  ...memberEditForm,
                  organization: event.target.value,
                })
              }
            />
            <Input
              label="전화"
              value={memberEditForm.phone}
              onChange={(event) =>
                setMemberEditForm({
                  ...memberEditForm,
                  phone: event.target.value,
                })
              }
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={handleCloseMemberEditor}
            >
              취소
            </Button>
            <Button type="submit" loading={updateMember.isPending}>
              저장
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
