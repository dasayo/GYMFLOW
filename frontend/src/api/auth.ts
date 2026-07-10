import { apiClient } from './client';

export type Rol = 'empleado' | 'administrador';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  rol: Rol;
}

export async function postLogin(email: string, password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/login', { email, password });
  return data;
}
