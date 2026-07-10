import { useState, type ReactNode } from 'react';

import { clearStoredToken, getStoredToken, setStoredToken } from '../api/client';
import type { Rol } from '../api/auth';
import { AuthContext } from './useAuth';

const ROL_KEY = 'gymflow-staff-rol';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [rol, setRol] = useState<Rol | null>(() => localStorage.getItem(ROL_KEY) as Rol | null);

  function login(nuevoToken: string, nuevoRol: Rol) {
    setStoredToken(nuevoToken);
    localStorage.setItem(ROL_KEY, nuevoRol);
    setToken(nuevoToken);
    setRol(nuevoRol);
  }

  function logout() {
    clearStoredToken();
    localStorage.removeItem(ROL_KEY);
    setToken(null);
    setRol(null);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated: token !== null, rol, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
