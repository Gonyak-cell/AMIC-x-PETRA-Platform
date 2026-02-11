import { UserPlus, X } from "lucide-react";
import { useState } from "react";
import { Select, Button, Badge } from "@/components/ui";
import type { SelectOption } from "@/components/ui";
import type { TeamMember, TeamAssignmentData } from "@/types/collaboration";

interface TeamAssignmentProps {
  assignment: TeamAssignmentData;
  partners: TeamMember[];
  managers: TeamMember[];
  analysts: TeamMember[];
  allMembers: TeamMember[];
  onUpdate: (assignment: Partial<TeamAssignmentData>) => void;
  isUpdating?: boolean;
}

function memberToOption(member: TeamMember): SelectOption {
  return { value: member.user_id, label: `${member.display_name} (${member.role})` };
}

function MemberSlot({
  label,
  memberId,
  candidates,
  onSelect,
  onClear,
}: {
  label: string;
  memberId: string | null;
  candidates: TeamMember[];
  onSelect: (userId: string) => void;
  onClear: () => void;
}) {
  const selected = candidates.find((c) => c.user_id === memberId);
  const options: SelectOption[] = [
    { value: "", label: "Select..." },
    ...candidates.map(memberToOption),
  ];

  return (
    <div>
      <label className="text-xs font-heading font-semibold text-text-dark mb-1 block">
        {label}
      </label>
      {selected ? (
        <div className="flex items-center gap-2 p-2 bg-bg-cool rounded-lg border border-gray-border">
          <div className="w-7 h-7 bg-amic rounded-full flex items-center justify-center">
            <span className="text-white text-xs font-medium">
              {selected.display_name.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-text-dark truncate">
              {selected.display_name}
            </div>
            <Badge variant="neutral" className="text-[10px]">
              {selected.role}
            </Badge>
          </div>
          <button
            onClick={onClear}
            className="p-1 text-text-secondary hover:text-negative transition-colors"
            aria-label={`Remove ${selected.display_name}`}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <Select
          value=""
          onChange={(e) => {
            if (e.target.value) onSelect(e.target.value);
          }}
          options={options}
        />
      )}
    </div>
  );
}

export function TeamAssignment({
  assignment,
  partners,
  managers,
  analysts,
  allMembers,
  onUpdate,
  isUpdating,
}: TeamAssignmentProps) {
  const [analystInput, setAnalystInput] = useState("");

  const assignedAnalysts = assignment.analysts
    .map((id) => allMembers.find((m) => m.user_id === id))
    .filter(Boolean) as TeamMember[];

  const availableAnalysts = analysts.filter(
    (a) => !assignment.analysts.includes(a.user_id),
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <MemberSlot
          label="Partner"
          memberId={assignment.partner_id}
          candidates={partners}
          onSelect={(userId) => onUpdate({ partner_id: userId })}
          onClear={() => onUpdate({ partner_id: null })}
        />
        <MemberSlot
          label="Manager"
          memberId={assignment.manager_id}
          candidates={managers}
          onSelect={(userId) => onUpdate({ manager_id: userId })}
          onClear={() => onUpdate({ manager_id: null })}
        />
      </div>

      {/* Analysts (multiple) */}
      <div>
        <label className="text-xs font-heading font-semibold text-text-dark mb-1 block">
          Analysts
        </label>

        {assignedAnalysts.length > 0 && (
          <div className="space-y-2 mb-2">
            {assignedAnalysts.map((analyst) => (
              <div
                key={analyst.user_id}
                className="flex items-center gap-2 p-2 bg-bg-cool rounded-lg border border-gray-border"
              >
                <div className="w-7 h-7 bg-amic rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-medium">
                    {analyst.display_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="flex-1 text-sm text-text-dark truncate">
                  {analyst.display_name}
                </span>
                <button
                  onClick={() =>
                    onUpdate({
                      analysts: assignment.analysts.filter(
                        (id) => id !== analyst.user_id,
                      ),
                    })
                  }
                  className="p-1 text-text-secondary hover:text-negative transition-colors"
                  aria-label={`Remove ${analyst.display_name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {availableAnalysts.length > 0 && (
          <div className="flex gap-2">
            <div className="flex-1">
              <Select
                value={analystInput}
                onChange={(e) => setAnalystInput(e.target.value)}
                options={[
                  { value: "", label: "Add analyst..." },
                  ...availableAnalysts.map(memberToOption),
                ]}
              />
            </div>
            <Button
              variant="ghost"
              size="sm"
              icon={UserPlus}
              disabled={!analystInput || isUpdating}
              onClick={() => {
                if (analystInput) {
                  onUpdate({
                    analysts: [...assignment.analysts, analystInput],
                  });
                  setAnalystInput("");
                }
              }}
            >
              Add
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
