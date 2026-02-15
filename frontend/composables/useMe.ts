/** Один активний запит /auth/me/ — щоб layout і профіль не робили два запити підряд */
let meRefreshPromise: Promise<unknown> | null = null

/**
 * Поточний користувач кабінету (me). Один джерело правди для layout та профілю.
 * Після refreshMe() хедер одразу показує оновлені ім'я та аватар.
 * Повторні виклики refreshMe() під час виконання одного запиту отримують той самий Promise — лише один запит.
 */
export const useMe = () => {
  const { getAuthHeaders, checkAuth } = useAuth()
  const { fetch: apiFetch } = useApi()

  const me = useState<{
    user?: {
      id: number
      email: string
      first_name?: string
      last_name?: string
      middle_name?: string
      phone?: string
      avatar?: string | null
    }
    memberships?: unknown[]
    permissions?: string[]
  } | null>('cabinet-me', () => null)

  const refreshMe = async () => {
    if (meRefreshPromise) {
      const result = await meRefreshPromise
      return result as typeof me.value
    }
    await checkAuth()
    if (!getAuthHeaders().Authorization) {
      me.value = null
      return null
    }
    meRefreshPromise = (async () => {
      try {
        const { data, error } = await apiFetch('/auth/me/', { headers: getAuthHeaders() })
        if (error || !data) {
          me.value = null
          return null
        }
        // API може повертати user на верхньому рівні або лише в memberships[0].user
        const userFromMembership = data.memberships?.[0]?.user
        const user = data.user ? { ...data.user } : (userFromMembership ? { ...userFromMembership } : undefined)
        const payload = {
          user,
          memberships: Array.isArray(data.memberships) ? data.memberships : [],
          permissions: Array.isArray(data.permissions) ? data.permissions : [],
        }
        me.value = payload
        return payload
      } finally {
        meRefreshPromise = null
      }
    })()
    return meRefreshPromise as Promise<typeof me.value>
  }

  const userShortName = computed(() => {
    const u = me.value?.user
    if (!u) return ''
    const name = [u.first_name, u.last_name].filter(Boolean).join(' ').trim()
    return name || u.email || ''
  })

  const userAvatarUrl = computed(() => me.value?.user?.avatar ?? null)

  return { me, refreshMe, userShortName, userAvatarUrl }
}
