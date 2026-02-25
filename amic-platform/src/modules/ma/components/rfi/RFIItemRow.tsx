import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { RFIItem, RFIItemPriority, RFIItemStatus } from "@/modules/ma/types/rfi";
import {
  RFI_ITEM_STATUS_LABELS,
  RFI_PRIORITY_LABELS,
  RFI_CATEGORY_LABELS,
} from "@/modules/ma/constants";

const PRIORITY_COLORS: Record<RFIItemPriority, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH: "bg-orange-100 text-orange-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  LOW: "bg-green-100 text-green-800",
};

const STATUS_COLORS: Record<RFIItemStatus, string> = {
  PENDING: "bg-gray-100 text-gray-700",
  RESPONDED: "bg-blue-100 text-blue-800",
  CLARIFICATION_NEEDED: "bg-amber-100 text-amber-800",
  ACCEPTED: "bg-emerald-100 text-emerald-800",
  NOT_APPLICABLE: "bg-gray-100 text-gray-500",
};

interface RFIItemRowProps {
  item: RFIItem;
  onRespond?: (itemId: string, response: string) => void;
  onReview?: (itemId: string, status: "ACCEPTED" | "CLARIFICATION_NEEDED", comment?: string) => void;
}

export default function RFIItemRow({ item, onRespond, onReview }: RFIItemRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [responseText, setResponseText] = useState("");
  const [reviewComment, setReviewComment] = useState("");

  return (
    <div className="border border-gray-200 rounded-lg p-4 mb-2 hover:bg-gray-50/50 transition-colors">
      {/* 헤더 행 */}
      <div className="flex items-start gap-3">
        <span className="text-sm font-mono text-gray-500 min-w-[2rem] text-right">
          {item.question_number}.
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_COLORS[item.priority]}`}>
              {RFI_PRIORITY_LABELS[item.priority]}
            </span>
            <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-700">
              {RFI_CATEGORY_LABELS[item.category]}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[item.status]}`}>
              {RFI_ITEM_STATUS_LABELS[item.status]}
            </span>
          </div>

          <button
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            className="text-sm text-left font-medium text-gray-900 hover:text-blue-700 transition-colors"
          >
            {item.question}
          </button>
        </div>
      </div>

      {/* 펼침 영역 */}
      {expanded && (
        <div className="mt-3 ml-11 space-y-3">
          {item.question_detail && (
            <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">{item.question_detail}</p>
          )}

          {/* 응답 표시 */}
          {item.response && (
            <div className="bg-blue-50 p-3 rounded">
              <p className="text-xs font-medium text-blue-800 mb-1">응답</p>
              <p className="text-sm text-gray-800">{item.response}</p>
              {item.responded_by && (
                <p className="text-xs text-gray-500 mt-1">
                  {item.responded_by} &middot; {item.responded_at?.slice(0, 10)}
                </p>
              )}
            </div>
          )}

          {/* 검토자 의견 */}
          {item.reviewer_comment && (
            <div className="bg-amber-50 p-3 rounded">
              <p className="text-xs font-medium text-amber-800 mb-1">검토 의견</p>
              <p className="text-sm text-gray-800">{item.reviewer_comment}</p>
            </div>
          )}

          {/* 후속 질문 */}
          {item.follow_up_question && (
            <div className="bg-red-50 p-3 rounded">
              <p className="text-xs font-medium text-red-800 mb-1">추가 질문</p>
              <p className="text-sm text-gray-800">{item.follow_up_question}</p>
            </div>
          )}

          {/* 응답 입력 */}
          {item.status === "PENDING" && onRespond && (
            <div className="space-y-2">
              <textarea
                className="w-full border rounded p-2 text-sm"
                rows={3}
                placeholder="응답을 입력하세요..."
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
              />
              <Button
                size="sm"
                onClick={() => {
                  if (responseText.trim()) {
                    onRespond(item.id, responseText);
                    setResponseText("");
                  }
                }}
              >
                응답 제출
              </Button>
            </div>
          )}

          {/* 검토 액션 */}
          {item.status === "RESPONDED" && onReview && (
            <div className="space-y-2">
              <textarea
                className="w-full border rounded p-2 text-sm"
                rows={2}
                placeholder="검토 의견 (선택)"
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => {
                    onReview(item.id, "ACCEPTED", reviewComment || undefined);
                    setReviewComment("");
                  }}
                >
                  확인 완료
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    onReview(item.id, "CLARIFICATION_NEEDED", reviewComment || undefined);
                    setReviewComment("");
                  }}
                >
                  추가 확인 필요
                </Button>
              </div>
            </div>
          )}

          {/* 메타 정보 */}
          <div className="flex gap-4 text-xs text-gray-500">
            {item.assignee_email && <span>담당: {item.assignee_email}</span>}
            {item.due_date && <span>마감: {item.due_date}</span>}
            {item.source_type !== "MANUAL" && <span>출처: {item.source_type}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
