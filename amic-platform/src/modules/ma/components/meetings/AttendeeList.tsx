import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Badge, Button, Input, Select } from "@/components/ui";
import {
  ATTENDEE_ROLE_OPTIONS,
  BUYER_REACTION_OPTIONS,
} from "@/modules/ma/constants";
import type {
  MeetingAttendee,
  MeetingAttendeeCreate,
  MeetingPhase,
} from "@/modules/ma/types/meeting_log";

interface AttendeeListProps {
  attendees: MeetingAttendee[];
  meetingPhase: MeetingPhase;
  canWrite: boolean;
  onAdd: (body: MeetingAttendeeCreate) => void;
  onDelete: (attendeeId: string) => void;
}

export default function AttendeeList({
  attendees,
  meetingPhase,
  canWrite,
  onAdd,
  onDelete,
}: AttendeeListProps) {
  const [name, setName] = useState("");
  const [org, setOrg] = useState("");
  const [role, setRole] = useState("SELLER_ADVISOR");

  const handleAdd = () => {
    if (!name.trim()) return;
    onAdd({
      name: name.trim(),
      organization: org.trim() || undefined,
      role: role as MeetingAttendeeCreate["role"],
    });
    setName("");
    setOrg("");
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
        {attendees.map((a) => (
          <div key={a.id} className="flex items-center gap-3 px-3 py-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-dark truncate">
                {a.name}
                {a.organization && (
                  <span className="ml-1 text-text-secondary text-xs">({a.organization})</span>
                )}
              </p>
              {a.comments && <p className="text-xs text-text-muted truncate">{a.comments}</p>}
            </div>
            <Badge variant="neutral">
              {ATTENDEE_ROLE_OPTIONS.find((o) => o.value === a.role)?.label ?? a.role}
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
                {BUYER_REACTION_OPTIONS.find((o) => o.value === a.reaction)?.label ?? a.reaction}
              </Badge>
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
        ))}
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
          <Select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            options={ATTENDEE_ROLE_OPTIONS}
            className="w-28 text-sm"
          />
          <Button size="sm" variant="ghost" icon={Plus} onClick={handleAdd} disabled={!name.trim()}>
            추가
          </Button>
        </div>
      )}
    </div>
  );
}
