/**
 * USATF-CT Grand Prix age divisions.
 * Higher divisions are subsets of lower ones (a 65-year-old is Seniors and Masters).
 */
export const DIVISION_MIN_AGE = {
  Open: 16,
  Masters: 40,
  Grandmasters: 50,
  Seniors: 60,
  Veteran: 70,
}

/**
 * Whether a result row is eligible for the selected division (age as of race day).
 * Unmatched / unknown ages are excluded when a division is selected.
 */
export function matchesDivision(row, divFilter) {
  if (!divFilter) return true
  const age = Number(row.age)
  if (!Number.isFinite(age)) return false
  const minAge = DIVISION_MIN_AGE[divFilter]
  if (minAge == null) return true
  return age >= minAge
}
