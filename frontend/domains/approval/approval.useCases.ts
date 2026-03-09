import * as approvalApi from "./approval.api";

export function useApprovalUseCases() {
  const { fetch } = useApi();

  async function getModelRoles(params?: {
    application?: "procurement" | "sales";
  }) {
    const { data, error } = await approvalApi.getModelRoles(fetch, params);
    return { data: Array.isArray(data) ? data : [], error };
  }

  async function createModelRole(body: {
    company: number;
    name: string;
    application: "procurement" | "sales";
  }) {
    return approvalApi.createModelRole(fetch, body);
  }

  async function patchModelRole(
    roleId: number,
    body: Partial<{
      name: string;
      application: "procurement" | "sales";
    }>
  ) {
    return approvalApi.patchModelRole(fetch, roleId, body);
  }

  async function deleteModelRole(roleId: number) {
    return approvalApi.deleteModelRole(fetch, roleId);
  }

  async function getModelRoleUsers(roleId: number) {
    const { data, error } = await approvalApi.getModelRoleUsers(fetch, roleId);
    return { data: Array.isArray(data) ? data : [], error };
  }

  async function createModelRoleUser(body: { role: number; user: number }) {
    return approvalApi.createModelRoleUser(fetch, body);
  }

  async function deleteModelRoleUser(id: number) {
    return approvalApi.deleteModelRoleUser(fetch, id);
  }

  async function getRangeMatrix() {
    const { data, error } = await approvalApi.getRangeMatrix(fetch);
    return { data: Array.isArray(data) ? data : [], error };
  }

  async function createRangeMatrix(body: {
    company: number;
    budget_from: number;
    budget_to: number;
    currency: number;
  }) {
    return approvalApi.createRangeMatrix(fetch, body);
  }

  async function patchRangeMatrix(
    id: number,
    body: Partial<{
      budget_from: number;
      budget_to: number;
      currency: number;
      is_active: boolean;
    }>
  ) {
    return approvalApi.patchRangeMatrix(fetch, id, body);
  }

  async function deleteRangeMatrix(id: number) {
    return approvalApi.deleteRangeMatrix(fetch, id);
  }

  async function getApprovalModels(params?: {
    application?: "procurement" | "sales";
    categoryIds?: number[];
    rangeIds?: number[];
  }) {
    const { data, error } = await approvalApi.getApprovalModels(fetch, params);
    return { data: Array.isArray(data) ? data : [], error };
  }

  async function createApprovalModel(body: Record<string, unknown>) {
    return approvalApi.createApprovalModel(fetch, body);
  }

  async function patchApprovalModel(id: number, body: Record<string, unknown>) {
    return approvalApi.patchApprovalModel(fetch, id, body);
  }

  async function deleteApprovalModel(id: number) {
    return approvalApi.deleteApprovalModel(fetch, id);
  }

  return {
    getModelRoles,
    createModelRole,
    patchModelRole,
    deleteModelRole,
    getModelRoleUsers,
    createModelRoleUser,
    deleteModelRoleUser,
    getRangeMatrix,
    createRangeMatrix,
    patchRangeMatrix,
    deleteRangeMatrix,
    getApprovalModels,
    createApprovalModel,
    patchApprovalModel,
    deleteApprovalModel,
  };
}
