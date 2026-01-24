import type { ComputedRef, MaybeRef } from 'vue'
export type LayoutKey = "cabinet" | "default" | "site"
declare module 'nuxt/app' {
  interface PageMeta {
    layout?: MaybeRef<LayoutKey | false> | ComputedRef<LayoutKey | false>
  }
}