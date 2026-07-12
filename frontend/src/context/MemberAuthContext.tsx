import { useEffect, useState, type ReactNode } from 'react';

import { clearPortalToken, portalLogout, refreshPortalSession } from '../api/portal';
import { MemberAuthContext, type MemberSessionState } from './useMemberAuth';

export function MemberAuthProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<MemberSessionState>('cargando');
  const [nombre, setNombre] = useState<string | null>(null);

  // Al montar: intenta restaurar la sesión con la cookie httpOnly de refresh
  // (el access token vive solo en memoria y se pierde al recargar la página).
  useEffect(() => {
    let cancelado = false;
    refreshPortalSession()
      .then((session) => {
        if (cancelado) return;
        setNombre(session.nombre);
        setEstado('autenticado');
      })
      .catch(() => {
        if (cancelado) return;
        clearPortalToken();
        setEstado('anonimo');
      });
    return () => {
      cancelado = true;
    };
  }, []);

  function login(nuevoNombre: string | null) {
    setNombre(nuevoNombre);
    setEstado('autenticado');
  }

  function logout() {
    void portalLogout();
    setNombre(null);
    setEstado('anonimo');
  }

  return (
    <MemberAuthContext.Provider value={{ estado, nombre, login, logout }}>
      {children}
    </MemberAuthContext.Provider>
  );
}
