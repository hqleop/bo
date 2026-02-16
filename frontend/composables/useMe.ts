import { useUsersStore } from '~/domains/users/users.store'
import { useUsersUseCases } from '~/domains/users/users.useCases'

/**
 * UI composable for current user (me): state and display helpers.
 * Data and actions are provided by the users domain (store + useCases).
 */
export const useMe = () => {
  const { me } = useUsersStore()
  const { refreshMe } = useUsersUseCases()

  const userShortName = computed(() => {
    const u = me.value?.user
    if (!u) return ''
    const name = [u.first_name, u.last_name].filter(Boolean).join(' ').trim()
    return name || u.email || ''
  })

  const userAvatarUrl = computed(() => me.value?.user?.avatar ?? null)

  return { me, refreshMe, userShortName, userAvatarUrl }
}
