export const CUNY_SCHOOLS = [
  "Baruch College",
  "Brooklyn College",
  "City College (City College of New York)",
  "Hunter College",
  "Queens College",
  "College of Staten Island",
  "John Jay College of Criminal Justice",
  "Lehman College",
  "Medgar Evers College",
  "New York City College of Technology",
  "York College",
  "Queensborough Community College",
  "Borough of Manhattan Community College (BMCC)",
  "Bronx Community College",
  "Hostos Community College",
  "LaGuardia Community College",
] as const;

export type CUNYSchool = (typeof CUNY_SCHOOLS)[number];
