import { useState } from "react";
import { Plus, Trash2, Pencil, Check, X } from "lucide-react";
import { Badge, Button, Input, Select } from "@/components/ui";
import {
  ATTENDEE_ROLE_OPTIONS,
  BUYER_REACTION_OPTIONS,
} from "@/modules/ma/constants";
import type {
  MeetingAttendee,
  MeetingAttendeeCreate,
  MeetingAttendeeUpdate,
  MeetingPhase,
} from "@/modules/ma/types/meeting_log";

interface AttendeeListProps {
  attendees: MeetingAttendee[];
  meetingPhase: MeetingPhase;
  canWrite: boolean;
  onAdd: (body: MeetingAttendeeCreate) => void;
  onUpdate?: (attId: string, body: MeetingAttendeeUpdate) => void;
  onDelete: (attendeeId: string) => void;
}

export default function AttendeeList({
  attendees,
  meetingPhase,
  canWrite,
  onAdd,
  onUpdate,
  onDelete,
}: AttendeeListProps) {
  const [name, setName] = useState("");
  const [org, setOrg] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("SELLER_ADVISOR");

  // 인라인 편집 상태
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<MeetingAttendeeUpdate>({});

  const handleAdd = () => {
    if (!name.trim()) return;
    onAdd({
      name: name.trim(),
      organization: org.trim() || undefined,
      email: email.trim() || undefined,
      role: role as MeetingAttendeeCreate["role"],
    });
    setName("");
    setOrg("");
    setEmail("");
  };

  const startEdit = (a: MeetingAttendee) => {
    setEditingId(a.id);
    setEditForm({
      name: a.name,
      organization: a.organization ?? "",
      email: a.email ?? "",
      role: a.role,
      comments: a.comments ?? "",
      reaction: a.reaction ?? undefined,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm({});
  };

  const saveEdit = () => {
    if (!editingId || !onUpdate) return;
    onUpdate(editingId, editForm);
    setEditingId(null);
    setEditForm({});
  };

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-heading font-semibold text-text-dark">
        참석자 ({attendees.length})
      </h4>
      {attendees.length === 0 && (
        <p className="text-xs text-text-muted">등록된 참석자가 없습니다.</p>
      )}
      <div className="divide-y divide-gray-border rounded-lg border border-gray-border">
        {attendees.map((a) =>
          editingId === a.id ? (
            /* ── 인라인 편집 모드 ── */
            <div key={a.id} className="px-3 py-2 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  value={editForm.name ?? ""}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  placeholder="이름"
                  className="w-28 text-sm"
                />
                <Input
                  value={editForm.organization ?? ""}
                  onChange={(e) =>
                    setEditForm((prev) => ({
                      ...prev,
                      organization: e.target.value,
                    }))
                  }
                  placeholder="소속"
                  className="w-28 text-sm"
                />
                <Input
                  value={editForm.email ?? ""}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, email: e.target.value }))
                  }
                  placeholder="이메일"
                  className="w-40 text-sm"
                />
                <Select
                  value={editForm.role ?? "SELLER_ADVISOR"}
                  onChange={(e) =>
                    setEditForm((prev) => ({
                      ...prev,
                      role: e.target.value as MeetingAttendeeUpdate["role"],
                    }))
                  }
                  options={ATTENDEE_ROLE_OPTIONS}
                  className="w-28 text-sm"
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  value={editForm.comments ?? ""}
                  onChange={(e) =>
                    setEditForm((prev) => ({
                      ...prev,
                      comments: e.target.value,
                    }))
                  }
                  placeholder="코멘트"
                  className="flex-1 min-w-[120px] text-sm"
                />
                {meetingPhase === "MARKETING" && (
                  <Select
                    value={editForm.reaction ?? ""}
                    onChange={(e) =>
                      setEditForm((prev) => ({
                        ...prev,
                        reaction:
                          (e.target
                            .value as MeetingAttendeeUpdate["reaction"]) ||
                          undefined,
                      }))
                    }
                    options={[
                      { value: "", label: "반응 없음" },
                      ...BUYER_REACTION_OPTIONS,
                    ]}
                    className="w-28 text-sm"
                  />
                )}
                <button
                  type="button"
                  className="p-1 text-green-600 hover:text-green-800"
                  onClick={saveEdit}
                >
                  <Check className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  className="p-1 text-gray-400 hover:text-gray-600"
                  onClick={cancelEdit}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ) : (
            /* ── 표시 모드 ── */
            <div key={a.id} className="flex items-center gap-3 px-3 py-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-dark truncate">
                  {a.name}
                  {a.organization && (
                    <span className="ml-1 text-text-secondary text-xs">
                      ({a.organization})
                    </span>
                  )}
                  {a.email && (
                    <span className="ml-1 text-text-muted text-xs">
                      {a.email}
                    </span>
                  )}
                </p>
                {a.comments && (
                  <p className="text-xs text-text-muted truncate">
                    {a.comments}
                  </p>
                )}
              </div>
              <Badge variant="neutral">
                {ATTENDEE_ROLE_OPTIONS.find((o) => o.value === a.role)?.label ??
                  a.role}
              </Badge>
              {meetingPhase === "MARKETING" && a.reaction && (
                <Badge
                  variant={
                    a.reaction.includes("POSITIVE")
                      ? "success"
                      : a.reaction === "NEUTRAL"
                        ? "neutral"
                        : "error"
                  }
                >
                  {BUYER_REACTION_OPTIONS.find((o) => o.value === a.reaction)
                    ?.label ?? a.reaction}
                </Badge>
              )}
              {canWrite && onUpdate && (
                <button
                  type="button"
                  className="text-gray-400 hover:text-primary-600"
                  onClick={() => startEdit(a)}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
              {canWrite && (
                <button
                  type="button"
                  className="text-red-400 hover:text-red-600"
                  onClick={() => onDelete(a.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ),
        )}
      </div>
      {canWrite && (
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="이름"
            className="w-28 text-sm"
          />
          <Input
            value={org}
            onChange={(e) => setOrg(e.target.value)}
            placeholder="소속"
            className="w-28 text-sm"
          />
          <Input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="이메일"
            className="w-40 text-sm"
          />
          <Select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            options={ATTENDEE_ROLE_OPTIONS}
            className="w-28 text-sm"
          />
          <Button
            size="sm"
            variant="ghost"
            icon={Plus}
            onClick={handleAdd}
            disabled={!name.trim()}
          >
            추가
          </Button>
        </div>
      )}
    </div>
  );
}
