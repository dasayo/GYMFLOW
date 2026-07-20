import { isAxiosError } from 'axios';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';

import { registrarCortesia, type CheckinResponse } from '../../api/checkin';
import { useAuth } from '../../context/useAuth';

function CortesiaPage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const puedeGestionar = auth.hasPermission('members.gestionar_usuarios');

  const [cedula, setCedula] = useState('');
  const [nombre, setNombre] = useState('');
  const [resultado, setResultado] = useState<CheckinResponse | null>(null);

  const registrar = useMutation({
    mutationFn: () => registrarCortesia(cedula.trim(), nombre.trim()),
    onSuccess: (data) => {
      setResultado(data);
      if (data.resultado === 'exitoso') {
        // El prospecto es un User nuevo: refresca la lista de usuarios (008).
        queryClient.invalidateQueries({ queryKey: ['usuarios'] });
        setCedula('');
        setNombre('');
      }
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (registrar.isPending) return;
    setResultado(null);
    registrar.mutate();
  }

  if (!puedeGestionar) {
    return (
      <div>
        <h1 className="text-member-navy-text text-2xl font-semibold mb-4">Cortesía de primer día</h1>
        <p className="text-red-600 bg-red-50 border border-red-200 rounded p-3">
          No tienes el permiso <code>members.gestionar_usuarios</code> — no puedes registrar
          cortesías. Pídele a un administrador que te lo otorgue.
        </p>
      </div>
    );
  }

  const exitoso = resultado?.resultado === 'exitoso';

  return (
    <div className="max-w-xl">
      <h1 className="text-member-navy-text text-2xl font-semibold mb-1">Cortesía de primer día</h1>
      <p className="text-member-muted text-sm mb-6">
        Registra el acceso gratuito único de una persona nueva. Verifica su identidad antes de
        continuar: la cortesía queda ligada a la cédula y no se puede repetir.
      </p>

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-card shadow border border-gray-200 p-4 flex flex-wrap items-end gap-3 mb-6"
      >
        <div>
          <label className="block text-xs text-gray-600 mb-1" htmlFor="cedula">Cédula</label>
          <input
            id="cedula"
            required
            inputMode="numeric"
            value={cedula}
            onChange={(e) => setCedula(e.target.value)}
            className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1" htmlFor="nombre">Nombre</label>
          <input
            id="nombre"
            required
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            className="w-56 border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={registrar.isPending}
          className="bg-member-navy text-white rounded px-3 py-1.5 text-sm disabled:opacity-50"
        >
          Registrar cortesía
        </button>
      </form>

      {registrar.isError && !isAxiosError(registrar.error) && (
        <p className="text-red-600 text-sm mb-4">No se pudo registrar la cortesía.</p>
      )}
      {registrar.isError && isAxiosError(registrar.error) && registrar.error.response?.status === 422 && (
        <p className="text-red-600 text-sm mb-4">
          Revisa los datos: la cédula debe tener entre 5 y 15 dígitos y el nombre no puede estar vacío.
        </p>
      )}

      {resultado && (
        <div
          className={`rounded-card border p-4 ${
            exitoso ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'
          }`}
        >
          <p className={`font-semibold ${exitoso ? 'text-green-800' : 'text-red-800'}`}>
            {exitoso ? '✅ Cortesía concedida' : '⛔ Cortesía no concedida'}
          </p>
          <p className="text-sm text-gray-700 mt-1">{resultado.mensaje}</p>
          {!exitoso && resultado.razon === 'CORTESIA_YA_UTILIZADA' && (
            <p className="text-sm text-gray-700 mt-2">
              Esta persona ya agotó su primer día gratis. Si desea seguir entrenando, créale una
              membresía en <strong>Usuarios</strong>.
            </p>
          )}
          {!exitoso && resultado.razon === 'YA_REGISTRADO' && (
            <p className="text-sm text-gray-700 mt-2">
              Esta cédula ya tiene una cuenta en el sistema; debe hacer check-in normal en el kiosko.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default CortesiaPage;
