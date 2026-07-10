import axios, { isAxiosError } from 'axios';

const TOKEN_KEY = 'gymflow-staff-token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const apiClient = axios.create({ baseURL: '/api' });

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// RN-11 (003-autenticacion-segura): expiración deslizante — el backend
// reemite el token en cada request autenticada exitosa, incluso en un 403
// (get_current_user corre y renueva antes de que require_permission decida
// el 403; solo un 401 no trae header nuevo). Por eso se lee en ambos caminos.
function guardarTokenRenovado(headers: Record<string, unknown> | undefined): void {
  const nuevoToken = headers?.['x-new-token'];
  if (typeof nuevoToken === 'string') {
    setStoredToken(nuevoToken);
  }
}

apiClient.interceptors.response.use(
  (response) => {
    guardarTokenRenovado(response.headers);
    return response;
  },
  (error) => {
    if (isAxiosError(error) && error.response) {
      guardarTokenRenovado(error.response.headers);
    }
    return Promise.reject(error);
  },
);
