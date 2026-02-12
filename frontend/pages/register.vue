<template>
  <div class="container mx-auto px-4 py-16 max-w-2xl">
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-center">Реєстрація</h2>
        <p class="text-center text-gray-600 mt-2">Крок {{ currentStep }} з 2</p>
      </template>

      <!-- Step 1: User Info -->
      <div v-if="currentStep === 1">
        <UForm :state="step1Form" @submit="onStep1Submit" class="space-y-4">
          <UFormField label="Прізвище" name="last_name" required>
            <UInput v-model="step1Form.last_name" />
          </UFormField>

          <UFormField label="Ім'я" name="first_name" required>
            <UInput v-model="step1Form.first_name" />
          </UFormField>

          <UFormField label="По батькові" name="middle_name">
            <UInput v-model="step1Form.middle_name" />
          </UFormField>

          <UFormField label="Телефон" name="phone" required>
            <UInput v-model="step1Form.phone" type="tel" />
          </UFormField>

          <UFormField label="Email" name="email" required>
            <UInput v-model="step1Form.email" type="email" />
          </UFormField>

          <UFormField label="Пароль" name="password" required>
            <UInput v-model="step1Form.password" type="password" />
          </UFormField>

          <UButton type="submit" block :loading="loading">Далі</UButton>
        </UForm>
      </div>

      <!-- Step 2: Company -->
      <div v-if="currentStep === 2">
        <UForm :state="step2Form" @submit="onStep2Submit" class="space-y-4">
          <UFormField label="Тип реєстрації" name="type" required>
            <URadioGroup
              v-model="step2Form.type"
              :options="companyTypeOptions"
            />
          </UFormField>

          <!-- Existing Company -->
          <div v-if="step2Form.type === 'existing'">
            <UFormField label="Компанія" name="company_id" required>
              <USelect
                v-model="step2Form.company_id"
                :items="companyItems"
                value-key="id"
                label-key="name"
                placeholder="Оберіть компанію"
              />
            </UFormField>
          </div>

          <!-- New Company -->
          <div v-if="step2Form.type === 'new'">
            <UFormField label="Код ЄДРПОУ" name="edrpou" required>
              <UInput v-model="step2Form.edrpou" />
            </UFormField>

            <UFormField label="Назва компанії" name="name" required>
              <UInput v-model="step2Form.name" />
            </UFormField>

            <UFormField label="Цілі реєстрації" name="goals" required>
              <UCheckbox
                v-model="step2Form.goal_tenders"
                label="Проведення тендерів"
              />
              <UCheckbox
                v-model="step2Form.goal_participation"
                label="Участь у тендерах"
              />
            </UFormField>
          </div>

          <div class="flex gap-4">
            <UButton variant="outline" block @click="currentStep = 1"
              >Назад</UButton
            >
            <UButton type="submit" block :loading="loading"
              >Завершити реєстрацію</UButton
            >
          </div>
        </UForm>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "site",
});

const { isAuthenticated, checkAuth } = useAuth();

// Перевірка чи вже залогінений
await checkAuth();
if (isAuthenticated.value) {
  await navigateTo("/cabinet/dashboard");
}

const { fetch } = useApi();
const currentStep = ref(1);
const loading = ref(false);
const userId = ref<number | null>(null);

const step1Form = reactive({
  first_name: "",
  last_name: "",
  middle_name: "",
  phone: "",
  email: "",
  password: "",
});

const step2Form = reactive({
  type: "new" as "new" | "existing",
  company_id: null as number | null,
  edrpou: "",
  name: "",
  goal_tenders: false,
  goal_participation: false,
});

const companyTypeOptions = [
  { label: "Нова компанія", value: "new" },
  { label: "Існуюча компанія", value: "existing" },
];

// Load companies for step 2
const config = useRuntimeConfig();
const { data: companiesData } = await useFetch(
  `${config.public.apiBase}/companies/`,
);
const companies = computed(() => companiesData.value || []);
const companyItems = computed(() =>
  (companies.value as any[]).map((c) => ({
    id: c.id,
    name: c.name ?? c.label ?? String(c.id),
  }))
);

const onStep1Submit = async () => {
  loading.value = true;
  const { data, error } = await fetch("/registration/step1/", {
    method: "POST",
    body: step1Form,
  });
  loading.value = false;

  if (error) {
    alert(error.detail || "Помилка реєстрації");
    return;
  }

  userId.value = data.id;
  currentStep.value = 2;
};

const onStep2Submit = async () => {
  if (step2Form.type === "existing" && !step2Form.company_id) {
    alert("Оберіть компанію");
    return;
  }

  if (step2Form.type === "new") {
    if (!step2Form.goal_tenders && !step2Form.goal_participation) {
      alert("Оберіть хоча б одну ціль");
      return;
    }
  }

  loading.value = true;

  const endpoint =
    step2Form.type === "new"
      ? "/registration/step2/new/"
      : "/registration/step2/existing/";
  const body =
    step2Form.type === "new"
      ? {
          user_id: userId.value,
          edrpou: step2Form.edrpou,
          name: step2Form.name,
          goal_tenders: step2Form.goal_tenders,
          goal_participation: step2Form.goal_participation,
        }
      : {
          user_id: userId.value,
          company_id: step2Form.company_id,
        };

  const { data, error } = await fetch(endpoint, {
    method: "POST",
    body,
  });

  loading.value = false;

  if (error) {
    alert(error.detail || "Помилка реєстрації");
    return;
  }

  alert("Реєстрацію завершено! Тепер ви можете увійти.");
  navigateTo("/login");
};
</script>
