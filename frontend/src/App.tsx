import { Route, Routes } from 'react-router';

import CheckinKiosk from './components/CheckinKiosk';
import DispositivosBloqueados from './components/backoffice/DispositivosBloqueados';
import LoginForm from './components/backoffice/LoginForm';
import ProtectedRoute from './components/backoffice/ProtectedRoute';

function App() {
  return (
    <Routes>
      <Route path="/" element={<CheckinKiosk />} />
      <Route path="/staff/login" element={<LoginForm />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/staff/dispositivos-bloqueados" element={<DispositivosBloqueados />} />
      </Route>
    </Routes>
  );
}

export default App;
