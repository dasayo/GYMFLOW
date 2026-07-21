import axios, { isAxiosError, type InternalAxiosRequestConfig } from 'axios';

import type { CheckinResponse } from './checkin';

// Sesión del Miembro (RF-02/RF-04): el access token vive SOLO en memoria (nunca
// localStorage — decisión de seguridad del equipo, cookie httpOnly para el
// refresh). Al recargar la página se recupera con un refresh silencioso.
let accessToken: string | null = null;

export function clearPortalToken(): void {
  accessToken = null;
}

export interface PortalSession {
  access_token: string;
  token_type: string;
  nombre: string | null;
}

export interface MembershipSummary {
  estado: 'activa' | 'vencida' | 'sin_plan';
  tipo: string | null;
  fecha_vencimiento: string | null;
  visitas_restantes: number | null;
  cupo_invitados_restantes: number | null;
  dias_restantes: number | null;
}

export interface AttendancePoint {
  fecha: string;
  asistencias: number;
}

export interface AttendanceConsistency {
  periodo: 'semana' | 'mes';
  total: number;
  puntos: AttendancePoint[];
}

export const portalClient = axios.create({ baseURL: '/api', withCredentials: true });

portalClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Refresh single-flight: si varias requests reciben 401 a la vez (o el
// contexto restaura sesión mientras carga el dashboard), todas esperan la
// MISMA promesa — con rotación de refresh token, dos refresh paralelos harían
// que uno revoque el token del otro.
let refreshEnCurso: Promise<PortalSession> | null = null;

export function refreshPortalSession(): Promise<PortalSession> {
  refreshEnCurso ??= axios
    .post<PortalSession>('/api/auth/portal/refresh', null, { withCredentials: true })
    .then(({ data }) => {
      accessToken = data.access_token;
      return data;
    })
    .finally(() => {
      refreshEnCurso = null;
    });
  return refreshEnCurso;
}

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

portalClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = (isAxiosError(error) ? error.config : undefined) as
      | RetriableConfig
      | undefined;
    if (isAxiosError(error) && error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      try {
        await refreshPortalSession();
      } catch {
        accessToken = null;
        return Promise.reject(error);
      }
      original.headers.Authorization = `Bearer ${accessToken}`;
      return portalClient(original);
    }
    return Promise.reject(error);
  },
);

export async function portalLogin(email: string, password: string): Promise<PortalSession> {
  const { data } = await portalClient.post<PortalSession>('/auth/portal/login', {
    email,
    password,
  });
  accessToken = data.access_token;
  return data;
}

export async function portalActivate(
  cedula: string,
  email: string,
  password: string,
): Promise<void> {
  await portalClient.post('/auth/portal/activar', { cedula, email, password });
}

export async function portalLogout(): Promise<void> {
  try {
    await portalClient.post('/auth/portal/logout');
  } finally {
    accessToken = null;
  }
}

export async function getMembershipSummary(): Promise<MembershipSummary> {
  const { data } = await portalClient.get<MembershipSummary>('/membresias/me/resumen');
  return data;
}

export async function getAttendanceConsistency(
  period: AttendanceConsistency['periodo'],
): Promise<AttendanceConsistency> {
  const { data } = await portalClient.get<AttendanceConsistency>('/checkin/me/constancia', {
    params: { period },
  });
  return data;
}

/** 012-checkin-qr-dinamico: el socio escanea el QR del kiosko desde el
 *  portal (ya logueado) — usa `portalClient` (Bearer + refresh automático),
 *  no el cliente de staff. */
export async function postEscanearQr(deviceId: string, nonce: string): Promise<CheckinResponse> {
  const { data } = await portalClient.post<CheckinResponse>('/checkin/qr/scan', {
    device_id: deviceId,
    nonce,
  });
  return data;
}
