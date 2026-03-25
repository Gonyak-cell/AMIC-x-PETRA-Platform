import type {
  MarketingDocType,
  MarketingMaterial,
} from "@/modules/ma/types/marketing_material";

export interface VersionedMarketingMaterial {
  material: MarketingMaterial;
  versionLabel: string;
}

function getMaterialOrderKey(material: MarketingMaterial) {
  return `${material.created_at}|${material.id}`;
}

function getMaterialActivityTimestamp(material: MarketingMaterial) {
  return material.distributed_at ?? material.updated_at ?? material.created_at;
}

export function buildVersionedMarketingMaterials(
  materials: MarketingMaterial[],
  docType: MarketingDocType,
): VersionedMarketingMaterial[] {
  return materials
    .filter((material) => material.doc_type === docType)
    .sort((left, right) =>
      getMaterialOrderKey(left).localeCompare(getMaterialOrderKey(right)),
    )
    .map((material, index) => ({
      material,
      versionLabel: `v${index + 1}`,
    }));
}

export function isDistributedToRecipient(
  material: MarketingMaterial,
  recipientName: string,
) {
  return (material.distributed_to ?? []).includes(recipientName);
}

export function getLatestRecipientDistribution(
  versionedMaterials: VersionedMarketingMaterial[],
  recipientName: string,
): VersionedMarketingMaterial | null {
  let latest: VersionedMarketingMaterial | null = null;

  for (const versioned of versionedMaterials) {
    if (!isDistributedToRecipient(versioned.material, recipientName)) {
      continue;
    }

    if (
      !latest ||
      getMaterialActivityTimestamp(versioned.material).localeCompare(
        getMaterialActivityTimestamp(latest.material),
      ) > 0
    ) {
      latest = versioned;
    }
  }

  return latest;
}

export function getRecipientDistributionDate(material: MarketingMaterial) {
  return (material.distributed_at ?? material.updated_at ?? material.created_at).slice(
    0,
    10,
  );
}
