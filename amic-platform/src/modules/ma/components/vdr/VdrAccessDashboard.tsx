import { useVdrAccessSummary } from "@/modules/ma/hooks/useVdrAccess";

interface Props {
  txnId: string;
}

export function VdrAccessDashboard({ txnId }: Props) {
  const { data: summaries, isLoading } = useVdrAccessSummary(txnId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-500">
        로딩 중...
      </div>
    );
  }

  if (!summaries?.length) {
    return (
      <div className="text-center py-8 text-sm text-gray-400">
        접근 기록이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-700">매수자별 VDR 활동</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-500">
                매수자
              </th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">
                조회 문서
              </th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">
                다운로드
              </th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">
                최근 접근
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {summaries.map((s) => (
              <tr key={s.buyer_id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-900">
                  {s.buyer_name}
                </td>
                <td className="px-4 py-2 text-right text-gray-600">
                  {s.unique_documents_accessed}
                </td>
                <td className="px-4 py-2 text-right text-gray-600">
                  {s.total_downloads}
                </td>
                <td className="px-4 py-2 text-right text-gray-400">
                  {s.last_access_at
                    ? new Date(s.last_access_at).toLocaleDateString("ko-KR")
                    : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
