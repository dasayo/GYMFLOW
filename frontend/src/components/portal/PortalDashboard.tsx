import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';

import { getMembershipSummary, type MembershipSummary } from '../../api/portal';
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

// Criterio de 007: aviso SOLO si quedan entre 0 y 10 días; con más de 10
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

function PortalDashboard() {
  const { nombre, logout } = useMemberAuth();
  const navigate = useNavigate();
  const { data: resumen, isPending, isError } = useQuery({
    queryKey: ['portal', 'resumen'],
    queryFn: getMembershipSummary,
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
              <section className="grid grid-cols-2 gap-4">
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
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default PortalDashboard;
