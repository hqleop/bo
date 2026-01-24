export default defineNuxtPlugin(async () => {
  const { checkAuth } = useAuth()
  
  // Перевірка автентифікації при завантаженні додатку
  await checkAuth()
})
