import { isAxiosError } from 'axios';
import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';

import { postLogin } from '../../api/auth';
import { useAuth } from '../../context/useAuth';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const auth = useAuth();
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: () => postLogin(email, password),
    onSuccess: (data) => {
      auth.login(data.access_token, data.rol);
      navigate('/staff/dispositivos-bloqueados', { replace: true });
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (mutation.isPending) return;
    mutation.mutate();
  }

  const credencialesInvalidas =
    isAxiosError(mutation.error) && mutation.error.response?.status === 401;

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-8">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-lg shadow p-8 w-full max-w-sm border border-gray-200"
      >
        <h1 className="text-gray-900 text-xl font-semibold mb-1">GymFlow · Backoffice</h1>
        <p className="text-gray-500 text-sm mb-6">Ingresa con tu correo y contraseña.</p>

        <label className="block text-sm text-gray-700 mb-1" htmlFor="email">
          Correo
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 mb-4 text-gray-900"
        />

        <label className="block text-sm text-gray-700 mb-1" htmlFor="password">
          Contraseña
        </label>
        <input
          id="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 mb-4 text-gray-900"
        />

        {mutation.isError && (
          <p className="text-red-600 text-sm mb-4">
            {credencialesInvalidas ? 'Credenciales inválidas.' : 'No se pudo iniciar sesión.'}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-gray-900 text-white rounded px-3 py-2 font-medium disabled:opacity-50"
        >
          {mutation.isPending ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </div>
  );
}

export default LoginForm;
