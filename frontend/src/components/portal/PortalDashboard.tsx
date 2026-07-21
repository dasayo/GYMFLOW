import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import {
  getAttendanceConsistency,
  getMembershipSummary,
  type AttendanceConsistency,
  type MembershipSummary,
} from '../../api/portal';
import { useMemberAuth } from '../../context/useMemberAuth';

const ESTADO_BADGE: Record<MembershipSummary['estado'], { texto: string; clases: string }> = {
  activa: { texto: 'Activa', clases: 'bg-[#50cfb4] text-white' },
  vencida: { texto: 'Vencida', clases: 'bg-member-error text-white' },
  sin_plan: { texto: 'Sin plan', clases: 'bg-gray-200 text-gray-700' },
};

function formatearFecha(iso: string | null): string {
  if (!iso) return '—';
  return new Date(`${iso}T00:00:00`).toLocaleDateString('es-CO', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

// Criterio de HU-06: aviso SOLO si quedan entre 0 y 10 días; con más de 10
// días no se muestra nada.
function AvisoVencimiento({ resumen }: { resumen: MembershipSummary }) {
  const dias = resumen.dias_restantes;
  if (resumen.estado !== 'activa' || dias === null || dias > 10) return null;
  return (
    <div className="bg-[#f8dfd0] text-member-warning rounded-card px-4 py-3 mb-6 text-sm font-medium">
      Tu membresía vence {dias === 0 ? 'hoy' : `en ${dias} ${dias === 1 ? 'día' : 'días'}`} (
      {formatearFecha(resumen.fecha_vencimiento)}). Renuévala en recepción.
    </div>
  );
}

function StatCard({
  valor,
  etiqueta,
  clases,
}: {
  valor: string;
  etiqueta: string;
  clases: string;
}) {
  return (
    <div className={`rounded-card p-5 ${clases}`}>
      <p className="text-3xl font-bold">{valor}</p>
      <p className="text-sm mt-1 opacity-90">{etiqueta}</p>
    </div>
  );
}

function GraficoConstancia({
  constancia,
  periodo,
}: {
  constancia: AttendanceConsistency;
  periodo: AttendanceConsistency['periodo'];
}) {
  const maximo = Math.max(1, ...constancia.puntos.map((punto) => punto.asistencias));
  const etiquetaPeriodo = periodo === 'semana' ? 'última semana' : 'último mes';

  return (
    <section className="bg-white rounded-card shadow-sm border border-gray-100 p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-member-navy-text font-semibold">Tu constancia</h2>
          <p className="text-sm text-member-muted mt-1">Asistencias de la {etiquetaPeriodo}.</p>
        </div>
        <div className="text-sm font-semibold text-member-navy-text">
          Total: {constancia.total}
        </div>
      </div>

      {constancia.puntos.length === 0 ? (
        <p className="text-sm text-member-muted">Aún no hay registros de asistencia para mostrar.</p>
      ) : (
        <div className="flex items-end gap-2 h-40 mt-4">
          {constancia.puntos.map((punto) => {
            const altura = Math.max(8, (punto.asistencias / maximo) * 100);
            const etiqueta = new Date(`${punto.fecha}T00:00:00`).toLocaleDateString('es-CO', {
              weekday: periodo === 'semana' ? 'short' : undefined,
              day: 'numeric',
            });

            return (
              <div key={punto.fecha} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full h-28 bg-gray-100 rounded-md flex items-end p-1">
                  <div
                    className="w-full rounded-sm bg-member-success"
                    style={{ height: `${altura}%` }}
                    title={`${punto.asistencias} asistencia${punto.asistencias === 1 ? '' : 's'}`}
                  />
                </div>
                <div className="text-center">
                  <div className="text-[11px] font-semibold text-member-navy-text uppercase">
                    {etiqueta}
                  </div>
                  <div className="text-xs text-member-muted">{punto.asistencias}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function PortalDashboard() {
  const { nombre, logout } = useMemberAuth();
  const navigate = useNavigate();
  const [periodoConstancia, setPeriodoConstancia] = useState<AttendanceConsistency['periodo']>('semana');
  const { data: resumen, isPending, isError } = useQuery({
    queryKey: ['portal', 'resumen'],
    queryFn: getMembershipSummary,
  });
  const { data: constancia, isPending: isPendingConstancia, isError: isErrorConstancia } = useQuery({
    queryKey: ['portal', 'constancia', periodoConstancia],
    queryFn: () => getAttendanceConsistency(periodoConstancia),
    enabled: Boolean(resumen),
  });

  function handleLogout() {
    logout();
    navigate('/portal/login', { replace: true });
  }

  return (
    <div className="min-h-screen bg-member-bg">
      <div className="max-w-3xl mx-auto p-6">
        <header className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-member-navy text-2xl font-bold">
              Hola{nombre ? `, ${nombre}` : ''} 👋
            </h1>
            <p className="text-member-muted text-sm mt-1">Este es el estado de tu membresía.</p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="text-member-muted text-sm underline min-h-12 px-2"
          >
            Cerrar sesión
          </button>
        </header>

        {isPending && <p className="text-member-muted">Cargando tu resumen…</p>}
        {isError && (
          <p className="text-member-error">No pudimos cargar tu resumen. Intenta de nuevo.</p>
        )}

        {resumen && (
          <>
            <AvisoVencimiento resumen={resumen} />

            <button
              type="button"
              onClick={() => navigate('/portal/escaner')}
              className="w-full min-h-[56px] mb-6 bg-member-navy text-white rounded-card flex items-center justify-center gap-2 text-lg font-semibold"
            >
              <span aria-hidden="true">📷</span>
              Escanear pase de acceso
            </button>

            <section className="bg-white rounded-card shadow-sm border border-gray-100 p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-member-navy-text font-semibold">Mi membresía</h2>
                <span
                  className={`text-xs font-semibold px-3 py-1 rounded-full ${ESTADO_BADGE[resumen.estado].clases}`}
                >
                  {ESTADO_BADGE[resumen.estado].texto}
                </span>
              </div>

              {resumen.estado === 'sin_plan' ? (
                <p className="text-member-muted text-sm">
                  Aún no tienes un plan asignado. Acércate a recepción para elegir tu membresía.
                </p>
              ) : (
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-member-muted">Tipo de plan</dt>
                    <dd className="text-member-navy-text font-semibold text-lg">
                      {resumen.tipo ?? '—'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-member-muted">
                      {resumen.estado === 'vencida' ? 'Venció el' : 'Vence el'}
                    </dt>
                    <dd className="text-member-navy-text font-semibold text-lg">
                      {formatearFecha(resumen.fecha_vencimiento)}
                    </dd>
                  </div>
                </dl>
              )}
            </section>

            {resumen.estado === 'activa' && (
              <>
                <section className="grid grid-cols-2 gap-4 mb-6">
                  <StatCard
                    valor={String(resumen.visitas_restantes ?? '—')}
                    etiqueta="Visitas restantes"
                    clases="bg-member-success text-white"
                  />
                  <StatCard
                    valor={String(resumen.cupo_invitados_restantes ?? '—')}
                    etiqueta="Cupos de invitado"
                    clases="bg-member-purple text-white"
                  />
                </section>

                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-member-navy-text font-semibold">Constancia</h2>
                  <div className="inline-flex rounded-full bg-gray-100 p-1">
                    {(['semana', 'mes'] as AttendanceConsistency['periodo'][]).map((opcion) => (
                      <button
                        key={opcion}
                        type="button"
                        onClick={() => setPeriodoConstancia(opcion)}
                        className={`rounded-full px-3 py-1 text-sm font-medium ${
                          periodoConstancia === opcion
                            ? 'bg-member-success text-white'
                            : 'text-member-muted'
                        }`}
                      >
                        {opcion === 'semana' ? 'Semana' : 'Mes'}
                      </button>
                    ))}
                  </div>
                </div>

                {isPendingConstancia && (
                  <p className="text-member-muted text-sm">Cargando tu constancia…</p>
                )}
                {isErrorConstancia && (
                  <p className="text-member-error text-sm">No pudimos cargar tu constancia.</p>
                )}
                {constancia && <GraficoConstancia constancia={constancia} periodo={periodoConstancia} />}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default PortalDashboard;
