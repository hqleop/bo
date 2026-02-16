/** Current user (me) and profile */
export interface MeUser {
  id: number
  email: string
  first_name?: string
  last_name?: string
  middle_name?: string
  phone?: string
  avatar?: string | null
}

export interface Me {
  user?: MeUser
  memberships?: unknown[]
  permissions?: string[]
}

/** Profile update payload (PATCH /auth/me/) */
export interface MeUpdatePayload {
  first_name?: string
  last_name?: string
  middle_name?: string
  phone?: string
}

/** Membership item (from /memberships/) */
export interface Membership {
  id: number
  user: {
    id: number
    email: string
    first_name?: string
    last_name?: string
    phone?: string
    is_active: boolean
  }
  [key: string]: unknown
}

/** Create user payload (POST /memberships/create-user/) */
export interface CreateUserPayload {
  first_name: string
  last_name: string
  middle_name?: string
  phone?: string
  email: string
  password: string
}

/** Update user payload (PATCH /memberships/:id/update-user/) */
export interface UpdateUserPayload {
  first_name?: string
  last_name?: string
  email?: string
  phone?: string
  password?: string
  password_confirm?: string
}
