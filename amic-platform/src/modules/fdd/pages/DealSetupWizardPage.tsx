import { PageHero } from "@/components/ui";
import DealSetupWizard from "@/modules/fdd/components/deal/DealSetupWizard";

export default function DealSetupWizardPage() {
  return (
    <div className="space-y-6">
      <PageHero title="Create New Deal" subtitle="Set up a new FDD deal by following the wizard steps." compact />
      <DealSetupWizard />
    </div>
  );
}
