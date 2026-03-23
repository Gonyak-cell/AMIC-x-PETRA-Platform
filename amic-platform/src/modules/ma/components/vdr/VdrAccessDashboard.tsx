import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useVdrAccessSummary } from "@/modules/ma/hooks/useVdrAccess";

interface Props {
  txnId: string;
}

export function VdrAccessDashboard({ txnId }: Props) {
  const { data: summaries, isLoading, isError, refetch } = useVdrAccessSummary(txnId);
  const hasCachedData = summaries != null;

  if (isLoading && !hasCachedData) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-500">
        Loading access activity...
      </div>
    );
  }

  if (isError && !hasCachedData) {
    return (
      <Card padding="md" className="border border-red-200 bg-red-50">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-red-900">
                Buyer access activity could not be loaded.
              </p>
              <p className="text-sm text-red-800">
                Retry the access summary without leaving the VDR tab.
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => void refetch()}
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  if (!summaries?.length) {
    return (
      <div className="py-8 text-center text-sm text-gray-400">
        No buyer activity has been recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {isError && (
        <Card padding="sm" className="border border-amber-200 bg-amber-50">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-amber-800">
              Showing the last loaded access activity while refresh retries.
            </p>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => void refetch()}
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </Card>
      )}

      <h3 className="text-sm font-semibold text-gray-700">Buyer VDR Activity</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-gray-500">
                Buyer
              </th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">
                Documents Viewed
              </th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">
                Downloads
              </th>
              <th className="px-4 py-2 text-right font-medium text-gray-500">
                Last Access
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {summaries.map((summary) => (
              <tr key={summary.buyer_id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-900">
                  {summary.buyer_name}
                </td>
                <td className="px-4 py-2 text-right text-gray-600">
                  {summary.unique_documents_accessed}
                </td>
                <td className="px-4 py-2 text-right text-gray-600">
                  {summary.total_downloads}
                </td>
                <td className="px-4 py-2 text-right text-gray-400">
                  {summary.last_access_at
                    ? new Date(summary.last_access_at).toLocaleDateString("ko-KR")
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
