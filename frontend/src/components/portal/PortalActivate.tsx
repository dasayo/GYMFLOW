import { isAxiosError } from 'axios';
import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';

import { portalActivate } from '../../api/portal';

function PortalActivate() {
  const [cedula, setCedula] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: () => portalActivate(cedula, email, password),
    onSuccess: () => {
      navigate('/portal/login', { replace: true });
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mutation.isPending) return;
    mutation.mutate();
  }

  const activacionRechazada =
    isAxiosError(mutation.error) && mutation.error.response?.status === 400;

  return (
    <div className="min-h-screen bg-member-bg flex items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-card shadow-sm p-8 w-full max-w-sm border border-gray-100"
      >
        <p className="text-member-navy font-bold text-2xl mb-1">GymFlow</p>
        <h1 className="text-member-navy-text text-lg font-semibold mb-1">Activa tu cuenta</h1>
        <p className="text-member-muted text-sm mb-6">
          Si ya estás registrado en el gimnasio, ingresa tu cédula y el correo que diste en
          recepción, y elige tu contraseña.
        </p>

        <label className="block text-sm text-member-navy-text mb-1" htmlFor="activar-cedula">
          Cédula
        </label>
        <input
          id="activar-cedula"
          type="text"
          inputMode="numeric"
          required
          value={cedula}
          onChange={(e) => setCedula(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mb-4 text-gray-900"
        />

        <label className="block text-sm text-member-navy-text mb-1" htmlFor="activar-email">
          Correo
        </label>
        <input
          id="activar-email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mb-4 text-gray-900"
        />

        <label className="block text-sm text-member-navy-text mb-1" htmlFor="activar-password">
          Contraseña nueva
        </label>
        <input
          id="activar-password"
          type="password"
          required
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2.5 mb-4 text-gray-900"
        />

        {mutation.isError && (
          <p className="text-member-error text-sm mb-4">
            {activacionRechazada
              ? 'No se pudo activar la cuenta. Verifica tus datos o consulta en recepción.'
              : 'Algo salió mal. Intenta de nuevo.'}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-member-navy text-white rounded-lg px-3 py-3 font-medium disabled:opacity-50"
        >
          {mutation.isPending ? 'Activando…' : 'Activar cuenta'}
        </button>

        <p className="text-member-muted text-sm mt-6 text-center">
          ¿Ya tienes cuenta?{' '}
          <Link to="/portal/login" className="text-member-navy font-medium underline">
            Inicia sesión
          </Link>
        </p>
      </form>
    </div>
  );
}

export default PortalActivate;
