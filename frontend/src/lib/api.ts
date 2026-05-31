// ============================================
// FFCES API Client
// ============================================

const API_BASE = "";

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async request(path: string, options: RequestInit = {}) {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
      throw new Error("غير مصرح");
    }

    if (res.status === 204) {
      return null;
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "فشل الطلب" }));
      throw new Error(error.detail || "فشل الطلب");
    }

    return res.json();
  }

  // GET
  async get<T = unknown>(path: string): Promise<T> {
    return this.request(path) as Promise<T>;
  }

  // POST
  async post<T = unknown>(path: string, data?: unknown): Promise<T> {
    return this.request(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }) as Promise<T>;
  }

  // PATCH
  async patch<T = unknown>(path: string, data?: unknown): Promise<T> {
    return this.request(path, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    }) as Promise<T>;
  }

  // PUT
  async put<T = unknown>(path: string, data?: unknown): Promise<T> {
    return this.request(path, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }) as Promise<T>;
  }

  // DELETE
  async delete<T = unknown>(path: string): Promise<T> {
    return this.request(path, { method: "DELETE" }) as Promise<T>;
  }

  // --- Auth ---
  login(email: string, password: string) {
    // Use form data for OAuth2
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    return this.request("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
  }

  getMe() {
    return this.get("/api/v1/auth/me");
  }

  // --- Dashboard ---
  getDashboardStats() {
    return this.get("/api/v1/dashboard/stats");
  }

  getOverdueAlerts() {
    return this.get("/api/v1/dashboard/overdue-alerts");
  }

  // --- Custodies ---
  getCustodies(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/custodies${query}`);
  }

  getCustody(id: string) {
    return this.get(`/api/v1/custodies/${id}`);
  }

  createCustody(data: unknown) {
    return this.post("/api/v1/custodies", data);
  }

  settleCustody(id: string, data: unknown) {
    return this.post(`/api/v1/custodies/${id}/settle`, data);
  }

  // --- Expenses ---
  getExpenses(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/expenses${query}`);
  }

  getExpense(id: string) {
    return this.get(`/api/v1/expenses/${id}`);
  }

  createExpense(data: unknown) {
    return this.post("/api/v1/expenses", data);
  }

  approveExpense(id: string) {
    return this.post(`/api/v1/expenses/${id}/approve`);
  }

  rejectExpense(id: string) {
    return this.post(`/api/v1/expenses/${id}/reject`);
  }

  // --- Parties ---
  getParties(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/parties${query}`);
  }

  getParty(id: string) {
    return this.get(`/api/v1/parties/${id}`);
  }

  createParty(data: unknown) {
    return this.post("/api/v1/parties", data);
  }

  updateParty(id: string, data: unknown) {
    return this.patch(`/api/v1/parties/${id}`, data);
  }

  // --- Payments ---
  getPayments(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/payments${query}`);
  }

  getPayment(id: string) {
    return this.get(`/api/v1/payments/${id}`);
  }

  createPayment(data: unknown) {
    return this.post("/api/v1/payments", data);
  }

  // --- Settlements ---
  getSettlements(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/settlements${query}`);
  }

  getSettlement(id: string) {
    return this.get(`/api/v1/settlements/${id}`);
  }

  createSettlement(data: unknown) {
    return this.post("/api/v1/settlements", data);
  }

  approveSettlement(id: string) {
    return this.post(`/api/v1/settlements/${id}/approve`);
  }

  rejectSettlement(id: string) {
    return this.post(`/api/v1/settlements/${id}/reject`);
  }

  // --- Work Records ---
  getWorkRecords(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/work-records${query}`);
  }

  getWorkRecord(id: string) {
    return this.get(`/api/v1/work-records/${id}`);
  }

  createWorkRecord(data: unknown) {
    return this.post("/api/v1/work-records", data);
  }

  createBulkWorkRecords(data: unknown) {
    return this.post("/api/v1/work-records/bulk", data);
  }

  verifyWorkRecord(id: string) {
    return this.post(`/api/v1/work-records/${id}/verify`);
  }

  rejectWorkRecord(id: string) {
    return this.post(`/api/v1/work-records/${id}/reject`);
  }

  // --- Entitlements ---
  getEntitlements(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/entitlements${query}`);
  }

  getEntitlement(id: string) {
    return this.get(`/api/v1/entitlements/${id}`);
  }

  createEntitlement(data: unknown) {
    return this.post("/api/v1/entitlements", data);
  }

  // --- Projects ---
  getProjects(params?: Record<string, string>) {
    const query = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.get(`/api/v1/projects${query}`);
  }

  // --- Reports ---
  getCustodyStatement(id: string) {
    return this.get(`/api/v1/reports/custody-statement/${id}`);
  }

  getPartyLedger(id: string) {
    return this.get(`/api/v1/reports/party-ledger/${id}`);
  }

  getProjectSummary(id: string) {
    return this.get(`/api/v1/reports/project-summary/${id}`);
  }

  getOpenCustodiesReport() {
    return this.get("/api/v1/reports/open-custodies");
  }
}

export const api = new ApiClient();
export default api;
