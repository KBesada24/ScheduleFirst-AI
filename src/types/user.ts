import { CUNYSchool } from "@/lib/constants/universities";

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  major: string | null;
  graduation_year: number | null;
  university: CUNYSchool | null;
  preferences: any;
  created_at: string;
  updated_at: string;
}

export interface UniversityDropdownProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}
