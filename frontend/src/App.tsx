import { Outlet, Route, Routes } from 'react-router';

import { MemberAuthProvider } from './context/MemberAuthContext';

import CheckinKiosk from './components/CheckinKiosk';
import Home from './components/Home';
import DispositivosBloqueados from './components/backoffice/DispositivosBloqueados';
import LoginForm from './components/backoffice/LoginForm';
import PermissionsPage from './components/backoffice/PermissionsPage';
import ProtectedRoute from './components/backoffice/ProtectedRoute';
import StaffHome from './components/backoffice/StaffHome';
import StaffLayout from './components/backoffice/StaffLayout';
import UsersPage from './components/backoffice/UsersPage';
import PortalActivate from './components/portal/PortalActivate';
import PortalDashboard from './components/portal/PortalDashboard';
import PortalLogin from './components/portal/PortalLogin';
import PortalProtectedRoute from './components/portal/PortalProtectedRoute';

function App() {
  return (
    <Routes>
      <Route path="/" element={<CheckinKiosk />} />
      <Route path="/home" element={<Home />} />
      <Route path="/staff/login" element={<LoginForm />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<StaffLayout />}>
          <Route path="/staff/home" element={<StaffHome />} />
          <Route path="/staff/usuarios" element={<UsersPage />} />
          <Route path="/staff/permisos" element={<PermissionsPage />} />
          <Route path="/staff/dispositivos-bloqueados" element={<DispositivosBloqueados />} />
        </Route>
      </Route>
      {/* El provider del Miembro solo envuelve /portal/*: intenta un refresh
          al montar y no queremos ese request en el kiosko ni en el backoffice. */}
      <Route
        element={
          <MemberAuthProvider>
            <Outlet />
          </MemberAuthProvider>
        }
      >
        <Route path="/portal/login" element={<PortalLogin />} />
        <Route path="/portal/activar" element={<PortalActivate />} />
        <Route element={<PortalProtectedRoute />}>
          <Route path="/portal" element={<PortalDashboard />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
