import { useState } from "react";
import { Plus, Trash2, Check, Circle } from "lucide-react";
import { cn } from "@/lib/cn";
import { Badge, Button, Input } from "@/components/ui";
import {
  ACTION_ITEM_STATUS_OPTIONS,
  ACTION_ITEM_STATUS_VARIANT,
} from "@/modules/ma/constants";
import type {
  MeetingActionItem,
  MeetingActionItemCreate,
} from "@/modules/ma/types/meeting_log";

interface ActionItemListProps {
  items: MeetingActionItem[];
  canWrite: boolean;
  onAdd: (body: MeetingActionItemCreate) => void;
  onUpdate: (itemId: string, body: Partial<MeetingActionItemCreate>) => void;
  onDelete: (itemId: string) => void;
}

export default function ActionItemList({
  items,
  canWrite,
  onAdd,
  onUpdate,
  onDelete,
}: ActionItemListProps) {
  const [title, setTitle] = useState("");
  const [assignee, setAssignee] = useState("");

  const handleAdd = () => {
    if (!title.trim()) return;
    onAdd({ title: title.trim(), assignee_name: assignee.trim() || undefined });
    setTitle("");
    setAssignee("");
  };

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-heading font-semibold text-text-dark">
        액션아이템
      </h4>
      {items.length === 0 && (
        <p className="text-xs text-text-muted">등록된 액션아이템이 없습니다.</p>
      )}
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex items-center gap-2 rounded-lg border border-gray-border px-3 py-2"
          >
            <button
              type="button"
              className="shrink-0"
              disabled={!canWrite}
              onClick={() =>
                onUpdate(item.id, {
                  status: item.status === "COMPLETED" ? "PENDING" : "COMPLETED",
                })
              }
            >
              {item.status === "COMPLETED" ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Circle className="h-4 w-4 text-gray-400" />
              )}
            </button>
            <span
              className={cn(
                "flex-1 text-sm",
                item.status === "COMPLETED" && "line-through text-text-muted",
              )}
            >
              {item.title}
            </span>
            {item.assignee_name && (
              <span className="text-xs text-text-secondary">
                {item.assignee_name}
              </span>
            )}
            {item.due_date && (
              <span className="text-xs text-text-muted">
                {new Date(item.due_date).toLocaleDateString("ko-KR")}
              </span>
            )}
            <Badge variant={ACTION_ITEM_STATUS_VARIANT[item.status]}>
              {ACTION_ITEM_STATUS_OPTIONS.find((o) => o.value === item.status)
                ?.label ?? item.status}
            </Badge>
            {canWrite && (
              <button
                type="button"
                className="text-red-400 hover:text-red-600"
                onClick={() => onDelete(item.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </li>
        ))}
      </ul>
      {canWrite && (
        <div className="flex items-center gap-2 mt-2">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="새 액션아이템"
            className="flex-1 text-sm"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAdd();
              }
            }}
          />
          <Input
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            placeholder="담당자"
            className="w-28 text-sm"
          />
          <Button
            size="sm"
            variant="ghost"
            icon={Plus}
            onClick={handleAdd}
            disabled={!title.trim()}
          >
            추가
          </Button>
        </div>
      )}
    </div>
  );
}
