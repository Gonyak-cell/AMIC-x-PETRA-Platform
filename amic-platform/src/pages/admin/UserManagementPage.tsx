import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Users,
  ShieldCheck,
  UserCheck,
  Eye,
  Building2,
  Plus,
  Pencil,
  Trash2,
  Briefcase,
  Info,
  X,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import {
  useUsers,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
} from "@/hooks/useUsers";
import {
  useClientDeals,
  useAdminAssignDeal,
  useAdminUnassignDeal,
} from "@/hooks/useClientDeals";
import type { ClientDealAssignment } from "@/hooks/useClientDeals";
import { useTransactions } from "@/modules/ma/hooks/useTransactions";
import { useCreateInvite } from "@/hooks/useInvite";
import { maApi } from "@/api/maClient";
import type { AdminUser, UserCreate, UserUpdate } from "@/types/admin";
import type { UserRole } from "@/types/auth";
import { ROLE_PERMISSIONS } from "@/types/auth";
import {
  Button,
  Card,
  KpiCard,
  DataTable,
  Modal,
  Input,
  Select,
  Badge,
  EmptyState,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { formatDate } from "@/lib/format";

const ROLE_OPTIONS = [
  { value: "ADMIN", label: "Admin" },
  { value: "MANAGER", label: "Manager" },
  { value: "ANALYST", label: "Analyst" },
  { value: "VIEWER", label: "Viewer" },
  { value: "CLIENT", label: "Client (External)" },
];

const INITIAL_CREATE_FORM: UserCreate = {
  email: "",
  display_name: "",
  password: "",
  role: "ANALYST",
  title: "",
};

const ALL_PERMISSIONS = [
  "deal:create",
  "deal:read",
  "deal:read_assigned",
  "deal:update",
  "deal:delete",
  "definition:approve",
  "upload:create",
  "mapping:approve",
  "report:generate",
  "report:download",
  "audit:view",
  "user:manage",
  "user:delete",
] as const;

// ── CLIENT 배정 딜 섹션 (Edit Modal 내부) ──────────────────────

function ClientDealAssignments({
  email,
  displayName,
}: {
  email: string;
  displayName: string;
}) {
  const { data: deals, isLoading } = useClientDeals(email);
  const { data: txnList } = useTransactions({ limit: 100 });
  const assignDeal = useAdminAssignDeal(email);
  const unassignDeal = useAdminUnassignDeal(email);
  const [selectedTxnId, setSelectedTxnId] = useState("");

  const assignedIds = new Set(deals?.map((d) => d.transaction_id) ?? []);
  const txnOptions = [
    { value: "", label: "거래를 선택하세요..." },
    ...(txnList?.items ?? [])
      .filter((t) => !assignedIds.has(t.id))
      .map((t) => ({ value: t.id, label: `${t.name} (${t.code_name})` })),
  ];

  const handleAssign = () => {
    if (!selectedTxnId) return;
    assignDeal.mutate(
      { txnId: selectedTxnId, display_name: displayName },
      { onSuccess: () => setSelectedTxnId("") },
    );
  };

  const handleRemove = (deal: ClientDealAssignment) => {
    unassignDeal.mutate({
      txnId: deal.transaction_id,
      clientId: deal.id,
    });
  };

  if (isLoading) {
    return (
      <div className="text-sm text-text-secondary py-2">
        Loading assigned deals...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Briefcase size={14} className="text-text-secondary" />
        <span className="text-sm font-medium text-text-dark">
          Assigned Deals ({deals?.length ?? 0})
        </span>
      </div>

      {!deals || deals.length === 0 ? (
        <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <p>
            배정된 딜이 없습니다. 이 클라이언트는 어떤 딜도 열람할 수 없습니다.
          </p>
        </div>
      ) : (
        <div className="rounded border border-amic-200 bg-amic-50/50 divide-y divide-amic-100">
          {deals.map((d) => (
            <div
              key={d.transaction_id}
              className="flex items-center justify-between px-3 py-2 text-sm"
            >
              <div>
                <span className="font-medium text-text-dark">
                  {d.transaction_name}
                </span>
                {d.codename && (
                  <span className="ml-2 text-xs text-text-secondary">
                    ({d.codename})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-secondary">
                  {formatDate(d.created_at)}
                </span>
                <button
                  type="button"
                  className="rounded p-1 text-red-500 hover:bg-red-50 transition-colors"
                  onClick={() => handleRemove(d)}
                  disabled={unassignDeal.isPending}
                  aria-label={`${d.transaction_name} 배정 해제`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 새 딜 배정 */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Select
            label="딜 배정"
            options={txnOptions}
            value={selectedTxnId}
            onChange={(e) => setSelectedTxnId(e.target.value)}
          />
        </div>
        <Button
          variant="accent"
          size="sm"
          icon={Plus}
          onClick={handleAssign}
          disabled={!selectedTxnId || assignDeal.isPending}
          loading={assignDeal.isPending}
        >
          배정
        </Button>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────

export default function UserManagementPage() {
  const { user: currentUser, hasPermission } = useAuth();
  const { data: users, isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const deleteUser = useDeleteUser();
  const createInvite = useCreateInvite();
  const queryClient = useQueryClient();
  const { data: txnList } = useTransactions({ limit: 100 });

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [deletingUser, setDeletingUser] = useState<AdminUser | null>(null);
  const [createForm, setCreateForm] = useState<UserCreate>(INITIAL_CREATE_FORM);
  const [editForm, setEditForm] = useState<UserUpdate>({});
  const [selectedTxnIds, setSelectedTxnIds] = useState<string[]>([]);
  const [clientOrg, setClientOrg] = useState("");
  const [selectedTxnId, setSelectedTxnId] = useState("");

  // KPI calculations (must be before early return to satisfy hooks rules)
  const kpis = useMemo(() => {
    if (!users)
      return { total: 0, admins: 0, managers: 0, others: 0, clients: 0 };
    return {
      total: users.length,
      admins: users.filter((u) => u.role === "ADMIN").length,
      managers: users.filter((u) => u.role === "MANAGER").length,
      others: users.filter((u) => u.role === "ANALYST" || u.role === "VIEWER")
        .length,
      clients: users.filter((u) => u.role === "CLIENT").length,
    };
  }, [users]);

  // Access guard
  if (!hasPermission("user:manage")) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="Access Denied"
        description="You don't have permission to manage users. Contact your administrator."
      />
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (createForm.role === "CLIENT") {
      // 1. 거래 배정 먼저 (deal-mgmt)
      const assignResults: { txnId: string; ok: boolean; reason?: string }[] =
        [];
      for (const txnId of selectedTxnIds) {
        try {
          await maApi.post(`/transactions/${txnId}/clients`, {
            email: createForm.email,
            display_name: createForm.display_name,
            organization: clientOrg || undefined,
          });
          assignResults.push({ txnId, ok: true });
        } catch (err: unknown) {
          const status = (err as { response?: { status?: number } })?.response
            ?.status;
          assignResults.push({
            txnId,
            ok: false,
            reason: status === 409 ? "이미 배정됨" : "배정 실패",
          });
        }
      }

      const assignedOk = assignResults.filter((r) => r.ok).length;
      if (
        selectedTxnIds.length > 0 &&
        assignedOk === 0 &&
        assignResults.every((r) => r.reason !== "이미 배정됨")
      ) {
        alert("거래 배정에 실패했습니다.");
        return;
      }

      // 2. 초대 생성 (FDD) — 거래 배정 성공 후
      const txnNames = selectedTxnIds.map(
        (id) => txnList?.items?.find((t) => t.id === id)?.name ?? "",
      );
      await createInvite.mutateAsync({
        email: createForm.email,
        display_name: createForm.display_name,
        title: createForm.title,
        transaction_ids: selectedTxnIds,
        transaction_names: txnNames,
      });

      // 3. 완료 처리
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setCreateForm(INITIAL_CREATE_FORM);
      setSelectedTxnIds([]);
      setClientOrg("");
      setSelectedTxnId("");
      setShowCreateModal(false);
    } else {
      createUser.mutate(createForm, {
        onSuccess: () => {
          setCreateForm(INITIAL_CREATE_FORM);
          setShowCreateModal(false);
        },
      });
    }
  };

  const handleEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    updateUser.mutate(
      { userId: editingUser.id, body: editForm },
      {
        onSuccess: () => {
          setEditingUser(null);
          setEditForm({});
        },
      },
    );
  };

  const handleDelete = () => {
    if (!deletingUser) return;
    deleteUser.mutate(deletingUser.id, {
      onSuccess: () => setDeletingUser(null),
    });
  };

  const openEditModal = (user: AdminUser) => {
    setEditingUser(user);
    setEditForm({
      display_name: user.display_name,
      title: user.title,
      role: user.role,
      is_active: user.is_active,
    });
  };

  const columns: Column<AdminUser>[] = [
    {
      key: "display_name",
      header: "Name",
      render: (row) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-amic-100 flex items-center justify-center text-sm font-medium text-amic">
            {row.display_name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </div>
          <span className="font-medium text-text-dark">{row.display_name}</span>
        </div>
      ),
    },
    {
      key: "email",
      header: "Email",
    },
    {
      key: "title",
      header: "Title",
      width: "120px",
    },
    {
      key: "role",
      header: "Role",
      align: "center",
      width: "100px",
      render: (row) => <Badge variant="neutral">{row.role}</Badge>,
    },
    {
      key: "is_active",
      header: "Status",
      align: "center",
      width: "100px",
      render: (row) => {
        if (row.role === "CLIENT" && !row.is_active) {
          return <Badge variant="warning">대기 중</Badge>;
        }
        return (
          <Badge variant={row.is_active ? "success" : "error"}>
            {row.is_active ? "Active" : "Inactive"}
          </Badge>
        );
      },
    },
    {
      key: "created_at",
      header: "Created",
      align: "center",
      width: "120px",
      render: (row) => formatDate(row.created_at),
    },
    {
      key: "actions" as keyof AdminUser,
      header: "",
      width: hasPermission("user:delete") ? "100px" : "60px",
      align: "center",
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            icon={Pencil}
            onClick={(e) => {
              e.stopPropagation();
              openEditModal(row);
            }}
            aria-label={`Edit ${row.display_name}`}
          />
          {hasPermission("user:delete") && row.id !== currentUser?.id && (
            <Button
              variant="ghost"
              size="sm"
              icon={Trash2}
              className="text-negative hover:bg-negative-light"
              onClick={(e) => {
                e.stopPropagation();
                setDeletingUser(row);
              }}
              aria-label={`Delete ${row.display_name}`}
            />
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          User Management
        </h1>
        <Button
          variant="accent"
          icon={Plus}
          onClick={() => setShowCreateModal(true)}
        >
          Create User
        </Button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          label="Total Users"
          value={String(kpis.total)}
          icon={Users}
          hoverLift
          generous
        />
        <KpiCard
          label="Admins"
          value={String(kpis.admins)}
          icon={ShieldCheck}
          variant="positive"
          hoverLift
          generous
        />
        <KpiCard
          label="Managers"
          value={String(kpis.managers)}
          icon={UserCheck}
          hoverLift
          generous
        />
        <KpiCard
          label="Analysts & Viewers"
          value={String(kpis.others)}
          icon={Eye}
          hoverLift
          generous
        />
        <KpiCard
          label="Clients"
          value={String(kpis.clients)}
          icon={Building2}
          hoverLift
          generous
        />
      </div>

      {/* User Table */}
      <Card title="All Users" headerBar padding="none">
        {!isLoading && (!users || users.length === 0) ? (
          <EmptyState
            icon={Users}
            title="No users found"
            description="Create your first user to get started."
            actionLabel="Create User"
            onAction={() => setShowCreateModal(true)}
          />
        ) : (
          <DataTable
            columns={columns}
            data={users ?? []}
            keyField="id"
            loading={isLoading}
            striped
            borderless
          />
        )}
      </Card>

      {/* Role-Permission Matrix */}
      <Card title="Role-Permission Matrix" headerBar>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-medium text-text-secondary">
                  Permission
                </th>
                {ROLE_OPTIONS.map((r) => (
                  <th
                    key={r.value}
                    className="text-center py-2 px-3 font-medium text-text-secondary"
                  >
                    {r.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ALL_PERMISSIONS.map((perm) => (
                <tr key={perm} className="border-b last:border-0">
                  <td className="py-2 px-3 font-mono text-xs">{perm}</td>
                  {ROLE_OPTIONS.map((r) => (
                    <td key={r.value} className="text-center py-2 px-3">
                      {ROLE_PERMISSIONS[r.value as UserRole].has(perm) ? (
                        <span className="text-positive font-bold">
                          &#10003;
                        </span>
                      ) : (
                        <span className="text-text-secondary">&#8212;</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Create User Modal */}
      <Modal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New User"
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              onClick={handleCreate}
              loading={createUser.isPending || createInvite.isPending}
            >
              {createForm.role === "CLIENT" ? "초대 발송" : "Create User"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Email"
            type="email"
            required
            value={createForm.email}
            onChange={(e) =>
              setCreateForm({ ...createForm, email: e.target.value })
            }
            placeholder="user@example.com"
          />
          <Input
            label="Display Name"
            required
            value={createForm.display_name}
            onChange={(e) =>
              setCreateForm({ ...createForm, display_name: e.target.value })
            }
            placeholder="John Doe"
          />
          <Input
            label="Title"
            value={createForm.title ?? ""}
            onChange={(e) =>
              setCreateForm({ ...createForm, title: e.target.value })
            }
            placeholder="e.g., Associate, VP, Director"
          />
          {createForm.role !== "CLIENT" && (
            <Input
              label="Password"
              type="password"
              required
              minLength={8}
              value={createForm.password}
              onChange={(e) =>
                setCreateForm({ ...createForm, password: e.target.value })
              }
              placeholder="Minimum 8 characters"
            />
          )}
          <Select
            label="Role"
            options={ROLE_OPTIONS}
            value={createForm.role}
            onChange={(e) => {
              setCreateForm({
                ...createForm,
                role: e.target.value as UserRole,
              });
              // CLIENT 전환 시 상태 초기화
              if (e.target.value !== "CLIENT") {
                setSelectedTxnIds([]);
                setClientOrg("");
                setSelectedTxnId("");
              }
            }}
          />
          {createForm.role === "CLIENT" && (
            <>
              <Input
                label="소속 기관 (선택)"
                value={clientOrg}
                onChange={(e) => setClientOrg(e.target.value)}
                placeholder="e.g., ABC 자산운용"
              />

              {/* 거래 선택 */}
              <div className="space-y-2">
                <div className="flex items-end gap-2">
                  <div className="flex-1">
                    <Select
                      label="거래 배정"
                      options={[
                        { value: "", label: "거래를 선택하세요..." },
                        ...(txnList?.items ?? [])
                          .filter((t) => !selectedTxnIds.includes(t.id))
                          .map((t) => ({
                            value: t.id,
                            label: `${t.name} (${t.code_name})`,
                          })),
                      ]}
                      value={selectedTxnId}
                      onChange={(e) => setSelectedTxnId(e.target.value)}
                    />
                  </div>
                  <Button
                    variant="accent"
                    size="sm"
                    icon={Plus}
                    onClick={() => {
                      if (
                        selectedTxnId &&
                        !selectedTxnIds.includes(selectedTxnId)
                      ) {
                        setSelectedTxnIds([...selectedTxnIds, selectedTxnId]);
                        setSelectedTxnId("");
                      }
                    }}
                    disabled={!selectedTxnId}
                  >
                    추가
                  </Button>
                </div>

                {selectedTxnIds.length > 0 && (
                  <div className="rounded border border-amic-200 bg-amic-50/50 divide-y divide-amic-100">
                    {selectedTxnIds.map((id) => {
                      const txn = txnList?.items?.find((t) => t.id === id);
                      return (
                        <div
                          key={id}
                          className="flex items-center justify-between px-3 py-2 text-sm"
                        >
                          <div>
                            <span className="font-medium text-text-dark">
                              {txn?.name ?? id}
                            </span>
                            {txn?.code_name && (
                              <span className="ml-2 text-xs text-text-secondary">
                                ({txn.code_name})
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            className="rounded p-1 text-red-500 hover:bg-red-50 transition-colors"
                            onClick={() =>
                              setSelectedTxnIds(
                                selectedTxnIds.filter((tid) => tid !== id),
                              )
                            }
                            aria-label={`${txn?.name ?? id} 제거`}
                          >
                            <X size={14} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="flex gap-2 rounded border border-amic-200 bg-amic-50 p-3 text-sm text-text-body">
                <Info size={16} className="shrink-0 mt-0.5 text-amic" />
                <div>
                  <p className="font-medium text-amic mb-1">
                    Client (External) 초대
                  </p>
                  <p>
                    초대 이메일이 발송됩니다. 클라이언트는 이메일 링크를 통해
                    비밀번호를 설정하고 배정된 딜을 열람할 수 있습니다.
                  </p>
                </div>
              </div>
            </>
          )}
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={!!deletingUser}
        onClose={() => setDeletingUser(null)}
        title="Delete User"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeletingUser(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDelete}
              loading={deleteUser.isPending}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-text-body">
          Are you sure you want to delete{" "}
          <span className="font-semibold">{deletingUser?.display_name}</span>?
          This action cannot be undone.
        </p>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        open={!!editingUser}
        onClose={() => setEditingUser(null)}
        title={`Edit User: ${editingUser?.display_name ?? ""}`}
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditingUser(null)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              onClick={handleEdit}
              loading={updateUser.isPending}
            >
              Save Changes
            </Button>
          </>
        }
      >
        <form onSubmit={handleEdit} className="space-y-4">
          <Input
            label="Display Name"
            value={editForm.display_name ?? ""}
            onChange={(e) =>
              setEditForm({ ...editForm, display_name: e.target.value })
            }
          />
          <Input
            label="Title"
            value={editForm.title ?? ""}
            onChange={(e) =>
              setEditForm({ ...editForm, title: e.target.value })
            }
            placeholder="e.g., Associate, VP, Director"
          />
          <Select
            label="Role"
            options={ROLE_OPTIONS}
            value={editForm.role ?? "ANALYST"}
            onChange={(e) =>
              setEditForm({ ...editForm, role: e.target.value as UserRole })
            }
          />
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-text-dark">
              Active Status
            </label>
            <button
              type="button"
              onClick={() =>
                setEditForm({ ...editForm, is_active: !editForm.is_active })
              }
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                editForm.is_active ? "bg-positive" : "bg-gray-300"
              }`}
              role="switch"
              aria-checked={editForm.is_active}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  editForm.is_active ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
            <span className="text-sm text-text-secondary">
              {editForm.is_active ? "Active" : "Inactive"}
            </span>
          </div>

          {/* CLIENT role: Show assigned deals */}
          {editingUser?.role === "CLIENT" && (
            <ClientDealAssignments
              email={editingUser.email}
              displayName={editingUser.display_name}
            />
          )}
        </form>
      </Modal>
    </div>
  );
}
