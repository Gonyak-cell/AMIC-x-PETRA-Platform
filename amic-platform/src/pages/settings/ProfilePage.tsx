import { useState } from "react";
import { User, Lock, Settings, Shield } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useUpdateProfile, useChangePassword } from "@/hooks/useProfile";
import { usePreferences } from "@/hooks/usePreferences";
import { ROLE_PERMISSIONS } from "@/types/auth";
import { Card, Input, Select, Button, Badge } from "@/components/ui";
import { formatDate } from "@/lib/format";

const MODULE_OPTIONS = [
  { value: "/", label: "Dashboard" },
  { value: "/fdd/deals", label: "Auto FDD" },
  { value: "/kiis", label: "KIIS" },
  { value: "/im", label: "IM Generator" },
];

const DATE_FORMAT_OPTIONS = [
  { value: "short", label: "MM/DD/YYYY" },
  { value: "long", label: "YYYY년 MM월 DD일" },
];

function SectionTitle({
  icon: Icon,
  children,
}: {
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <h2 className="flex items-center gap-2 text-base font-heading font-semibold text-text-dark mb-4">
      <Icon className="h-5 w-5 text-text-secondary" />
      {children}
    </h2>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const { preferences, updatePreferences } = usePreferences();

  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [passwordError, setPasswordError] = useState("");

  if (!user) return null;

  const handleSaveProfile = () => {
    updateProfile.mutate({ userId: user.id, displayName });
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");

    if (passwordForm.new_password.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("Passwords do not match");
      return;
    }

    changePassword.mutate(passwordForm, {
      onSuccess: () => {
        setPasswordForm({
          current_password: "",
          new_password: "",
          confirm_password: "",
        });
      },
    });
  };

  const userPermissions = ROLE_PERMISSIONS[user.role];

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Page Header */}
      <h1 className="text-2xl font-heading font-bold text-text-dark">
        Profile & Settings
      </h1>

      {/* Profile Section */}
      <Card>
        <SectionTitle icon={User}>Profile</SectionTitle>
        <div className="space-y-4">
          {/* Avatar + Basic Info */}
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-amic rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-xl">
                {user.display_name?.charAt(0).toUpperCase() ?? "U"}
              </span>
            </div>
            <div>
              <div className="font-medium text-text-dark">
                {user.display_name}
              </div>
              <div className="text-sm text-text-secondary">{user.email}</div>
              <Badge variant="neutral" className="mt-1">
                {user.role}
              </Badge>
            </div>
          </div>

          <div className="border-t pt-4 space-y-4">
            <Input
              label="Display Name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
            <Input label="Email" value={user.email} disabled />
            <div className="text-sm text-text-secondary">
              Member since {formatDate(user.created_at, "long")}
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              variant="accent"
              onClick={handleSaveProfile}
              loading={updateProfile.isPending}
              disabled={displayName === user.display_name}
            >
              Save Profile
            </Button>
          </div>
        </div>
      </Card>

      {/* Password Change */}
      <Card>
        <SectionTitle icon={Lock}>Change Password</SectionTitle>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <Input
            label="Current Password"
            type="password"
            required
            value={passwordForm.current_password}
            onChange={(e) =>
              setPasswordForm({
                ...passwordForm,
                current_password: e.target.value,
              })
            }
          />
          <Input
            label="New Password"
            type="password"
            required
            value={passwordForm.new_password}
            onChange={(e) =>
              setPasswordForm({
                ...passwordForm,
                new_password: e.target.value,
              })
            }
            placeholder="Minimum 8 characters"
          />
          <Input
            label="Confirm New Password"
            type="password"
            required
            value={passwordForm.confirm_password}
            onChange={(e) =>
              setPasswordForm({
                ...passwordForm,
                confirm_password: e.target.value,
              })
            }
            error={passwordError || undefined}
          />
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="accent"
              loading={changePassword.isPending}
            >
              Change Password
            </Button>
          </div>
        </form>
      </Card>

      {/* Display Preferences */}
      <Card>
        <SectionTitle icon={Settings}>Display Preferences</SectionTitle>
        <div className="space-y-4">
          <Select
            label="Default Landing Page"
            options={MODULE_OPTIONS}
            value={preferences.defaultModule}
            onChange={(e) =>
              updatePreferences({
                defaultModule: e.target.value as typeof preferences.defaultModule,
              })
            }
          />
          <Select
            label="Date Format"
            options={DATE_FORMAT_OPTIONS}
            value={preferences.dateFormat}
            onChange={(e) =>
              updatePreferences({
                dateFormat: e.target.value as "short" | "long",
              })
            }
          />
        </div>
      </Card>

      {/* Session Info / Permissions */}
      <Card>
        <SectionTitle icon={Shield}>Your Permissions</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {Array.from(userPermissions).map((perm) => (
            <Badge key={perm} variant="neutral">
              {perm}
            </Badge>
          ))}
        </div>
      </Card>
    </div>
  );
}
