import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { useDeal, useUpdateDeal } from "@/modules/fdd/hooks/useDeals";
import { Card, Button, Input, Spinner, PageHero } from "@/components/ui";
import ScopeSelector from "@/modules/fdd/components/deal/ScopeSelector";
import { TeamAssignment } from "@/components/collaboration/TeamAssignment";
import { useTeamMembers, useUpdateTeamAssignment } from "@/hooks/useTeamMembers";
import type { TeamAssignmentData } from "@/types/collaboration";

export default function DealSetupPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const { data: deal, isLoading } = useDeal(dealId!);
  const updateDeal = useUpdateDeal(dealId!);
  const { partners, managers, analysts, members } = useTeamMembers();
  const updateTeam = useUpdateTeamAssignment(dealId!);

  const [formData, setFormData] = useState({
    client_name: "",
    client_contact_name: "",
    client_contact_email: "",
    target_company_name: "",
    scope_qoe: true,
    scope_nwc: true,
    scope_debt: true,
  });

  useEffect(() => {
    if (deal) {
      setFormData({
        client_name: deal.client_name ?? "",
        client_contact_name: deal.client_contact_name ?? "",
        client_contact_email: deal.client_contact_email ?? "",
        target_company_name: deal.target_company_name ?? "",
        scope_qoe: deal.scope_qoe ?? true,
        scope_nwc: deal.scope_nwc ?? true,
        scope_debt: deal.scope_debt ?? true,
      });
    }
  }, [deal]);

  const updateField = <K extends keyof typeof formData>(field: K, value: (typeof formData)[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    try {
      await updateDeal.mutateAsync({
        client_name: formData.client_name || undefined,
        client_contact_name: formData.client_contact_name || undefined,
        client_contact_email: formData.client_contact_email || undefined,
        target_company_name: formData.target_company_name || undefined,
        scope_qoe: formData.scope_qoe,
        scope_nwc: formData.scope_nwc,
        scope_debt: formData.scope_debt,
      });
      toast.success("Deal updated successfully");
    } catch {
      toast.error("Failed to update deal");
    }
  };

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
    <div className="space-y-6">
      <PageHero title="Deal Setup" subtitle="Edit deal information, client details, and FDD scope." compact />

      {/* Deal Info (read-only) */}
      <Card title="Deal Information" headerBar>
        <dl className="grid grid-cols-2 md:grid-cols-3 gap-6 text-sm">
          <div>
            <dt className="text-text-secondary mb-1">Deal Name</dt>
            <dd className="font-medium text-text-dark">{deal.name}</dd>
          </div>
          <div>
            <dt className="text-text-secondary mb-1">Deal Type</dt>
            <dd className="font-medium text-text-dark">
              {deal.deal_type === "COMPLETION_ACCOUNTS" ? "Completion Accounts" : "Locked Box"}
            </dd>
          </div>
          <div>
            <dt className="text-text-secondary mb-1">Currency</dt>
            <dd className="font-medium text-text-dark">{deal.base_currency}</dd>
          </div>
        </dl>
      </Card>

      {/* Client & Target */}
      <Card title="Client & Target">
        <div className="space-y-4">
          <Input
            label="Client Name"
            value={formData.client_name}
            onChange={(e) => updateField("client_name", e.target.value)}
            placeholder="Enter client company name"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Client Contact Name"
              value={formData.client_contact_name}
              onChange={(e) => updateField("client_contact_name", e.target.value)}
              placeholder="Contact person name"
            />
            <Input
              label="Client Contact Email"
              type="email"
              value={formData.client_contact_email}
              onChange={(e) => updateField("client_contact_email", e.target.value)}
              placeholder="contact@example.com"
            />
          </div>
          <Input
            label="Target Company Name"
            value={formData.target_company_name}
            onChange={(e) => updateField("target_company_name", e.target.value)}
            placeholder="Enter target company name"
          />
        </div>
      </Card>

      {/* Team Assignment */}
      <Card title="Team">
        <TeamAssignment
          assignment={{
            partner_id: deal.team_partner_id,
            manager_id: deal.team_manager_id,
            analysts: [],
          }}
          partners={partners}
          managers={managers}
          analysts={analysts}
          allMembers={members}
          onUpdate={(update: Partial<TeamAssignmentData>) => {
            updateTeam.mutate(update);
          }}
          isUpdating={updateTeam.isPending}
        />
      </Card>

      {/* FDD Scope */}
      <Card title="FDD Scope">
        <ScopeSelector
          scopeQoe={formData.scope_qoe}
          scopeNwc={formData.scope_nwc}
          scopeDebt={formData.scope_debt}
          onScopeChange={(field, value) => updateField(field, value)}
        />
      </Card>

      {/* Save */}
      <div className="flex justify-end">
        <Button
          variant="accent"
          onClick={handleSave}
          loading={updateDeal.isPending}
        >
          Save Changes
        </Button>
      </div>
    </div>
  );
}
