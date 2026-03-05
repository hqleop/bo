<template>
  <div class="container mx-auto px-4 py-12 max-w-3xl">
    <UCard>
      <template #header>
        <div class="space-y-4">
          <h2 class="text-2xl font-bold text-center">Реєстрація</h2>
          <UStepper
            v-model="stepperValue"
            :items="registrationSteps"
            value-key="value"
            size="sm"
            :disabled="true"
          />
        </div>
      </template>

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

          <UButton type="submit" block :loading="loading">Зберегти та продовжити</UButton>
        </UForm>
      </div>

      <div v-else-if="currentStep === 2">
        <div class="space-y-4">
          <UFormField label="Тип суб'єкта" name="subject_type" required>
            <USelectMenu
              v-model="step2Form.subject_type"
              :items="subjectTypeOptions"
              value-key="value"
              label-key="label"
              placeholder="Оберіть тип суб'єкта"
              class="w-full"
              :disabled="isCompanyDataLocked"
            />
          </UFormField>

          <UFormField :label="codeLabel" name="edrpou" required>
            <UInput
              v-model="step2Form.edrpou"
              type="text"
              :inputmode="isNumericCodeType ? 'numeric' : 'text'"
              @input="onCodeInput"
            />
          </UFormField>

          <UFormField
            v-if="step2Form.subject_type !== 'individual'"
            label="Назва згідно уставних документів"
            name="name"
            :required="!shouldUseExistingCompanyFlow"
          >
            <UInput v-model="step2Form.name" :disabled="isCompanyDataLocked" />
          </UFormField>

          <UFormField
            v-if="step2Form.subject_type === 'non_resident'"
            label="Країна реєстрації"
            name="registration_country"
            :required="!shouldUseExistingCompanyFlow"
          >
            <USelectMenu
              v-model="step2Form.registration_country"
              :items="registrationCountryOptions"
              value-key="value"
              label-key="label"
              placeholder="Оберіть країну"
              class="w-full"
              :disabled="isCompanyDataLocked"
            />
          </UFormField>

          <UFormField :label="addressLabel" name="company_address" :required="!shouldUseExistingCompanyFlow">
            <UInput v-model="step2Form.company_address" :disabled="isCompanyDataLocked" />
          </UFormField>

          <UFormField
            v-if="step2Form.subject_type === 'individual' && !shouldUseExistingCompanyFlow"
            label="Завантажити документ, що підтверджує особу"
            name="identity_document"
            required
          >
            <UFileUpload
              v-model="step2Form.identity_document"
              :multiple="false"
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              label="Оберіть файл"
              description="Додайте документ для підтвердження особи"
            />
          </UFormField>

          <UAlert
            v-if="companyLookup?.exists && companyLookup?.has_registered_users"
            color="primary"
            variant="subtle"
            title="Компанія вже має зареєстрованих користувачів"
            description="Дані компанії заповнено автоматично та заблоковано для редагування. Реєстрація буде виконана як приєднання до існуючої компанії."
          />

          <div class="rounded-md border border-gray-200 p-4 space-y-3">
            <UCheckbox
              v-model="step2Form.agree_trade_rules"
              name="agree_trade_rules"
            >
              <template #label>
                Я погоджуюсь з
                <button
                  type="button"
                  class="text-primary-600 underline"
                  @click="openInfoModal('trade')"
                >
                  регламентом торгів
                </button>
              </template>
            </UCheckbox>

            <UCheckbox
              v-model="step2Form.agree_privacy_policy"
              name="agree_privacy_policy"
            >
              <template #label>
                Я погоджуюся з
                <button
                  type="button"
                  class="text-primary-600 underline"
                  @click="openInfoModal('privacy')"
                >
                  політикою конфіденційності
                </button>
              </template>
            </UCheckbox>
          </div>

          <div class="flex gap-4">
            <UButton type="button" variant="outline" block @click="currentStep = 1">Назад</UButton>
            <UButton type="button" block :loading="loading" @click="handleStep2Continue">
              Зберегти та продовжити
            </UButton>
          </div>
        </div>
      </div>

      <div v-else>
        <UForm @submit="onStep3Submit" class="space-y-4">
          <div class="rounded-md border border-gray-200 p-4 space-y-3">
            <p class="text-sm font-medium">Напрямок діяльності:</p>
            <UCheckbox v-model="step3Form.goal_tenders" name="goal_tenders" label="Організація тендерів" />
            <UCheckbox v-model="step3Form.goal_participation" name="goal_participation" label="Участь в тендерах" />
          </div>

          <div v-if="step3Form.goal_participation" class="space-y-4">
            <UCheckbox
              v-model="step3Form.agree_participation_visibility"
              name="agree_participation_visibility"
              label="Погоджуюсь, що мої реєстраційні дані відображатимуться організаторам тендерів"
            />

            <CpvTenderModalSelect
              label="Категорії CPV"
              placeholder="Оберіть одну або кілька CPV-категорій"
              :selected-ids="cpvSelectedIds"
              :selected-labels="cpvSelectedLabels"
              @update:selected-ids="cpvSelectedIds = $event"
              @update:selected-labels="cpvSelectedLabels = $event"
            />
          </div>

          <div class="flex gap-4">
            <UButton type="button" variant="outline" block @click="currentStep = 2">Назад</UButton>
            <UButton type="submit" block :loading="loading">Завершити реєстрацію</UButton>
          </div>
        </UForm>
      </div>
    </UCard>

    <UModal v-model:open="infoModalOpen">
      <template #content>
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">{{ infoModalTitle }}</h3>
          </template>
          <p class="text-sm text-gray-700">{{ infoModalText }}</p>
          <template #footer>
            <UButton block @click="infoModalOpen = false">Закрити</UButton>
          </template>
        </UCard>
      </template>
    </UModal>

    <UModal v-model:open="successModalOpen">
      <template #content>
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">{{ successModalTitle }}</h3>
          </template>
          <p>{{ successModalText }}</p>
          <template #footer>
            <div class="flex gap-3">
              <UButton type="button" variant="outline" block @click="goToHome">На головну</UButton>
              <UButton type="button" block @click="goToLogin">Вхід</UButton>
            </div>
          </template>
        </UCard>
      </template>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { getApiErrorMessage } from "~/shared/api/error";
import { onBeforeUnmount } from "vue";

definePageMeta({
  layout: "site",
});

const route = useRoute();
const router = useRouter();
const usersUC = useUsersUseCases();
const { isAuthenticated, checkAuth } = useAuth();
const { refreshMe } = useMe();

const loading = ref(false);
const currentStep = ref(1);
const userId = ref<number | null>(null);
const companyId = ref<number | null>(null);

const registrationSteps = [
  { title: "Крок 1", value: "step1", description: "" },
  { title: "Крок 2", value: "step2", description: "" },
  { title: "Крок 3", value: "step3", description: "" },
];

const stepperValue = computed(() => `step${currentStep.value}`);

const step1Form = reactive({
  first_name: "",
  last_name: "",
  middle_name: "",
  phone: "",
  email: "",
  password: "",
});

const step2Form = reactive({
  subject_type: "fop_resident" as "fop_resident" | "legal_resident" | "non_resident" | "individual",
  edrpou: "",
  name: "",
  registration_country: "",
  company_address: "",
  identity_document: null as File | null,
  agree_trade_rules: false,
  agree_privacy_policy: false,
});

type SubjectType = "fop_resident" | "legal_resident" | "non_resident" | "individual";
type RegistrationCompanyLookup = {
  exists: boolean;
  has_registered_users: boolean;
  company?: {
    id?: number;
    edrpou?: string;
    name?: string;
    subject_type?: SubjectType;
    registration_country?: string;
    company_address?: string;
  } | null;
};

const step3Form = reactive({
  goal_tenders: false,
  goal_participation: false,
  agree_participation_visibility: false,
});

const cpvSelectedIds = ref<number[]>([]);
const cpvSelectedLabels = ref<string[]>([]);

const subjectTypeOptions = [
  { label: "Фізична особа-підприємець (Резидент)", value: "fop_resident" },
  { label: "Юридична особа (Резидент)", value: "legal_resident" },
  { label: "Не резидент", value: "non_resident" },
  { label: "Фізична особа", value: "individual" },
];

const registrationCountryOptions = ref<Array<{ label: string; value: string }>>([]);
const companyLookup = ref<RegistrationCompanyLookup | null>(null);
const companyLookupLoading = ref(false);
let companyLookupTimer: ReturnType<typeof setTimeout> | null = null;
let companyLookupRequestId = 0;

const isNumericCodeType = computed(
  () => step2Form.subject_type !== "non_resident",
);
const shouldUseExistingCompanyFlow = computed(
  () => Boolean(companyLookup.value?.exists),
);
const isCompanyDataLocked = computed(
  () => Boolean(companyLookup.value?.exists && companyLookup.value?.has_registered_users),
);

const codeLabel = computed(() => {
  if (step2Form.subject_type === "fop_resident") return "ІПН";
  if (step2Form.subject_type === "legal_resident") return "Код ЄДРПОУ";
  if (step2Form.subject_type === "individual") return "Ідентифікаційний код";
  return "Унікальний код організації в країні реєстрації";
});

const addressLabel = computed(() => {
  if (step2Form.subject_type === "fop_resident" || step2Form.subject_type === "individual") {
    return "Фактична адреса";
  }
  return "Юридична адреса";
});

const infoModalOpen = ref(false);
const infoModalTitle = ref("");
const infoModalText = ref("");

const successModalOpen = ref(false);
const successModalTitle = ref("Реєстрацію завершено");
const successModalText = ref("Ви успішно зареєструвались у системі.");

const getQueryStep = () => {
  const raw = Array.isArray(route.query.step) ? route.query.step[0] : route.query.step;
  const parsed = Number(raw);
  if (Number.isFinite(parsed) && parsed >= 1 && parsed <= 3) return parsed;
  return null;
};

const initRegistrationState = async () => {
  await checkAuth();

  if (!isAuthenticated.value) {
    currentStep.value = 1;
    return;
  }

  const me = await refreshMe();
  const hasMemberships = Array.isArray(me?.memberships) && me.memberships.length > 0;
  const registrationStep = Number((me as any)?.registration_step ?? 4);

  userId.value = me?.user?.id ?? null;
  companyId.value = Number((me as any)?.registration_company_id ?? null) || null;

  if (registrationStep >= 4 && hasMemberships) {
    await navigateTo("/cabinet/dashboard");
    return;
  }

  const queryStep = getQueryStep();
  currentStep.value = queryStep ?? Math.min(Math.max(registrationStep, 1), 3);
  if (currentStep.value < 1 || currentStep.value > 3) currentStep.value = 1;
};

await initRegistrationState();

const loadCountryNumbers = async () => {
  const { data } = await usersUC.getRegistrationCountryBusinessNumbers();
  registrationCountryOptions.value = (data as any[]).map((item) => ({
    value: String(item.number_code || ""),
    label: String(item.label || `${item.number_name || ""} (${item.number_code || ""})`).trim(),
  }));
};

const expectedCodeLength = (subjectType: SubjectType) => {
  if (subjectType === "legal_resident") return 8;
  if (subjectType === "fop_resident" || subjectType === "individual") return 10;
  return null;
};

const clearCompanyLookup = () => {
  companyLookup.value = null;
  companyLookupLoading.value = false;
};

const applyLookupCompanyData = (lookup: RegistrationCompanyLookup) => {
  if (!lookup.exists || !lookup.company) return;
  const company = lookup.company;
  if (company.subject_type) {
    step2Form.subject_type = company.subject_type;
  }
  step2Form.name = String(company.name || "");
  step2Form.company_address = String(company.company_address || "");
  step2Form.registration_country = String(company.registration_country || "");
  if (lookup.has_registered_users) {
    step2Form.identity_document = null;
  }
};

const lookupCompanyByCode = async () => {
  const code = String(step2Form.edrpou || "").trim();
  if (!code) {
    clearCompanyLookup();
    return;
  }

  const expectedLen = expectedCodeLength(step2Form.subject_type as SubjectType);
  if (expectedLen && code.length !== expectedLen) {
    clearCompanyLookup();
    return;
  }

  const requestId = ++companyLookupRequestId;
  companyLookupLoading.value = true;
  const { data, error } = await usersUC.lookupRegistrationCompanyByCode(code);
  if (requestId !== companyLookupRequestId) return;
  companyLookupLoading.value = false;

  if (error || !data) {
    clearCompanyLookup();
    return;
  }

  companyLookup.value = data;
  if (data.exists && data.company) {
    applyLookupCompanyData(data);
  }
};

const scheduleCompanyLookup = () => {
  if (companyLookupTimer) {
    clearTimeout(companyLookupTimer);
    companyLookupTimer = null;
  }
  companyLookupTimer = setTimeout(() => {
    void lookupCompanyByCode();
  }, 350);
};

watch(
  () => step2Form.subject_type,
  async (nextSubjectType) => {
    if (nextSubjectType === "non_resident" && registrationCountryOptions.value.length === 0) {
      await loadCountryNumbers();
    }
    if (nextSubjectType !== "non_resident") {
      step2Form.registration_country = "";
    }
    scheduleCompanyLookup();
  },
  { immediate: true },
);

watch(
  () => step2Form.edrpou,
  () => {
    scheduleCompanyLookup();
  },
);

const onPhoneInput = (event: Event) => {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  step1Form.phone = target.value.replace(/\D/g, "").slice(0, 9);
};

const onCodeInput = (event: Event) => {
  if (!isNumericCodeType.value) return;
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  step2Form.edrpou = target.value.replace(/\D/g, "");
};

const openInfoModal = (type: "trade" | "privacy") => {
  if (type === "trade") {
    infoModalTitle.value = "Регламент торгів";
    infoModalText.value = "Погоджуючись, ви приймаєте правила проведення торгів та взаємодії з учасниками на платформі.";
  } else {
    infoModalTitle.value = "Політика конфіденційності";
    infoModalText.value = "Погоджуючись, ви приймаєте обробку персональних даних відповідно до політики конфіденційності платформи.";
  }
  infoModalOpen.value = true;
};

const onStep1Submit = async () => {
  if (step1Form.phone.length !== 9) {
    alert("Введіть повний номер телефону (9 цифр після +380).");
    return;
  }

  loading.value = true;
  const payload = {
    ...step1Form,
    phone: `+380${step1Form.phone}`,
  };
  const { data, error } = await usersUC.registerStep1(payload);
  loading.value = false;

  if (error) {
    alert(getApiErrorMessage(error));
    return;
  }

  userId.value =
    (data as { id?: number; user_id?: number })?.user_id ??
    (data as { id?: number })?.id ??
    null;
  currentStep.value = 2;
};

const validateStep2 = () => {
  const code = String(step2Form.edrpou ?? "").trim();

  if (!code) return "Заповніть код.";
  const expectedLen = expectedCodeLength(step2Form.subject_type as SubjectType);
  if (expectedLen && code.length !== expectedLen) {
    if (step2Form.subject_type === "legal_resident") return "Код ЄДРПОУ має містити 8 цифр.";
    if (step2Form.subject_type === "fop_resident") return "ІПН має містити 10 цифр.";
    return "Ідентифікаційний код має містити 10 цифр.";
  }

  if (!shouldUseExistingCompanyFlow.value) {
    if (step2Form.subject_type !== "individual" && !step2Form.name.trim()) {
      return "Заповніть назву згідно уставних документів.";
    }

    if (step2Form.subject_type === "non_resident" && !step2Form.registration_country) {
      return "Оберіть країну реєстрації.";
    }

    if (!step2Form.company_address.trim()) return "Заповніть адресу.";

    if (step2Form.subject_type === "individual" && !step2Form.identity_document) {
      return "Завантажте документ, що підтверджує особу.";
    }
  }

  if (!step2Form.agree_trade_rules) return "Потрібно погодитися з регламентом торгів.";
  if (!step2Form.agree_privacy_policy) return "Потрібно погодитися з політикою конфіденційності.";

  return null;
};

const onStep2Submit = async () => {
  if (!userId.value) {
    const me = await refreshMe();
    userId.value = me?.user?.id ?? null;
  }

  if (!userId.value) {
    alert("Не вдалося визначити користувача. Увійдіть знову.");
    await navigateTo("/login");
    return;
  }

  const validationError = validateStep2();
  if (validationError) {
    alert(validationError);
    return;
  }

  const normalizedCode = String(step2Form.edrpou ?? "").trim();

  if (shouldUseExistingCompanyFlow.value) {
    loading.value = true;
    const { data, error } = await usersUC.registerStep2Existing({
      user_id: userId.value,
      edrpou: normalizedCode,
      name: step2Form.name.trim(),
    });
    loading.value = false;

    if (error) {
      alert(getApiErrorMessage(error));
      return;
    }

    companyId.value =
      Number((data as any)?.company?.id ?? null) ||
      Number((data as any)?.company_id ?? null) ||
      companyId.value;

    if (!companyId.value) {
      const me = await refreshMe();
      companyId.value = Number((me as any)?.registration_company_id ?? null) || null;
    }

    const membershipStatus = String((data as any)?.status || "");
    if (membershipStatus === "pending") {
      successModalTitle.value = "Запит на приєднання надіслано";
      successModalText.value =
        "Реєстрацію завершено. Ваш запит на приєднання до компанії передано адміністратору для підтвердження.";
      successModalOpen.value = true;
      return;
    }

    currentStep.value = 3;
    return;
  }

  const body = new FormData();
  body.append("user_id", String(userId.value));
  body.append("subject_type", step2Form.subject_type);
  body.append("edrpou", normalizedCode);
  body.append("name", step2Form.name.trim());
  body.append("company_address", step2Form.company_address.trim());
  body.append("agree_trade_rules", String(step2Form.agree_trade_rules));
  body.append("agree_privacy_policy", String(step2Form.agree_privacy_policy));

  if (step2Form.registration_country) {
    body.append("registration_country", step2Form.registration_country);
  }
  if (step2Form.identity_document) {
    body.append("identity_document", step2Form.identity_document);
  }

  loading.value = true;
  const { data, error } = await usersUC.registerStep2New(body);
  loading.value = false;

  if (error) {
    alert(getApiErrorMessage(error));
    return;
  }

  companyId.value = Number((data as any)?.id ?? null) || companyId.value;
  currentStep.value = 3;
};

const handleStep2Continue = async () => {
  try {
    await onStep2Submit();
  } catch (error) {
    console.error("Step 2 submit failed:", error);
    alert("Сталася помилка при збереженні другого кроку.");
  }
};

const onStep3Submit = async () => {
  if (!userId.value || !companyId.value) {
    const me = await refreshMe();
    userId.value = me?.user?.id ?? null;
    companyId.value = Number((me as any)?.registration_company_id ?? null) || null;
  }

  if (!userId.value || !companyId.value) {
    alert("Не вдалося визначити дані реєстрації. Оновіть сторінку.");
    return;
  }

  if (!step3Form.goal_tenders && !step3Form.goal_participation) {
    alert("Оберіть хоча б один напрямок діяльності.");
    return;
  }

  if (step3Form.goal_participation) {
    if (!step3Form.agree_participation_visibility) {
      alert("Підтвердьте відображення реєстраційних даних.");
      return;
    }
    if (!cpvSelectedIds.value.length) {
      alert("Оберіть хоча б одну CPV-категорію.");
      return;
    }
  }

  loading.value = true;
  const { error } = await usersUC.registerStep3CompanyCpvs({
    user_id: userId.value,
    company_id: companyId.value,
    goal_tenders: step3Form.goal_tenders,
    goal_participation: step3Form.goal_participation,
    agree_participation_visibility: step3Form.goal_participation
      ? step3Form.agree_participation_visibility
      : false,
    cpv_ids: step3Form.goal_participation ? cpvSelectedIds.value : [],
  });
  loading.value = false;

  if (error) {
    alert(getApiErrorMessage(error));
    return;
  }

  successModalTitle.value = "Реєстрацію завершено";
  successModalText.value = "Ви успішно зареєструвались у системі.";
  successModalOpen.value = true;
};

onBeforeUnmount(() => {
  if (companyLookupTimer) {
    clearTimeout(companyLookupTimer);
    companyLookupTimer = null;
  }
});

const goToHome = async () => {
  successModalOpen.value = false;
  await router.push("/");
};

const goToLogin = async () => {
  successModalOpen.value = false;
  await router.push("/login");
};
</script>
