import { isAxiosError } from 'axios';
import { useMutation } from '@tanstack/react-query';
import { useEffect, useRef, useState, type FormEvent } from 'react';

import {
  DispositivoBloqueadoError,
  checkinGuest,
  postCheckin,
  type CheckinResponse,
} from '../api/checkin';
import NumericKeypad from './NumericKeypad';

const REINICIO_MS = 4000;

type Resultado = CheckinResponse | { resultado: 'denegado'; mensaje: string; razon: null };
type Modo = 'socio' | 'invitado';

function CheckinKiosk() {
  const [modo, setModo] = useState<Modo>('socio');
  const [cedula, setCedula] = useState('');
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [bloqueadoHasta, setBloqueadoHasta] = useState<Date | null>(null);
  const reinicioRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function onErrorCheckin(error: unknown) {
    if (error instanceof DispositivoBloqueadoError) {
      setBloqueadoHasta(error.bloqueadoHasta);
      setCedula('');
      return;
    }
    const noEncontrado = isAxiosError(error) && error.response?.status === 404;
    mostrarResultado({
      resultado: 'denegado',
      mensaje: noEncontrado
        ? 'Cédula no registrada. Dirígete a recepción.'
        : 'No se pudo validar el ingreso. Intenta de nuevo.',
      razon: null,
    });
  }

  const mutation = useMutation({
    mutationFn: postCheckin,
    onSuccess: (data) => mostrarResultado(data),
    onError: onErrorCheckin,
  });

  const guestMutation = useMutation({
    mutationFn: checkinGuest,
    onSuccess: (data) => {
      setModo('socio');
      mostrarResultado(data);
    },
    onError: onErrorCheckin,
  });

  function mostrarResultado(data: Resultado) {
    setResultado(data);
    setCedula('');
    reinicioRef.current = setTimeout(() => setResultado(null), REINICIO_MS);
  }

  function handleSubmit() {
    if (cedula.length === 0 || mutation.isPending) return;
    mutation.mutate(cedula);
  }

  if (bloqueadoHasta) {
    return <PantallaBloqueo hasta={bloqueadoHasta} onExpira={() => setBloqueadoHasta(null)} />;
  }

  if (resultado) {
    const exitoso = resultado.resultado === 'exitoso';
    return (
      <div
        className={`min-h-screen flex items-center justify-center p-8 ${
          exitoso ? 'bg-green-600' : 'bg-red-600'
        }`}
      >
        <p className="text-white text-4xl font-bold text-center leading-snug">
          {resultado.mensaje}
        </p>
      </div>
    );
  }

  if (modo === 'invitado') {
    return (
      <GuestForm
        pending={guestMutation.isPending}
        onCancel={() => setModo('socio')}
        onSubmit={(input) => guestMutation.mutate(input)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-member-bg flex items-center justify-center p-8">
      <div className="bg-white rounded-card shadow-md p-10 w-full max-w-md text-center">
        <h1 className="text-member-navy-text text-2xl font-bold">GymFlow</h1>
        <p className="text-member-muted mt-1 mb-6">Ingresa tu número de cédula</p>

        <div className="h-16 rounded-card bg-member-bg text-member-navy-text text-3xl font-mono flex items-center justify-center tracking-widest mb-6">
          {cedula || '—'}
        </div>

        <NumericKeypad
          disabled={mutation.isPending}
          onDigit={(d) => setCedula((prev) => (prev.length < 20 ? prev + d : prev))}
          onBackspace={() => setCedula((prev) => prev.slice(0, -1))}
          onSubmit={handleSubmit}
        />

        <button
          type="button"
          onClick={() => setModo('invitado')}
          className="mt-6 w-full min-h-[48px] rounded-card border-2 border-member-navy text-member-navy text-lg font-semibold hover:bg-member-navy hover:text-white"
        >
          Ingresar un invitado
        </button>
      </div>
    </div>
  );
}

function GuestForm({
  pending,
  onCancel,
  onSubmit,
}: {
  pending: boolean;
  onCancel: () => void;
  onSubmit: (input: {
    cedulaTitular: string;
    cedulaInvitado: string;
    nombreInvitado: string;
  }) => void;
}) {
  const [cedulaTitular, setCedulaTitular] = useState('');
  const [cedulaInvitado, setCedulaInvitado] = useState('');
  const [nombreInvitado, setNombreInvitado] = useState('');

  const listo =
    cedulaTitular.trim().length > 0 &&
    cedulaInvitado.trim().length > 0 &&
    nombreInvitado.trim().length > 0;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!listo || pending) return;
    onSubmit({
      cedulaTitular: cedulaTitular.trim(),
      cedulaInvitado: cedulaInvitado.trim(),
      nombreInvitado: nombreInvitado.trim(),
    });
  }

  return (
    <div className="min-h-screen bg-member-bg flex items-center justify-center p-8">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-card shadow-md p-10 w-full max-w-md"
      >
        <h1 className="text-member-navy-text text-2xl font-bold text-center">Ingreso de invitado</h1>
        <p className="text-member-muted text-center mt-1 mb-6">
          El socio titular debe estar presente y registrar a su invitado.
        </p>

        <label className="block text-sm text-member-navy-text font-medium mb-1" htmlFor="ct">
          Cédula del socio titular
        </label>
        <input
          id="ct"
          inputMode="numeric"
          value={cedulaTitular}
          onChange={(e) => setCedulaTitular(e.target.value)}
          className="w-full min-h-[48px] border-2 border-gray-300 rounded-card px-3 text-xl mb-4"
        />

        <label className="block text-sm text-member-navy-text font-medium mb-1" htmlFor="ci">
          Cédula del invitado
        </label>
        <input
          id="ci"
          inputMode="numeric"
          value={cedulaInvitado}
          onChange={(e) => setCedulaInvitado(e.target.value)}
          className="w-full min-h-[48px] border-2 border-gray-300 rounded-card px-3 text-xl mb-4"
        />

        <label className="block text-sm text-member-navy-text font-medium mb-1" htmlFor="ni">
          Nombre del invitado
        </label>
        <input
          id="ni"
          value={nombreInvitado}
          onChange={(e) => setNombreInvitado(e.target.value)}
          className="w-full min-h-[48px] border-2 border-gray-300 rounded-card px-3 text-xl mb-6"
        />

        <button
          type="submit"
          disabled={!listo || pending}
          className="w-full min-h-[56px] rounded-card bg-member-navy text-white text-xl font-semibold disabled:opacity-50"
        >
          Registrar ingreso
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="mt-3 w-full min-h-[48px] rounded-card border-2 border-gray-300 text-member-muted text-lg font-medium hover:bg-gray-50"
        >
          Volver
        </button>
      </form>
    </div>
  );
}

function PantallaBloqueo({ hasta, onExpira }: { hasta: Date; onExpira: () => void }) {
  const [restanteMs, setRestanteMs] = useState(() => hasta.getTime() - Date.now());

  useEffect(() => {
    const id = setInterval(() => {
      const restante = hasta.getTime() - Date.now();
      setRestanteMs(restante);
      if (restante <= 0) onExpira();
    }, 1000);
    return () => clearInterval(id);
  }, [hasta, onExpira]);

  const totalSeg = Math.max(0, Math.ceil(restanteMs / 1000));
  const minutos = String(Math.floor(totalSeg / 60)).padStart(2, '0');
  const segundos = String(totalSeg % 60).padStart(2, '0');

  return (
    <div className="min-h-screen bg-red-700 flex flex-col items-center justify-center p-8 gap-6">
      <p className="text-white text-3xl font-bold text-center">
        Dispositivo bloqueado temporalmente.
      </p>
      <p className="text-white/90 text-xl text-center">
        Demasiados intentos fallidos. Intenta de nuevo en:
      </p>
      <p className="text-white text-6xl font-mono font-bold tabular-nums">
        {minutos}:{segundos}
      </p>
    </div>
  );
}

export default CheckinKiosk;
