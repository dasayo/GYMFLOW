import { Navigate, Outlet } from 'react-router';

import { useMemberAuth } from '../../context/useMemberAuth';

function PortalProtectedRoute() {
  const { estado } = useMemberAuth();

  if (estado === 'cargando') {
    return (
      <div className="min-h-screen bg-member-bg flex items-center justify-center">
        <p className="text-member-muted">Cargando tu sesión…</p>
      </div>
    );
  }
  if (estado === 'anonimo') {
    return <Navigate to="/portal/login" replace />;
  }
  return <Outlet />;
}

export default PortalProtectedRoute;
