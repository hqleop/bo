type MembershipLike = {
  status?: string;
  company?: { id?: number | null } | number | null;
};

type MePayloadLike = {
  memberships?: MembershipLike[];
};

let pendingCompanyIdRequest: Promise<number | null> | null = null;

function resolveCompanyId(payload: unknown): number | null {
  const data = payload as MePayloadLike | null | undefined;
  const memberships = Array.isArray(data?.memberships) ? data.memberships : [];
  if (!memberships.length) return null;

  const approved = memberships.find((m) => m?.status === "approved") || memberships[0];
  if (!approved) return null;

  if (typeof approved.company === "number") return approved.company;
  const nested = approved.company?.id;
  return typeof nested === "number" ? nested : null;
}

export const useCurrentCompanyId = () => {
  const cachedCompanyId = useState<number | null>(
    "current-company-id",
    () => null,
  );
  const { me, refreshMe } = useMe();

  const getCurrentCompanyId = async (force = false): Promise<number | null> => {
    if (!force && cachedCompanyId.value) return cachedCompanyId.value;

    const fromState = resolveCompanyId(me.value);
    if (fromState) {
      cachedCompanyId.value = fromState;
      return fromState;
    }

    if (pendingCompanyIdRequest) return pendingCompanyIdRequest;

    pendingCompanyIdRequest = (async () => {
      const fresh = await refreshMe();
      const resolved = resolveCompanyId(fresh ?? me.value);
      cachedCompanyId.value = resolved;
      return resolved;
    })().finally(() => {
      pendingCompanyIdRequest = null;
    });

    return pendingCompanyIdRequest;
  };

  return {
    getCurrentCompanyId,
    currentCompanyId: readonly(cachedCompanyId),
  };
};
