// In dev, Vite proxies "/api" to the backend (see vite.config.js). In
// production the frontend and backend are deployed as separate services, so
// VITE_API_BASE_URL must point at the backend's public URL (e.g.
// https://order-enquiry-backend.onrender.com/api).
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // response had no JSON body
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function searchOrders(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      params.append(key, value);
    }
  });
  return fetch(`${API_BASE}/orders?${params.toString()}`).then(handleResponse);
}

export function createOrder(order) {
  return fetch(`${API_BASE}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(order),
  }).then(handleResponse);
}

export function updateOrder(orderId, order) {
  return fetch(`${API_BASE}/orders/${orderId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(order),
  }).then(handleResponse);
}

export function deleteOrder(orderId) {
  return fetch(`${API_BASE}/orders/${orderId}`, { method: "DELETE" }).then(
    handleResponse
  );
}

export function importOrders(file) {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API_BASE}/orders/import`, {
    method: "POST",
    body: formData,
  }).then(handleResponse);
}

export function getReceiptUrl(orderId) {
  return `${API_BASE}/orders/${orderId}/receipt`;
}

export function getSalesSummary(filters = {}) {
  const params = new URLSearchParams(filters);
  return fetch(`${API_BASE}/sales/summary?${params.toString()}`).then(handleResponse);
}

export function getSalesByDay(filters = {}) {
  const params = new URLSearchParams(filters);
  return fetch(`${API_BASE}/sales/by-day?${params.toString()}`).then(handleResponse);
}

export function getTopProducts(filters = {}) {
  const params = new URLSearchParams(filters);
  return fetch(`${API_BASE}/sales/top-products?${params.toString()}`).then(handleResponse);
}
