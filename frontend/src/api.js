export async function api(path, options = {}) {
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (response.status === 204) return null;
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? "The server returned an invalid response."
        : `Request failed (${response.status}). Please try again.`,
    );
  }
  if (!response.ok)
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "Check the fields and try again.",
    );
  return data;
}
export const post = (path, data) =>
  api(path, { method: "POST", body: JSON.stringify(data) });
