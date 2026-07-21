import { isAxiosError } from 'axios';
import { useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import QRCode from 'react-qr-code';

import {
  DispositivoBloqueadoError,
  DispositivoNoAutorizadoError,
  checkinGuest,
  getDeviceId,
  postCheckin,
  postQrNonce,
  type CheckinResponse,
} from '../api/checkin';
import NumericKeypad from './NumericKeypad';

const REINICIO_MS = 4000;

type Resultado = CheckinResponse | { resultado: 'denegado'; mensaje: string; razon: null };
type Modo = 'qr' | 'cedula' | 'invitado';

interface MensajeWs {
  tipo: 'nonce' | 'resultado';
  nonce?: string;
  expira_en?: string;
  resultado?: CheckinResponse['resultado'];
  mensaje?: string;
  nombre?: string | null;
  visitas_restantes?: number | null;
  razon?: CheckinResponse['razon'];
}

function CheckinKiosk() {
  const [autorizado, setAutorizado] = useState<boolean | null>(null);
  const [modo, setModo] = useState<Modo>('qr');
  const [cedula, setCedula] = useState('');
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [bloqueadoHasta, setBloqueadoHasta] = useState<Date | null>(null);
  const [nonce, setNonce] = useState<string | null>(null);
  const [qrError, setQrError] = useState<string | null>(null);
  const reinicioRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

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
      setModo('qr');
      mostrarResultado(data);
    },
    onError: onErrorCheckin,
  });

  const mostrarResultado = useCallback((data: Resultado) => {
    setResultado(data);
    setCedula('');
    if (reinicioRef.current) clearTimeout(reinicioRef.current);
    reinicioRef.current = setTimeout(() => {
      setResultado(null);
      setModo('qr');
    }, REINICIO_MS);
  }, []);

  const pedirNonce = useCallback(async () => {
    try {
      setQrError(null);
      const data = await postQrNonce();
      setAutorizado(true);
      setNonce(data.nonce);
    } catch (error) {
      if (error instanceof DispositivoNoAutorizadoError) {
        setAutorizado(false);
        return;
      }
      setAutorizado(true);
      setQrError('Sin conexión con el servidor. Usa el ingreso por cédula.');
    }
  }, []);

  useEffect(() => {
    pedirNonce();
  }, [pedirNonce]);

  // Conexión persistente al kiosko (012-checkin-qr-dinamico): recibe tanto
  // la rotación del QR como el resultado del check-in, sin reconectar en
  // cada rotación (el `device_id` es la clave, no el nonce).
  useEffect(() => {
    if (autorizado !== true) return;

    let cerradoIntencional = false;

    function conectar() {
      const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${protocolo}://${window.location.host}/api/checkin/ws/${getDeviceId()}`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data) as MensajeWs;
        if (data.tipo === 'nonce' && data.nonce) {
          setNonce(data.nonce);
        } else if (data.tipo === 'resultado' && data.resultado && data.mensaje) {
          mostrarResultado({
            resultado: data.resultado,
            mensaje: data.mensaje,
            nombre: data.nombre ?? null,
            visitas_restantes: data.visitas_restantes ?? null,
            razon: data.razon ?? null,
          });
        }
      };

      ws.onclose = () => {
        if (cerradoIntencional) return;
        setTimeout(conectar, 2000);
      };
    }

    conectar();

    return () => {
      cerradoIntencional = true;
      wsRef.current?.close();
    };
  }, [autorizado, mostrarResultado]);

  function handleSubmit() {
    if (cedula.length === 0 || mutation.isPending) return;
    mutation.mutate(cedula);
  }

  if (autorizado === null) {
    return (
      <div className="min-h-screen bg-member-bg flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-member-navy-text" />
      </div>
    );
  }

  if (autorizado === false) {
    return <PantallaNoAutorizado onReintentar={pedirNonce} />;
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
        onCancel={() => setModo('qr')}
        onSubmit={(input) => guestMutation.mutate(input)}
      />
    );
  }

  if (modo === 'cedula') {
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
          <button
            type="button"
            onClick={() => setModo('qr')}
            className="mt-3 w-full min-h-[48px] rounded-card border-2 border-gray-300 text-member-muted text-lg font-medium hover:bg-gray-50"
          >
            Volver al código QR
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-member-bg flex items-center justify-center p-8">
      <div className="bg-white rounded-card shadow-md p-10 w-full max-w-md text-center flex flex-col items-center">
        <h1 className="text-member-navy-text text-2xl font-bold">GymFlow</h1>
        <p className="text-member-muted mt-1 mb-6">Escanea el código desde tu portal</p>

        <div className="bg-member-bg p-4 rounded-card border border-gray-100 flex items-center justify-center w-64 h-64">
          {qrError ? (
            <p className="text-member-error font-semibold text-center px-2">{qrError}</p>
          ) : !nonce ? (
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-member-navy-text" />
          ) : (
            <QRCode
              value={JSON.stringify({ device_id: getDeviceId(), nonce })}
              size={220}
              style={{ height: 'auto', maxWidth: '100%', width: '100%' }}
            />
          )}
        </div>
        <p className="text-member-muted text-xs mt-4 uppercase tracking-widest">
          Se actualiza automáticamente
        </p>

        <button
          type="button"
          onClick={() => setModo('cedula')}
          className="mt-6 w-full min-h-[48px] rounded-card border-2 border-member-navy text-member-navy text-lg font-semibold hover:bg-member-navy hover:text-white"
        >
          Ingresar con cédula
        </button>
      </div>
    </div>
  );
}

function PantallaNoAutorizado({ onReintentar }: { onReintentar: () => void }) {
  return (
    <div className="min-h-screen bg-member-bg flex items-center justify-center p-8">
      <div className="bg-white rounded-card shadow-md p-10 w-full max-w-md text-center">
        <h1 className="text-member-navy-text text-2xl font-bold">Dispositivo no autorizado</h1>
        <p className="text-member-muted mt-2 mb-6">
          Un administrador debe autorizar este dispositivo antes de usarlo como kiosko.
        </p>
        <p className="text-member-muted text-sm mb-1">ID de este dispositivo:</p>
        <p className="font-mono text-sm bg-member-bg rounded-card px-3 py-2 mb-6 break-all">
          {getDeviceId()}
        </p>
        <button
          type="button"
          onClick={onReintentar}
          className="w-full min-h-[48px] rounded-card bg-member-navy text-white text-lg font-semibold"
        >
          Reintentar
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
