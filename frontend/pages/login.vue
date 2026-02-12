<template>
  <div class="container mx-auto px-4 py-16 max-w-md">
    <UCard>
      <template #header>
        <h2 class="text-2xl font-bold text-center">Вхід</h2>
      </template>

      <UForm :state="form" @submit="onSubmit" class="space-y-4">
        <UFormField label="Email" name="email" required>
          <UInput
            v-model="form.email"
            type="email"
            placeholder="your@email.com"
          />
        </UFormField>

        <UFormField label="Пароль" name="password" required>
          <UInput
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
definePageMeta({
  layout: "site",
});

const { login, isAuthenticated, checkAuth } = useAuth();

// Перевірка чи вже залогінений
await checkAuth();
if (isAuthenticated.value) {
  await navigateTo("/cabinet/dashboard");
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
    await navigateTo("/cabinet/dashboard");
  } else {
    // Show error (TODO: use toast/notification)
    alert(result.error);
  }
};
</script>
