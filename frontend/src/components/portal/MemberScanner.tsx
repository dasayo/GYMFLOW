import { isAxiosError } from 'axios';
import { useState } from 'react';
import { Scanner, type IDetectedBarcode, type IScannerError } from '@yudiel/react-qr-scanner';
import { useNavigate } from 'react-router';

import { postEscanearQr } from '../../api/portal';

type Estado = 'escaneando' | 'procesando' | 'exito' | 'error';

// Mismo payload que codifica CheckinKiosk.tsx: { device_id, nonce }.
interface QrPayload {
  device_id: string;
  nonce: string;
}

function parsearQr(texto: string): QrPayload | null {
  try {
    const data = JSON.parse(texto) as Partial<QrPayload>;
    if (typeof data.device_id === 'string' && typeof data.nonce === 'string') {
      return { device_id: data.device_id, nonce: data.nonce };
    }
  } catch {
    // No era JSON válido — se trata como QR ajeno, se ignora.
  }
  return null;
}

// Este flujo lo usa un socio real desde su celular (no un admin en
// escritorio): pantalla a ancho completo, sin max-width de tarjeta como el
// resto del portal, controles con áreas táctiles grandes.
function MemberScanner() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState<Estado>('escaneando');
  const [mensaje, setMensaje] = useState<string | null>(null);

  async function handleScan(codigos: IDetectedBarcode[]) {
    if (estado !== 'escaneando' || codigos.length === 0) return;
    const payload = parsearQr(codigos[0].rawValue);
    if (!payload) return;

    setEstado('procesando');
    try {
      const resp = await postEscanearQr(payload.device_id, payload.nonce);
      setEstado(resp.resultado === 'exitoso' ? 'exito' : 'error');
      setMensaje(resp.mensaje);
    } catch (error) {
      setEstado('error');
      setMensaje(
        isAxiosError(error) && error.response?.status === 400
          ? 'Este código ya no es válido. Pídele al kiosko uno nuevo.'
          : 'No se pudo validar el ingreso. Intenta de nuevo.',
      );
    }

    setTimeout(() => {
      setEstado('escaneando');
      setMensaje(null);
    }, 3000);
  }

  return (
    <div className="min-h-screen bg-black flex flex-col">
      <header className="bg-member-navy text-white px-4 py-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="min-h-[44px] min-w-[44px] flex items-center justify-center text-2xl"
          aria-label="Volver"
        >
          ←
        </button>
        <div>
          <h1 className="text-lg font-bold leading-tight">Escanear pase de acceso</h1>
          <p className="text-xs text-white/80">Apunta la cámara al código del kiosko</p>
        </div>
      </header>

      <div className="flex-1 relative flex items-center justify-center">
        {estado === 'escaneando' || estado === 'procesando' ? (
          <>
            <Scanner
              onScan={handleScan}
              onError={(error: IScannerError) => console.error(error.message)}
              components={{ finder: true }}
              styles={{ container: { width: '100%', height: '100%' } }}
            />
            {estado === 'procesando' && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white" />
              </div>
            )}
          </>
        ) : (
          <div className="text-center p-8 w-full">
            <span
              role="img"
              aria-label={estado === 'exito' ? 'Éxito' : 'Error'}
              className="block text-6xl mb-4"
            >
              {estado === 'exito' ? '✅' : '❌'}
            </span>
            <p className="text-white font-medium text-lg">{mensaje}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default MemberScanner;
