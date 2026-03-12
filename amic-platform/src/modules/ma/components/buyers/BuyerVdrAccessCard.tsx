import { useVdrAccessLogs } from "@/modules/ma/hooks/useVdrAccess";

interface Props {
  txnId: string;
  buyerId: string;
}

export default function BuyerVdrAccessCard({ txnId, buyerId }: Props) {
  const { data, isLoading } = useVdrAccessLogs(txnId, {
    buyerId,
    limit: 5,
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="text-xs text-gray-400">VDR 접근 이력 로딩 중...</div>
      </div>
    );
  }

  const total = data?.total ?? 0;
  const items = data?.items ?? [];

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-500 uppercase">
          VDR 접근 이력
        </h4>
        {total > 0 && (
          <span className="text-xs text-gray-400">총 {total}건</span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-gray-400">접근 기록이 없습니다.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {items.map((log) => (
            <li
              key={log.id}
              className="flex items-center justify-between py-1.5 text-sm"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full ${
                    log.action === "DOWNLOAD"
                      ? "bg-blue-500"
                      : log.action === "UPLOAD"
                        ? "bg-green-500"
                        : "bg-gray-400"
                  }`}
                />
                <span className="text-gray-600">
                  {log.action === "VIEW"
                    ? "조회"
                    : log.action === "DOWNLOAD"
                      ? "다운로드"
                      : "업로드"}
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(log.created_at).toLocaleDateString("ko-KR")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
