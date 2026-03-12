import { useDocumentAccessLogs } from "@/modules/ma/hooks/useVdrAccess";

interface Props {
  txnId: string;
  docId: string;
}

const ACTION_LABELS: Record<string, string> = {
  VIEW: "조회",
  DOWNLOAD: "다운로드",
  UPLOAD: "업로드",
};

export function DocumentAccessHistory({ txnId, docId }: Props) {
  const { data, isLoading } = useDocumentAccessLogs(txnId, docId);

  if (isLoading) {
    return <div className="text-sm text-gray-500 py-4">로딩 중...</div>;
  }

  if (!data?.items.length) {
    return (
      <div className="text-sm text-gray-400 py-4">접근 기록이 없습니다.</div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-gray-500 uppercase">
        접근 이력
      </h4>
      <ul className="divide-y divide-gray-100">
        {data.items.map((log) => (
          <li
            key={log.id}
            className="flex items-center justify-between py-2 text-sm"
          >
            <div>
              <span className="font-medium text-gray-700">
                {log.user_email}
              </span>
              <span className="ml-2 text-xs text-gray-400">
                {ACTION_LABELS[log.action] ?? log.action}
              </span>
            </div>
            <span className="text-xs text-gray-400">
              {new Date(log.created_at).toLocaleString("ko-KR")}
            </span>
          </li>
        ))}
      </ul>
      {data.total > data.items.length && (
        <p className="text-xs text-gray-400 text-center">
          총 {data.total}건 중 {data.items.length}건 표시
        </p>
      )}
    </div>
  );
}
