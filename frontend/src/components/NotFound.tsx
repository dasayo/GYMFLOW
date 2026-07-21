import { Link } from 'react-router';

function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-gray-100">
      <div className="bg-white rounded-lg shadow p-8 w-full max-w-sm text-center border border-gray-200">
        <h1 className="text-gray-900 text-xl font-semibold mb-2">Página no encontrada</h1>
        <p className="text-gray-500 text-sm mb-6">
          La página que buscas no existe o fue movida.
        </p>
        <Link
          to="/"
          className="inline-block bg-gray-900 text-white rounded px-4 py-2 font-medium"
        >
          Volver al inicio
        </Link>
      </div>
    </div>
  );
}

export default NotFound;
