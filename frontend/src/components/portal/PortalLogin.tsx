import { isAxiosError } from 'axios';
import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';

import { portalLogin } from '../../api/portal';
import { useMemberAuth } from '../../context/useMemberAuth';

function PortalLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const auth = useMemberAuth();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: () => portalLogin(email, password),
    onSuccess: (session) => {
      auth.login(session.nombre);
      navigate('/portal', { replace: true });
    },
  });

  if (auth.estado === 'autenticado') {
    return <Navigate to="/portal" replace />;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mutation.isPending) return;
    mutation.mutate();
  }

  const credencialesInvalidas =
    isAxiosError(mutation.error) && mutation.error.response?.status === 401;

  return (
    <div className="min-h-screen bg-member-bg flex items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-card shadow-sm p-8 w-full max-w-sm border border-gray-100"
      >
        <p className="text-member-navy font-bold text-2xl mb-1">GymFlow</p>
        <h1 className="text-member-navy-text text-lg font-semibold mb-1">Portal del socio</h1>
        <p className="text-member-muted text-sm mb-6">Ingresa con tu correo y contraseña.</p>

        <label className="block text-sm text-member-navy-text mb-1" htmlFor="portal-email">
          Correo
        </label>
        <input
          id="portal-email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mb-4 text-gray-900"
        />

        <label className="block text-sm text-member-navy-text mb-1" htmlFor="portal-password">
          Contraseña
        </label>
        <input
          id="portal-password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mb-4 text-gray-900"
        />

        {mutation.isError && (
          <p className="text-member-error text-sm mb-4">
            {credencialesInvalidas ? 'Credenciales inválidas.' : 'No se pudo iniciar sesión.'}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-member-navy text-white rounded-lg px-3 py-3 font-medium disabled:opacity-50"
        >
          {mutation.isPending ? 'Ingresando…' : 'Ingresar'}
        </button>

        <p className="text-member-muted text-sm mt-6 text-center">
          ¿Primera vez aquí?{' '}
          <Link to="/portal/activar" className="text-member-navy font-medium underline">
            Activa tu cuenta
          </Link>
        </p>
      </form>
    </div>
  );
}

export default PortalLogin;
