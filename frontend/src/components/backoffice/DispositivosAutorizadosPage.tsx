import { isAxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Navigate } from 'react-router';

import {
  autorizarDispositivo,
  getDeviceId,
  getDispositivosAutorizados,
  revocarDispositivo,
} from '../../api/checkin';
import { useAuth } from '../../context/useAuth';

const QUERY_KEY = ['dispositivos-autorizados'];

function DispositivosAutorizadosPage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [etiqueta, setEtiqueta] = useState('');

  const query = useQuery({ queryKey: QUERY_KEY, queryFn: getDispositivosAutorizados });

  const autorizar = useMutation({
    mutationFn: (input: { deviceId: string; etiqueta?: string }) =>
      autorizarDispositivo(input.deviceId, input.etiqueta),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const revocar = useMutation({
    mutationFn: revocarDispositivo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  if (isAxiosError(query.error) && query.error.response?.status === 401) {
    auth.logout();
    return <Navigate to="/staff/login" replace />;
  }

  const sinPermiso = isAxiosError(query.error) && query.error.response?.status === 403;
  const esteDispositivoId = getDeviceId();
  const esteDispositivoAutorizado = query.data?.some((d) => d.device_id === esteDispositivoId);

  return (
    <div>
      <h1 className="text-member-navy-text text-2xl font-semibold mb-4">Dispositivos autorizados</h1>
      <p className="text-gray-500 text-sm mb-6">
        Solo los kioscos autorizados aquí pueden mostrar la pantalla de check-in en{' '}
        <code className="bg-gray-100 rounded px-1">/kiosko</code>.
      </p>

      {sinPermiso && (
        <p className="text-red-600 bg-red-50 border border-red-200 rounded p-3 mb-4">
          No tienes permiso para gestionar dispositivos.
        </p>
      )}

      {!sinPermiso && (
        <div className="bg-white rounded-card shadow border border-gray-200 p-5 mb-6">
          <h2 className="text-member-navy-text font-semibold mb-1">Este dispositivo</h2>
          <p className="text-sm text-gray-500 mb-3">
            Si estás usando esta pantalla desde la tablet/equipo que va a ser el kiosko, autorízalo
            directamente aquí.
          </p>
          <p className="font-mono text-xs bg-gray-50 rounded px-3 py-2 mb-3 break-all">
            {esteDispositivoId}
          </p>
          <input
            value={etiqueta}
            onChange={(e) => setEtiqueta(e.target.value)}
            placeholder="Etiqueta (ej. Tablet recepción)"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm mb-3"
          />
          <button
            onClick={() => autorizar.mutate({ deviceId: esteDispositivoId, etiqueta })}
            disabled={autorizar.isPending || esteDispositivoAutorizado}
            className="w-full min-h-[44px] bg-member-navy text-white rounded px-3 py-2 font-semibold disabled:opacity-50"
          >
            {esteDispositivoAutorizado ? 'Este dispositivo ya está autorizado' : 'Autorizar este dispositivo'}
          </button>
        </div>
      )}

      {query.isLoading && <p className="text-gray-500">Cargando…</p>}

      {query.data && (
        <table className="w-full bg-white rounded-card shadow border border-gray-200 text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-200">
              <th className="p-3">Dispositivo</th>
              <th className="p-3">Etiqueta</th>
              <th className="p-3">Autorizado el</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {query.data.length === 0 && (
              <tr>
                <td colSpan={4} className="p-3 text-gray-500">
                  No hay dispositivos autorizados todavía.
                </td>
              </tr>
            )}
            {query.data.map((d) => (
              <tr key={d.device_id} className="border-b border-gray-100 last:border-0">
                <td className="p-3 text-gray-900 font-mono">{d.device_id}</td>
                <td className="p-3 text-gray-900">{d.etiqueta ?? '—'}</td>
                <td className="p-3 text-gray-900">{new Date(d.autorizado_en).toLocaleString()}</td>
                <td className="p-3 text-right">
                  <button
                    onClick={() => revocar.mutate(d.device_id)}
                    disabled={revocar.isPending}
                    className="text-sm bg-red-600 text-white rounded px-3 py-1.5 disabled:opacity-50"
                  >
                    Revocar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default DispositivosAutorizadosPage;
