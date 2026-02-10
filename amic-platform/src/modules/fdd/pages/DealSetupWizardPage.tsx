import DealSetupWizard from "@/modules/fdd/components/deal/DealSetupWizard";

export default function DealSetupWizardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold text-text-dark">
          Create New Deal
        </h1>
        <p className="text-text-secondary mt-1">
          Set up a new FDD deal by following the wizard steps.
        </p>
      </div>
      <DealSetupWizard />
    </div>
  );
}
