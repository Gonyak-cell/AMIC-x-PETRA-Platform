import { useState, useRef, useCallback, useEffect } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui";
import type { TeamMember } from "@/types/collaboration";

interface CommentInputProps {
  teamMembers: TeamMember[];
  onSubmit: (content: string, mentions: string[]) => void;
  isSubmitting?: boolean;
  placeholder?: string;
}

export function CommentInput({
  teamMembers,
  onSubmit,
  isSubmitting,
  placeholder = "Write a comment... Use @ to mention",
}: CommentInputProps) {
  const [value, setValue] = useState("");
  const [mentions, setMentions] = useState<string[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const filteredMembers = teamMembers.filter((m) =>
    m.display_name.toLowerCase().includes(mentionQuery.toLowerCase()),
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [mentionQuery]);

  const insertMention = useCallback(
    (member: TeamMember) => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const cursorPos = textarea.selectionStart;
      const textBefore = value.slice(0, cursorPos);
      const textAfter = value.slice(cursorPos);

      // Find the @ that started this mention
      const atIndex = textBefore.lastIndexOf("@");
      if (atIndex === -1) return;

      const newText =
        textBefore.slice(0, atIndex) +
        `@${member.display_name} ` +
        textAfter;

      setValue(newText);
      if (!mentions.includes(member.user_id)) {
        setMentions((prev) => [...prev, member.user_id]);
      }
      setShowDropdown(false);
      setMentionQuery("");

      // Restore focus
      requestAnimationFrame(() => {
        const newPos = atIndex + member.display_name.length + 2;
        textarea.focus();
        textarea.setSelectionRange(newPos, newPos);
      });
    },
    [value, mentions],
  );

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setValue(newValue);

    const cursorPos = e.target.selectionStart;
    const textBefore = newValue.slice(0, cursorPos);
    const atIndex = textBefore.lastIndexOf("@");

    if (atIndex !== -1 && (atIndex === 0 || textBefore[atIndex - 1] === " ")) {
      const query = textBefore.slice(atIndex + 1);
      if (!query.includes(" ")) {
        setMentionQuery(query);
        setShowDropdown(true);
        return;
      }
    }

    setShowDropdown(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showDropdown && filteredMembers.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredMembers.length - 1 ? prev + 1 : 0,
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredMembers.length - 1,
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        insertMention(filteredMembers[selectedIndex]);
      } else if (e.key === "Escape") {
        setShowDropdown(false);
      }
      return;
    }

    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed, mentions);
    setValue("");
    setMentions([]);
  };

  return (
    <div className="relative">
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={2}
            className="w-full px-3 py-2 text-sm border border-gray-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-amic/30 focus:border-amic"
          />

          {/* Mention Dropdown */}
          {showDropdown && filteredMembers.length > 0 && (
            <div className="absolute bottom-full left-0 mb-1 w-64 bg-white border border-gray-border rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
              {filteredMembers.map((member, idx) => (
                <button
                  key={member.user_id}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-bg-cool transition-colors ${
                    idx === selectedIndex ? "bg-bg-cool" : ""
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    insertMention(member);
                  }}
                >
                  <div className="w-6 h-6 bg-amic rounded-full flex items-center justify-center">
                    <span className="text-white text-[10px] font-medium">
                      {member.display_name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-text-dark truncate">
                      {member.display_name}
                    </div>
                    <div className="text-xs text-text-secondary">
                      {member.role}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <Button
          variant="accent"
          size="sm"
          icon={Send}
          onClick={handleSubmit}
          disabled={!value.trim() || isSubmitting}
          loading={isSubmitting}
          aria-label="Post comment"
        />
      </div>

      <div className="text-xs text-text-secondary mt-1">
        Press Ctrl+Enter to submit
      </div>
    </div>
  );
}
