import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CUNY_SCHOOLS } from "@/lib/constants/universities";
import { UniversityDropdownProps } from "@/types/user";

export function UniversityDropdown({
  value,
  onChange,
  disabled,
  className,
}: UniversityDropdownProps) {
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger className={className}>
        <SelectValue placeholder="Select your school" />
      </SelectTrigger>
      <SelectContent>
        {CUNY_SCHOOLS.map((school) => (
          <SelectItem key={school} value={school}>
            {school}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
