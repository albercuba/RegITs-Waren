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

export async function scanPhoto(photo, options = {}) {
  const formData = new FormData();
  formData.append("photo", photo);
  if (options.ocrCropped) {
    formData.append("ocr_cropped", "true");
  }
  formData.append("mode", options.mode || "fast");
  const response = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: options.ocrCropped ? { "X-OCR-Cropped": "true" } : undefined,
    body: formData,
  });
  return parseResponse(response);
}

export async function createSubmission(metadata, photos) {
  const formData = new FormData();
  formData.append("metadata", JSON.stringify(metadata));
  for (const photo of photos) {
    formData.append("photos", photo);
  }
  const response = await fetch(`${API_BASE}/submissions`, { method: "POST", body: formData });
  return parseResponse(response);
}

export async function getSubmissions(adminPassword) {
  const response = await fetch(`${API_BASE}/submissions`, {
    headers: { "X-Admin-Password": adminPassword },
  });
  return parseResponse(response);
}

export async function getLocations() {
  const response = await fetch(`${API_BASE}/locations`);
  return parseResponse(response);
}

export async function getEmailSettings(adminPassword) {
  const response = await fetch(`${API_BASE}/admin/email-settings`, {
    headers: { "X-Admin-Password": adminPassword },
  });
  return parseResponse(response);
}

export async function getAdminLocations(adminPassword) {
  const response = await fetch(`${API_BASE}/admin/locations`, {
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

export async function saveLocations(adminPassword, locations) {
  const response = await fetch(`${API_BASE}/admin/locations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": adminPassword,
    },
    body: JSON.stringify({ locations }),
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

export async function getScanDebug(debugId, adminPassword) {
  const response = await fetch(`${API_BASE}/scan/debug/${debugId}`, {
    headers: { "X-Admin-Password": adminPassword },
  });
  return parseResponse(response);
}

export async function getUploadBlob(filename, adminPassword) {
  const response = await fetch(`${API_BASE}/uploads/${encodeURIComponent(filename)}`, {
    headers: { "X-Admin-Password": adminPassword },
  });
  if (!response.ok) {
    const data = await response.text();
    throw new Error(data || "Bild konnte nicht geladen werden");
  }
  return response.blob();
}
