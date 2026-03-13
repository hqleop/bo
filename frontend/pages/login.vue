<template>
  <div class="container mx-auto px-4 py-16 max-w-md">
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-center">Вхід</h2>
      </template>

      <UForm :state="form" @submit="onSubmit" class="space-y-4">
        <UFormField label="Email" name="email" required>
          <UInput
            class="w-full"
            v-model="form.email"
            type="email"
            placeholder="your@email.com"
          />
        </UFormField>

        <UFormField label="Пароль" name="password" required>
          <UInput
            class="w-full"
            v-model="form.password"
            type="password"
            placeholder="••••••••"
          />
        </UFormField>

        <UButton type="submit" block :loading="loading">Увійти</UButton>
      </UForm>

      <template #footer>
        <div class="text-center">
          <UButton variant="link" to="/password-reset" size="sm"
            >Забули пароль?</UButton
          >
        </div>
        <div class="text-center mt-4">
          <span class="text-gray-600">Немає акаунту? </span>
          <UButton variant="link" to="/register" size="sm"
            >Зареєструватися</UButton
          >
        </div>
      </template>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { resolveRegistrationStep } from "~/shared/registrationFlow";

definePageMeta({
  layout: "site",
});

const { login, isAuthenticated, checkAuth } = useAuth();
const { refreshMe } = useMe();

// Перевірка чи вже залогінений
await checkAuth();
if (isAuthenticated.value) {
  await navigateTo("/cabinet/tasks");
}

const form = reactive({
  email: "",
  password: "",
});
const loading = ref(false);

const onSubmit = async () => {
  loading.value = true;
  const result = await login(form.email, form.password);
  loading.value = false;

  if (result.success) {
    const me = await refreshMe();
    const registrationStep = resolveRegistrationStep(me as any);
    if (registrationStep < 4) {
      await navigateTo(
        `/register?step=${Math.min(Math.max(registrationStep, 1), 3)}`,
      );
      return;
    }
    const hasMemberships =
      Array.isArray(me?.memberships) && me.memberships.length > 0;
    if (!hasMemberships) {
      await navigateTo("/register?step=2");
      return;
    }
    await navigateTo("/cabinet/tasks");
  } else {
    // Show error (TODO: use toast/notification)
    alert(result.error);
  }
};
</script>
