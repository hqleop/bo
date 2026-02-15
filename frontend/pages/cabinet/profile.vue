<template>
  <div class="max-w-2xl">
    <UCard>
      <template #header>
        <h2 class="text-xl font-semibold">Профіль</h2>
        <p class="text-sm text-gray-500 mt-1">Дані, внесені при реєстрації (крок 1). Можна змінити.</p>
      </template>

      <div v-if="loading" class="py-8 text-center text-gray-500">Завантаження...</div>
      <template v-else>
        <!-- Аватар -->
        <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4 pb-6 border-b border-gray-200">
          <div class="flex items-center gap-4">
            <UAvatar
              :src="me?.user?.avatar"
              :alt="form.first_name + ' ' + form.last_name"
              size="xl"
              class="flex-shrink-0"
            />
            <div class="flex flex-col gap-2">
              <input
                ref="avatarInputRef"
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                class="hidden"
                @change="onAvatarFileChange"
              />
              <UButton variant="outline" size="sm" @click="avatarInputRef?.click()">
                Завантажити фото
              </UButton>
              <p class="text-xs text-gray-500">JPEG, PNG, GIF або WebP, макс. 5 МБ</p>
            </div>
          </div>
          <p v-if="avatarError" class="text-sm text-red-600">{{ avatarError }}</p>
          <p v-if="avatarSuccess" class="text-sm text-green-600">{{ avatarSuccess }}</p>
        </div>

        <UForm
          :state="form"
          @submit="onSubmit"
          class="space-y-4"
        >
        <UFormField label="Прізвище" name="last_name" required>
          <UInput v-model="form.last_name" />
        </UFormField>
        <UFormField label="Ім'я" name="first_name" required>
          <UInput v-model="form.first_name" />
        </UFormField>
        <UFormField label="По батькові" name="middle_name">
          <UInput v-model="form.middle_name" />
        </UFormField>
        <UFormField label="Телефон" name="phone" required>
          <UInput v-model="form.phone" type="tel" />
        </UFormField>
        <UFormField label="Email" name="email">
          <UInput v-model="form.email" type="email" disabled class="opacity-75" />
          <template #hint>
            <span class="text-xs text-gray-500">Змінити email неможливо</span>
          </template>
        </UFormField>
        <div class="flex gap-3 pt-2">
          <UButton type="submit" :loading="saving">Зберегти</UButton>
          <UButton variant="outline" type="button" @click="resetForm">Скасувати</UButton>
        </div>
      </UForm>
      </template>
    </UCard>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "cabinet",
  middleware: "auth",
  meta: { title: "Профіль" },
});

const config = useRuntimeConfig();
const { getAuthHeaders } = useAuth();
const { fetch } = useApi();
const { me, refreshMe } = useMe();

const loading = ref(true);
const saving = ref(false);
const avatarInputRef = ref<HTMLInputElement | null>(null);
const avatarError = ref("");
const avatarSuccess = ref("");

const form = reactive({
  first_name: "",
  last_name: "",
  middle_name: "",
  phone: "",
  email: "",
});

function fillFormFrom(data: typeof me.value) {
  const u = data?.user;
  if (!u) return;
  form.first_name = u.first_name ?? "";
  form.last_name = u.last_name ?? "";
  form.middle_name = u.middle_name ?? "";
  form.phone = u.phone ?? "";
  form.email = u.email ?? "";
}

const personalAnalyticsPath = "/cabinet/dashboard?view=personal";

function resetForm() {
  fillFormFrom(me.value);
  navigateTo(personalAnalyticsPath);
}

async function loadMe() {
  loading.value = true;
  try {
    const data = await refreshMe();
    if (!data) {
      await navigateTo("/");
      return;
    }
    fillFormFrom(data);
  } finally {
    loading.value = false;
  }
}

// Заповнити поля, як тільки з’являться дані me (від layout або після loadMe)
watch(
  () => me.value,
  (data) => {
    if (data?.user) {
      fillFormFrom(data);
      loading.value = false;
    }
  },
  { immediate: true }
);

async function onSubmit() {
  saving.value = true;
  try {
    const { error } = await fetch("/auth/me/", {
      method: "PATCH",
      body: {
        first_name: form.first_name,
        last_name: form.last_name,
        middle_name: form.middle_name,
        phone: form.phone,
      },
      headers: getAuthHeaders(),
    });
    if (error) {
      alert(typeof error === "string" ? error : "Помилка збереження");
      return;
    }
    await refreshMe();
    fillFormFrom(me.value);
    await navigateTo(personalAnalyticsPath);
  } finally {
    saving.value = false;
  }
}

async function onAvatarFileChange(event: Event) {
  avatarError.value = "";
  avatarSuccess.value = "";
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("avatar", file);
  const token = getAuthHeaders().Authorization;
  if (!token) {
    avatarError.value = "Потрібна авторизація.";
    return;
  }
  try {
    const res = await $fetch<{ avatar: string }>(`${config.public.apiBase}/auth/me/avatar/`, {
      method: "POST",
      body: formData,
      headers: {
        Authorization: token,
      },
    });
    if (res?.avatar) {
      await refreshMe();
      avatarSuccess.value = "Фото збережено.";
    }
  } catch (e: any) {
    const msg = e?.data?.detail || e?.message || e?.data?.avatar?.[0] || "Помилка завантаження.";
    avatarError.value = typeof msg === "string" ? msg : JSON.stringify(msg);
  }
  input.value = "";
}

onMounted(async () => {
  if (!me.value?.user) {
    await loadMe();
  }
});
</script>
