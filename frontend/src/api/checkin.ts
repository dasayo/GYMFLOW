import { isAxiosError } from 'axios';

import { apiClient } from './client';

export type CheckinResultado = 'exitoso' | 'denegado';

export type RazonDenegacion =
  | 'MEMBRESIA_VENCIDA'
  | 'SIN_VISITAS'
  | 'CEDULA_NO_ENCONTRADA'
  | 'DISPOSITIVO_BLOQUEADO'
  | 'CORTESIA_YA_UTILIZADA'
  | 'YA_REGISTRADO'
  | 'TITULAR_NO_ENCONTRADO'
  | 'TITULAR_SIN_MEMBRESIA'
  | 'SIN_CUPO_INVITADOS';

export interface CheckinResponse {
  resultado: CheckinResultado;
  mensaje: string;
  nombre: string | null;
  visitas_restantes: number | null;
  razon: RazonDenegacion | null;
}

export class DispositivoBloqueadoError extends Error {
  bloqueadoHasta: Date | null;

  constructor(mensaje: string, bloqueadoHasta: Date | null) {
    super(mensaje);
    this.bloqueadoHasta = bloqueadoHasta;
  }
}

const DEVICE_ID_KEY = 'gymflow-kiosko-device-id';

// Id estable del kiosko (RN-03, 002-acceso-denegado) — persistido en
// localStorage para que sobreviva a recargas de página.
function getDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = crypto.randomUUID();
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

export async function postCheckin(cedula: string): Promise<CheckinResponse> {
  try {
    const { data } = await apiClient.post<CheckinResponse>(
      '/checkin',
      { cedula },
      { headers: { 'X-Device-Id': getDeviceId() } },
    );
    return data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 423) {
      const detail = error.response.data?.detail as
        | { mensaje?: string; bloqueado_hasta?: string }
        | undefined;
      throw new DispositivoBloqueadoError(
        detail?.mensaje ?? 'Dispositivo bloqueado temporalmente.',
        detail?.bloqueado_hasta ? new Date(detail.bloqueado_hasta) : null,
      );
    }
    throw error;
  }
}

/** 005: el Staff registra la cortesía de primer día de un prospecto. No pasa
 *  por el kiosko (no manda X-Device-Id) — es un endpoint de backoffice. */
export async function registrarCortesia(
  cedula: string,
  nombre: string,
): Promise<CheckinResponse> {
  const { data } = await apiClient.post<CheckinResponse>('/checkin/cortesia', {
    cedula,
    nombre,
  });
  return data;
}

export interface GuestCheckinInput {
  cedulaTitular: string;
  cedulaInvitado: string;
  nombreInvitado: string;
}

/** 006: el titular presente hace entrar a su invitado desde el kiosko. Mismo
 *  guard de dispositivo que el check-in normal (puede devolver 423). */
export async function checkinGuest(input: GuestCheckinInput): Promise<CheckinResponse> {
  try {
    const { data } = await apiClient.post<CheckinResponse>(
      '/checkin/guest',
      {
        cedula_titular: input.cedulaTitular,
        cedula_invitado: input.cedulaInvitado,
        nombre_invitado: input.nombreInvitado,
      },
      { headers: { 'X-Device-Id': getDeviceId() } },
    );
    return data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 423) {
      const detail = error.response.data?.detail as
        | { mensaje?: string; bloqueado_hasta?: string }
        | undefined;
      throw new DispositivoBloqueadoError(
        detail?.mensaje ?? 'Dispositivo bloqueado temporalmente.',
        detail?.bloqueado_hasta ? new Date(detail.bloqueado_hasta) : null,
      );
    }
    throw error;
  }
}

export interface DispositivoBloqueadoInfo {
  device_id: string;
  intentos_fallidos: number;
  bloqueado_hasta: string;
}

export async function getDispositivosBloqueados(): Promise<DispositivoBloqueadoInfo[]> {
  const { data } = await apiClient.get<DispositivoBloqueadoInfo[]>(
    '/checkin/dispositivos-bloqueados',
  );
  return data;
}

export async function desbloquearDispositivo(deviceId: string): Promise<{ mensaje: string }> {
  const { data } = await apiClient.post<{ mensaje: string }>(
    `/checkin/desbloquear/${deviceId}`,
  );
  return data;
}
