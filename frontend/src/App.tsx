import { Navigate, Outlet, Route, Routes } from 'react-router';

import { MemberAuthProvider } from './context/MemberAuthContext';

import CheckinKiosk from './components/CheckinKiosk';
import NotFound from './components/NotFound';
import AttendanceReportPage from './components/backoffice/AttendanceReportPage';
import CortesiaPage from './components/backoffice/CortesiaPage';
import DispositivosBloqueados from './components/backoffice/DispositivosBloqueados';
import LoginForm from './components/backoffice/LoginForm';
import MembershipTypesPage from './components/backoffice/MembershipTypesPage';
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
      <Route path="/kiosko" element={<CheckinKiosk />} />
      <Route path="/staff/login" element={<LoginForm />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<StaffLayout />}>
          <Route path="/staff/home" element={<StaffHome />} />
          <Route path="/staff/usuarios" element={<UsersPage />} />
          <Route path="/staff/cortesia" element={<CortesiaPage />} />
          <Route path="/staff/tipos-membresia" element={<MembershipTypesPage />} />
          <Route path="/staff/reportes" element={<AttendanceReportPage />} />
          <Route path="/staff/permisos" element={<PermissionsPage />} />
          <Route path="/staff/dispositivos-bloqueados" element={<DispositivosBloqueados />} />
        </Route>
      </Route>
      {/* El provider del Miembro solo envuelve la raíz y /portal/*: intenta
          un refresh al montar y no queremos ese request en el kiosko ni en
          el backoffice. */}
      <Route
        element={
          <MemberAuthProvider>
            <Outlet />
          </MemberAuthProvider>
        }
      >
        <Route path="/portal" element={<Navigate to="/" replace />} />
        <Route path="/portal/login" element={<PortalLogin />} />
        <Route path="/portal/activar" element={<PortalActivate />} />
        <Route element={<PortalProtectedRoute />}>
          <Route path="/" element={<PortalDashboard />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
