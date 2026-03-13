export function resolveRegistrationStep(payload: {
  registration_step?: number | null
  registration_company_id?: number | null
} | null | undefined): number {
  const rawStep = Number(payload?.registration_step ?? 4)
  let step = Number.isFinite(rawStep) ? Math.min(Math.max(rawStep, 1), 4) : 4

  // If company is already selected on step 2, user should continue from step 3.
  const registrationCompanyId = Number(payload?.registration_company_id ?? null)
  if (Number.isFinite(registrationCompanyId) && registrationCompanyId > 0 && step < 3) {
    step = 3
  }

  return step
}
