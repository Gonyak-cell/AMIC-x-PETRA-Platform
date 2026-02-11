import { useState } from "react";
import { Plus } from "lucide-react";
import { Input, Button } from "@/components/ui";

interface AliasCreateFormProps {
  onSubmit: (aliasName: string, corpCode: string) => void;
  isPending: boolean;
}

export default function AliasCreateForm({
  onSubmit,
  isPending,
}: AliasCreateFormProps) {
  const [aliasName, setAliasName] = useState("");
  const [corpCode, setCorpCode] = useState("");

  const handleSubmit = () => {
    const name = aliasName.trim();
    const code = corpCode.trim();
    if (!name || !code) return;
    onSubmit(name, code);
    setAliasName("");
    setCorpCode("");
  };

  return (
    <div className="flex gap-3 items-end">
      <div className="flex-1">
        <Input
          label="Alias Name"
          placeholder="e.g. 삼전"
          value={aliasName}
          onChange={(e) => setAliasName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />
      </div>
      <div className="flex-1">
        <Input
          label="Corp Code"
          placeholder="e.g. 00126380"
          value={corpCode}
          onChange={(e) => setCorpCode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        />
      </div>
      <Button
        variant="primary"
        icon={Plus}
        onClick={handleSubmit}
        loading={isPending}
        disabled={!aliasName.trim() || !corpCode.trim()}
      >
        Add
      </Button>
    </div>
  );
}
