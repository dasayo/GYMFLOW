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

      // Sesión inválida a mitad de uso (token expirado/corrupto, cuenta
      // desactivada): cerrar sesión y forzar login de nuevo, no dejar
      // vistas de staff cargadas con datos viejos. Se excluye el propio
      // intento de login: ese 401 es "contraseña incorrecta", lo maneja
      // el formulario, no una sesión que se cayó.
      const esIntentoDeLogin = error.config?.url === '/auth/login';
      if (error.response.status === 401 && !esIntentoDeLogin) {
        clearStoredToken();
        localStorage.removeItem('gymflow-staff-rol');
        localStorage.removeItem('gymflow-staff-permisos');
        window.location.href = '/staff/login';
      }
    }
    return Promise.reject(error);
  },
);
