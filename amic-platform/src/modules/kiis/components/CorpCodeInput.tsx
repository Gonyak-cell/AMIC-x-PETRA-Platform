import { useState } from "react";
import { Search } from "lucide-react";
import { Input, Button } from "@/components/ui";

interface CorpCodeInputProps {
  onSearch: (corpCode: string) => void;
  label?: string;
  placeholder?: string;
}

export default function CorpCodeInput({
  onSearch,
  label = "Company Code",
  placeholder = "Enter corp code...",
}: CorpCodeInputProps) {
  const [value, setValue] = useState("");

  const handleSearch = () => {
    const trimmed = value.trim();
    if (trimmed) onSearch(trimmed);
  };

  return (
    <div className="flex gap-3 items-end">
      <div className="flex-1 max-w-sm">
        <Input
          label={label}
          placeholder={placeholder}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
      </div>
      <Button variant="primary" icon={Search} onClick={handleSearch}>
        Search
      </Button>
    </div>
  );
}
