import { Navigate, Outlet } from 'react-router';

import { useAuth } from '../../context/useAuth';

function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Outlet /> : <Navigate to="/staff/login" replace />;
}

export default ProtectedRoute;
