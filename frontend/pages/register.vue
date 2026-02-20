<template>
  <div class="container mx-auto px-4 py-16 max-w-2xl">
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-center">Реєстрація</h2>
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
            <div class="flex">
              <span
                class="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-700 text-sm"
              >
                +380
              </span>
              <UInput
                v-model="step1Form.phone"
                type="tel"
                class="flex-1 rounded-l-none"
                maxlength="9"
                placeholder="Введіть 9 цифр"
                @input="onPhoneInput"
              />
            </div>
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

          <!-- Existing Company: приєднання за кодом (ЄДРПОУ) -->
          <div v-if="step2Form.type === 'existing'">
            <UFormField
              label="Код компанії (ЄДРПОУ)"
              name="edrpou_existing"
              required
            >
              <UInput
                v-model="step2Form.edrpou_existing"
                placeholder="Введіть код компанії"
              />
            </UFormField>
            <UFormField label="Назва компанії (опційно)" name="name_existing">
              <UInput
                v-model="step2Form.name_existing"
                placeholder="При першій реєстрації — буде збережена як назва компанії"
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
            <p
              v-if="step2Form.goal_participation"
              class="mt-2 text-xs text-gray-600"
            >
              Реєстраційні дані учасника відображатимуться організаторам.
            </p>
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

      <!-- Step 3: CPV категорії для участі у тендерах -->
      <div v-if="currentStep === 3">
        <UForm @submit="onStep3Submit" class="space-y-4">
          <p class="text-sm text-gray-600">
            Оберіть CPV-категорії, за якими ви плануєте брати участь у
            тендерах. Ці категорії будуть закріплені за вашою компанією.
          </p>

          <CpvLazyMultiSearch
            label="Категорії CPV"
            placeholder="Оберіть одну або кілька CPV-категорій"
            :selected-ids="cpvSelectedIds"
            :selected-labels="cpvSelectedLabels"
            @update:selected-ids="cpvSelectedIds = $event"
            @update:selected-labels="cpvSelectedLabels = $event"
          />

          <div class="flex gap-4">
            <UButton
              variant="outline"
              block
              @click="currentStep = 2"
            >
              Назад
            </UButton>
            <UButton type="submit" block :loading="loading">
              Завершити реєстрацію
            </UButton>
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

const usersUC = useUsersUseCases();
const currentStep = ref(1);
const loading = ref(false);
const userId = ref<number | null>(null);
const companyId = ref<number | null>(null);

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
  edrpou_existing: "",
  name_existing: "",
  edrpou: "",
  name: "",
  goal_tenders: false,
  goal_participation: false,
});

const cpvSelectedIds = ref<number[]>([]);
const cpvSelectedLabels = ref<string[]>([]);

const companyTypeOptions = [
  { label: "Нова компанія", value: "new" },
  { label: "Існуюча компанія", value: "existing" },
];

const onPhoneInput = (event: Event) => {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  const digits = target.value.replace(/\D/g, "").slice(0, 9);
  step1Form.phone = digits;
};

const onStep1Submit = async () => {
  if (step1Form.phone.length !== 9) {
    alert("Введіть повний номер телефону (9 цифр після +380).");
    return;
  }

  loading.value = true;
  const payload = {
    ...step1Form,
    phone: step1Form.phone ? `+380${step1Form.phone}` : "",
  };
  const { data, error } = await usersUC.registerStep1(payload);
  loading.value = false;

  if (error) {
    alert(typeof error === "string" ? error : "Помилка реєстрації");
    return;
  }

  userId.value =
    (data as { id?: number; user_id?: number })?.user_id ??
    (data as { id?: number })?.id ??
    null;
  currentStep.value = 2;
};

const onStep2Submit = async () => {
  if (step2Form.type === "existing" && !step2Form.edrpou_existing?.trim()) {
    alert("Введіть код компанії (ЄДРПОУ)");
    return;
  }

  if (step2Form.type === "new") {
    if (!step2Form.goal_tenders && !step2Form.goal_participation) {
      alert("Оберіть хоча б одну ціль");
      return;
    }
  }

  loading.value = true;

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
          edrpou: step2Form.edrpou_existing.trim(),
          name: step2Form.name_existing?.trim() || undefined,
        };

  if (step2Form.type === "new") {
    const { data, error } = (await usersUC.registerStep2New(body)) as {
      data?: { id?: number };
      error: string | null;
    };
    loading.value = false;

    if (error) {
      alert(typeof error === "string" ? error : "Помилка реєстрації");
      return;
    }

    companyId.value = data?.id ?? null;

    if (step2Form.goal_participation && companyId.value && userId.value) {
      currentStep.value = 3;
      return;
    }

    alert("Реєстрацію завершено! Тепер ви можете увійти.");
    navigateTo("/login");
    return;
  }

  const { error } = await usersUC.registerStep2Existing(body);

  loading.value = false;

  if (error) {
    alert(typeof error === "string" ? error : "Помилка реєстрації");
    return;
  }

  alert("Реєстрацію завершено! Тепер ви можете увійти.");
  navigateTo("/login");
};

const onStep3Submit = async () => {
  if (!userId.value || !companyId.value) {
    alert("Сталася помилка. Спробуйте перезавантажити сторінку.");
    return;
  }
  if (!cpvSelectedIds.value.length) {
    alert("Оберіть хоча б одну CPV-категорію.");
    return;
  }

  loading.value = true;
  const { error } = await usersUC.registerStep3CompanyCpvs({
    user_id: userId.value,
    company_id: companyId.value,
    cpv_ids: cpvSelectedIds.value,
  });
  loading.value = false;

  if (error) {
    alert(typeof error === "string" ? error : "Помилка збереження CPV-категорій");
    return;
  }

  alert("Реєстрацію завершено! Тепер ви можете увійти.");
  navigateTo("/login");
};
</script>
