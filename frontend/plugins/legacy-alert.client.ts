export default defineNuxtPlugin(() => {
  const { pushFromLegacyAlert } = useSystemAlerts();

  const originalAlert = window.alert.bind(window);

  window.alert = (message?: unknown) => {
    pushFromLegacyAlert(message);
  };

  return {
    provide: {
      nativeAlert: originalAlert,
    },
  };
});
