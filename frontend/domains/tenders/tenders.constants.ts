/** Етапи тендера з іконками для степеру (паспорт, підготовка, прийом, рішення, затвердження, завершений). */
export const TENDER_STAGE_ITEMS = [
  {
    value: "passport",
    title: "Паспорт тендера",
    icon: "i-heroicons-document-text",
  },
  {
    value: "preparation",
    title: "Підготовка процедури",
    icon: "i-heroicons-clipboard-document-list",
  },
  {
    value: "acceptance",
    title: "Прийом пропозицій",
    icon: "i-heroicons-envelope",
  },
  { value: "decision", title: "Вибір рішення", icon: "i-heroicons-scale" },
  {
    value: "approval",
    title: "Затвердження",
    icon: "i-heroicons-check-circle",
  },
  { value: "completed", title: "Завершений", icon: "i-heroicons-flag" },
] as const;
