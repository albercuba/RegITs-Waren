const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    if (response.status === 504) {
      throw new Error("Scan timed out");
    }
    const detail = typeof data === "object" ? data.detail : data;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || item.message || "Validierungsfehler").join(", ")
      : detail || "Request failed";
    throw new Error(message);
  }
  return data;
}

export async function scanPhoto(photo) {
  const formData = new FormData();
  formData.append("photo", photo);
  const response = await fetch(`${API_BASE}/scan`, { method: "POST", body: formData });
  return parseResponse(response);
}

export async function createSubmission(metadata, photo) {
  const formData = new FormData();
  formData.append("metadata", JSON.stringify(metadata));
  formData.append("photo", photo);
  const response = await fetch(`${API_BASE}/submissions`, { method: "POST", body: formData });
  return parseResponse(response);
}

export async function getSubmissions() {
  const response = await fetch(`${API_BASE}/submissions`);
  return parseResponse(response);
}

export async function getEmailSettings(adminPassword) {
  const response = await fetch(`${API_BASE}/admin/email-settings`, {
    headers: { "X-Admin-Password": adminPassword },
  });
  return parseResponse(response);
}

export async function saveEmailSettings(adminPassword, settings) {
  const response = await fetch(`${API_BASE}/admin/email-settings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": adminPassword,
    },
    body: JSON.stringify(settings),
  });
  return parseResponse(response);
}

export async function testEmailSettings(adminPassword, settings) {
  const response = await fetch(`${API_BASE}/admin/email-settings/test`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": adminPassword,
    },
    body: JSON.stringify(settings),
  });
  return parseResponse(response);
}

export async function getScanDebug(debugId) {
  const response = await fetch(`${API_BASE}/scan/debug/${debugId}`);
  return parseResponse(response);
}
