import { useState } from "react";
import { MessageSquare, Pencil, Trash2, Check, X } from "lucide-react";
import {
  useComments,
  useCreateComment,
  useUpdateComment,
  useDeleteComment,
} from "@/hooks/useComments";
import { useTeamMembers } from "@/hooks/useTeamMembers";
import { useAuth } from "@/hooks/useAuth";
import { Badge, Spinner } from "@/components/ui";
import { CommentInput } from "./CommentInput";
import type { Comment, CommentEntityType } from "@/types/collaboration";

function formatCommentTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function CommentItem({
  comment,
  isOwner,
  onEdit,
  onDelete,
}: {
  comment: Comment;
  isOwner: boolean;
  onEdit: (commentId: string, content: string) => void;
  onDelete: (commentId: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(comment.content);

  const handleSaveEdit = () => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== comment.content) {
      onEdit(comment.id, trimmed);
    }
    setEditing(false);
  };

  return (
    <div className="flex gap-3 py-3">
      {/* Avatar */}
      <div className="w-8 h-8 bg-amic rounded-full flex items-center justify-center shrink-0">
        <span className="text-white text-xs font-medium">
          {comment.author_name.charAt(0).toUpperCase()}
        </span>
      </div>

      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-sm text-text-dark">
            {comment.author_name}
          </span>
          <span className="text-xs text-text-secondary">
            {formatCommentTime(comment.created_at)}
          </span>
          {comment.is_edited && (
            <Badge variant="neutral" className="text-[10px]">
              edited
            </Badge>
          )}
        </div>

        {/* Content */}
        {editing ? (
          <div className="flex items-start gap-2">
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              rows={2}
              className="flex-1 px-3 py-2 text-sm border border-gray-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-amic/30 focus:border-amic"
              autoFocus
            />
            <button
              onClick={handleSaveEdit}
              className="p-1.5 text-positive hover:bg-bg-cool rounded transition-colors"
              aria-label="Save edit"
            >
              <Check className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setEditValue(comment.content);
              }}
              className="p-1.5 text-text-secondary hover:bg-bg-cool rounded transition-colors"
              aria-label="Cancel edit"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <p className="text-sm text-text-body whitespace-pre-wrap break-words">
            {comment.content}
          </p>
        )}

        {/* Actions (own comments only) */}
        {isOwner && !editing && (
          <div className="flex gap-1 mt-1">
            <button
              onClick={() => setEditing(true)}
              className="flex items-center gap-1 px-2 py-0.5 text-xs text-text-secondary hover:text-text-dark transition-colors rounded"
            >
              <Pencil className="h-3 w-3" />
              Edit
            </button>
            <button
              onClick={() => onDelete(comment.id)}
              className="flex items-center gap-1 px-2 py-0.5 text-xs text-text-secondary hover:text-negative transition-colors rounded"
            >
              <Trash2 className="h-3 w-3" />
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface CommentThreadProps {
  entityType: CommentEntityType;
  entityId: string;
}

export function CommentThread({ entityType, entityId }: CommentThreadProps) {
  const { user } = useAuth();
  const { data: comments = [], isLoading } = useComments(entityType, entityId);
  const createComment = useCreateComment(entityType, entityId);
  const updateComment = useUpdateComment(entityType, entityId);
  const deleteComment = useDeleteComment(entityType, entityId);
  const { members } = useTeamMembers();

  const handleSubmit = (content: string, mentions: string[]) => {
    createComment.mutate({ content, mentions });
  };

  const handleEdit = (commentId: string, content: string) => {
    updateComment.mutate({ commentId, content });
  };

  const handleDelete = (commentId: string) => {
    deleteComment.mutate(commentId);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <Spinner size="sm" />
      </div>
    );
  }

  return (
    <div>
      <h4 className="text-xs font-heading font-semibold text-text-dark mb-2 flex items-center gap-1.5">
        <MessageSquare className="h-3.5 w-3.5" />
        Comments ({comments.length})
      </h4>

      {comments.length === 0 ? (
        <div className="py-3 text-sm text-text-secondary">
          No comments yet. Be the first to add one.
        </div>
      ) : (
        <div className="divide-y divide-gray-border mb-3">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              isOwner={user?.id === comment.author_id}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <CommentInput
        teamMembers={members}
        onSubmit={handleSubmit}
        isSubmitting={createComment.isPending}
      />
    </div>
  );
}
