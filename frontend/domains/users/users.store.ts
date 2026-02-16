import type { Me } from './users.types'

/** Global me state (shared with layout and profile). Key must match previous useState for compatibility. */
export function useUsersStore() {
  const me = useState<Me | null>('cabinet-me', () => null)
  return { me }
}
