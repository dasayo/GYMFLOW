import { createContext, useContext } from 'react';

// 'cargando' = intentando restaurar la sesión con la cookie de refresh al
// montar la app; las rutas protegidas muestran un placeholder mientras tanto.
export type MemberSessionState = 'cargando' | 'anonimo' | 'autenticado';

export interface MemberAuthContextValue {
  estado: MemberSessionState;
  nombre: string | null;
  login: (nombre: string | null) => void;
  logout: () => void;
}

export const MemberAuthContext = createContext<MemberAuthContextValue | null>(null);

export function useMemberAuth(): MemberAuthContextValue {
  const context = useContext(MemberAuthContext);
  if (!context) {
    throw new Error('useMemberAuth debe usarse dentro de <MemberAuthProvider>');
  }
  return context;
}
