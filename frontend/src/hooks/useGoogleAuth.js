import API from "../srevices/api";

export async function getGoogleAuthUrl(intent = "login") {
  const endpoint = intent === "signup" ? "/google/signup" : "/google/login";
  const { data } = await API.get(endpoint);
  return data.url;
}

export async function getGoogleConfig() {
  const { data } = await API.get("/google/config");
  return data;
}

export async function startGoogleAuth(intent = "login") {
  const url = await getGoogleAuthUrl(intent);
  window.location.href = url;
}
