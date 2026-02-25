import { useParams, Routes, Route } from "react-router-dom";
import { useDeal } from "@/modules/fdd/hooks/useDeals";
import { Spinner } from "@/components/ui";
import WorkflowOverviewPage from "./WorkflowOverviewPage";
import DealSetupPage from "./DealSetupPage";
import VdrPage from "./VdrPage";
import DefinitionPage from "./DefinitionPage";
import IssuesPage from "./IssuesPage";
import MappingPage from "./MappingPage";
import NetDebtPage from "./NetDebtPage";
import NWCPage from "./NWCPage";
import QoEPage from "./QoEPage";
import ReportPage from "./ReportPage";
import UploadPage from "./UploadPage";
import ChecklistReviewPage from "./ChecklistReviewPage";

export default function DealWorkspacePage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: deal, isLoading } = useDeal(dealId!);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!deal) {
    return (
      <div className="text-center py-12">
        <p className="text-negative">Deal not found</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route index element={<WorkflowOverviewPage />} />
      <Route path="setup" element={<DealSetupPage />} />
      <Route path="vdr" element={<VdrPage />} />
      <Route path="definitions" element={<DefinitionPage />} />
      <Route path="uploads" element={<UploadPage />} />
      <Route path="mapping" element={<MappingPage />} />
      <Route path="qoe" element={<QoEPage />} />
      <Route path="nwc" element={<NWCPage />} />
      <Route path="netdebt" element={<NetDebtPage />} />
      <Route path="issues" element={<IssuesPage />} />
      <Route path="checklist" element={<ChecklistReviewPage />} />
      <Route path="report" element={<ReportPage />} />
    </Routes>
  );
}
