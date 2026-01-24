export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated } = useAuth()
  
  // Якщо не автентифікований і намагається зайти в кабінет - редірект на головну
  if (!isAuthenticated.value && to.path.startsWith('/cabinet')) {
    return navigateTo('/')
  }
})
