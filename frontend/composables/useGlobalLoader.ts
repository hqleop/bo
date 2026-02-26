export const useGlobalLoader = () => {
  const pending = useState<number>("global_loader_pending", () => 0);

  const start = () => {
    pending.value += 1;
  };

  const stop = () => {
    pending.value = Math.max(0, pending.value - 1);
  };

  const isLoading = computed(() => pending.value > 0);

  return {
    pending: readonly(pending),
    isLoading,
    start,
    stop,
  };
};
