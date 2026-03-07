import type { RequestFn } from "~/shared/api/apiClient";

export async function getModelRoles(
  request: RequestFn,
  params?: { application?: "procurement" | "sales" }
) {
  const query = params?.application
    ? `?application=${encodeURIComponent(params.application)}`
    : "";
  return request<any[]>(`/approval-model-roles/${query}`);
}

export async function createModelRole(
  request: RequestFn,
  body: {
    company: number;
    name: string;
    application: "procurement" | "sales";
  }
) {
  return request<any>("/approval-model-roles/", {
    method: "POST",
    body: body as unknown as Record<string, unknown>,
  });
}

export async function patchModelRole(
  request: RequestFn,
  roleId: number,
  body: Partial<{
    name: string;
    application: "procurement" | "sales";
  }>
) {
  return request<any>(`/approval-model-roles/${roleId}/`, {
    method: "PATCH",
    body: body as unknown as Record<string, unknown>,
  });
}

export async function getModelRoleUsers(
  request: RequestFn,
  roleId: number
) {
  return request<any[]>(`/approval-model-role-users/?role_id=${roleId}`);
}

export async function createModelRoleUser(
  request: RequestFn,
  body: { role: number; user: number }
) {
  return request<any>("/approval-model-role-users/", {
    method: "POST",
    body: body as unknown as Record<string, unknown>,
  });
}

export async function deleteModelRoleUser(request: RequestFn, id: number) {
  return request(`/approval-model-role-users/${id}/`, { method: "DELETE" });
}

export async function getRangeMatrix(request: RequestFn) {
  return request<any[]>("/approval-range-matrix/");
}

export async function createRangeMatrix(
  request: RequestFn,
  body: {
    company: number;
    budget_from: number;
    budget_to: number;
    currency: number;
  }
) {
  return request<any>("/approval-range-matrix/", {
    method: "POST",
    body: body as unknown as Record<string, unknown>,
  });
}

export async function getApprovalModels(
  request: RequestFn,
  params?: {
    application?: "procurement" | "sales";
    categoryIds?: number[];
    rangeIds?: number[];
  }
) {
  const q = new URLSearchParams();
  if (params?.application) q.set("application", params.application);
  for (const id of params?.categoryIds || []) q.append("category_ids", String(id));
  for (const id of params?.rangeIds || []) q.append("range_ids", String(id));
  const query = q.toString() ? `?${q.toString()}` : "";
  return request<any[]>(`/approval-models/${query}`);
}

export async function createApprovalModel(
  request: RequestFn,
  body: Record<string, unknown>
) {
  return request<any>("/approval-models/", { method: "POST", body });
}

export async function patchApprovalModel(
  request: RequestFn,
  id: number,
  body: Record<string, unknown>
) {
  return request<any>(`/approval-models/${id}/`, { method: "PATCH", body });
}

export async function deleteApprovalModel(request: RequestFn, id: number) {
  return request(`/approval-models/${id}/`, { method: "DELETE" });
}
