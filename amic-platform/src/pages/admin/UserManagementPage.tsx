import { useState, useMemo } from "react";
import {
  Users,
  ShieldCheck,
  UserCheck,
  Eye,
  Plus,
  Pencil,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useUsers, useCreateUser, useUpdateUser } from "@/hooks/useUsers";
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
];

const INITIAL_CREATE_FORM: UserCreate = {
  email: "",
  display_name: "",
  password: "",
  role: "ANALYST",
};

const ALL_PERMISSIONS = [
  "deal:create",
  "deal:read",
  "deal:update",
  "deal:delete",
  "definition:approve",
  "upload:create",
  "mapping:approve",
  "report:generate",
  "report:download",
  "audit:view",
  "user:manage",
] as const;

export default function UserManagementPage() {
  const { hasPermission } = useAuth();
  const { data: users, isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [createForm, setCreateForm] = useState<UserCreate>(INITIAL_CREATE_FORM);
  const [editForm, setEditForm] = useState<UserUpdate>({});

  // KPI calculations (must be before early return to satisfy hooks rules)
  const kpis = useMemo(() => {
    if (!users) return { total: 0, admins: 0, managers: 0, others: 0 };
    return {
      total: users.length,
      admins: users.filter((u) => u.role === "ADMIN").length,
      managers: users.filter((u) => u.role === "MANAGER").length,
      others: users.filter(
        (u) => u.role === "ANALYST" || u.role === "VIEWER",
      ).length,
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

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createUser.mutate(createForm, {
      onSuccess: () => {
        setCreateForm(INITIAL_CREATE_FORM);
        setShowCreateModal(false);
      },
    });
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

  const openEditModal = (user: AdminUser) => {
    setEditingUser(user);
    setEditForm({
      display_name: user.display_name,
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
      render: (row) => (
        <Badge variant={row.is_active ? "success" : "error"}>
          {row.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
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
      width: "60px",
      align: "center",
      render: (row) => (
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
            uppercaseHeaders
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
                        <span className="text-positive font-bold">&#10003;</span>
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
              loading={createUser.isPending}
            >
              Create User
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
            label="Password"
            type="password"
            required
            value={createForm.password}
            onChange={(e) =>
              setCreateForm({ ...createForm, password: e.target.value })
            }
            placeholder="Minimum 8 characters"
          />
          <Select
            label="Role"
            options={ROLE_OPTIONS}
            value={createForm.role}
            onChange={(e) =>
              setCreateForm({
                ...createForm,
                role: e.target.value as UserRole,
              })
            }
          />
        </form>
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
        </form>
      </Modal>
    </div>
  );
}
