import { isAxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fragment, useEffect, useState, type FormEvent } from 'react';

import {
  createUser,
  deleteUser,
  listUsers,
  searchUsers,
  updateUser,
  type Rol,
  type UserCreate,
} from '../../api/members';
import { useAuth } from '../../context/useAuth';
import MembershipPanel from './MembershipPanel';

const QUERY_KEY = ['usuarios'];

function UsersPage() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const puedeGestionar = auth.hasPermission('members.gestionar_usuarios');
  const usuarios = useQuery({
    queryKey: QUERY_KEY,
    queryFn: listUsers,
    enabled: puedeGestionar,
  });
  const [seleccionadoId, setSeleccionadoId] = useState<number | null>(null);

  // 008: búsqueda por nombre o cédula (coincidencia parcial, un solo campo).
  const [busqueda, setBusqueda] = useState('');
  const [termino, setTermino] = useState('');

  // Debounce para no disparar una request por tecla. 300ms es latencia de
  // interfaz, no una regla de negocio del spec.
  useEffect(() => {
    const id = setTimeout(() => setTermino(busqueda.trim()), 300);
    return () => clearTimeout(id);
  }, [busqueda]);

  const buscando = termino.length > 0;
  // La queryKey cuelga de QUERY_KEY a propósito: React Query invalida por
  // prefijo, así que crear o eliminar un usuario también refresca los
  // resultados de búsqueda sin lógica extra.
  const resultados = useQuery({
    queryKey: [...QUERY_KEY, 'buscar', termino],
    queryFn: () => searchUsers(termino),
    enabled: puedeGestionar && buscando,
  });

  const listaVisible = buscando ? resultados.data : usuarios.data;
  const cargando = buscando ? resultados.isLoading : usuarios.isLoading;

  // Espejo de members.service.puede_asignar_rol (backend): solo para no
  // ofrecer una opción que el backend igual va a rechazar con 403. El
  // backend sigue siendo quien realmente lo exige.
  const rolesDisponibles: Rol[] =
    auth.rol === 'administrador'
      ? ['miembro', 'empleado', 'administrador']
      : auth.hasPermission('members.asignar_rol_empleado')
        ? ['miembro', 'empleado']
        : ['miembro'];

  const [form, setForm] = useState<UserCreate>({
    cedula: '', nombre: '', email: '', rol: 'miembro', password: '',
  });

  const crear = useMutation({
    mutationFn: () => createUser(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      setForm({ cedula: '', nombre: '', email: '', rol: 'miembro', password: '' });
    },
  });

  const editarNombre = useMutation({
    mutationFn: ({ id, nombre }: { id: number; nombre: string }) => updateUser(id, { nombre }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  const eliminar = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      setSeleccionadoId(null);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (crear.isPending) return;
    crear.mutate();
  }

  const requierePassword = form.rol === 'empleado' || form.rol === 'administrador';

  if (!puedeGestionar) {
    return (
      <div>
        <h1 className="text-member-navy-text text-2xl font-semibold mb-4">Usuarios</h1>
        <p className="text-red-600 bg-red-50 border border-red-200 rounded p-3">
          No tienes el permiso <code>members.gestionar_usuarios</code> — no puedes gestionar
          usuarios. Pídele a un administrador que te lo otorgue.
        </p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-member-navy-text text-2xl font-semibold mb-4">Usuarios</h1>

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-card shadow border border-gray-200 p-4 mb-6 flex flex-wrap items-end gap-3"
      >
        <div>
          <label className="block text-xs text-gray-600 mb-1" htmlFor="cedula">Cédula</label>
          <input
            id="cedula" required value={form.cedula}
            onChange={(e) => setForm({ ...form, cedula: e.target.value })}
            className="w-32 border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1" htmlFor="nombre">Nombre</label>
          <input
            id="nombre" required value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1" htmlFor="email">Email</label>
          <input
            id="email" type="email" value={form.email ?? ''}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-48 border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1" htmlFor="rol">Rol</label>
          <select
            id="rol" value={form.rol}
            onChange={(e) => setForm({ ...form, rol: e.target.value as Rol })}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            {rolesDisponibles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
        {requierePassword && (
          <div>
            <label className="block text-xs text-gray-600 mb-1" htmlFor="password">Contraseña</label>
            <input
              id="password" type="password" required value={form.password ?? ''}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-40 border border-gray-300 rounded px-2 py-1 text-sm"
            />
          </div>
        )}
        <button
          type="submit" disabled={crear.isPending}
          className="bg-member-navy text-white rounded px-3 py-1.5 text-sm disabled:opacity-50"
        >
          Crear usuario
        </button>
      </form>

      {crear.isError && (
        <p className="text-red-600 text-sm mb-4">
          {isAxiosError(crear.error) && crear.error.response?.status === 409
            ? 'Ya existe un usuario con esa cédula o email.'
            : 'No se pudo crear el usuario.'}
        </p>
      )}

      <div className="mb-4">
        <label className="block text-xs text-gray-600 mb-1" htmlFor="busqueda">
          Buscar por nombre o documento
        </label>
        <div className="flex items-center gap-2">
          <input
            id="busqueda"
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Ej. Laura, o 5554…"
            className="w-72 border border-gray-300 rounded px-2 py-1 text-sm"
          />
          {buscando && (
            <button
              type="button"
              onClick={() => setBusqueda('')}
              className="text-sm text-gray-600 border border-gray-300 rounded px-2 py-1 hover:bg-gray-50"
            >
              Limpiar
            </button>
          )}
        </div>
        {buscando && resultados.data && (
          <p className="text-xs text-gray-500 mt-1">
            {resultados.data.length === 0
              ? 'Sin coincidencias.'
              : `${resultados.data.length} resultado(s) para “${termino}”.`}
          </p>
        )}
      </div>

      {resultados.isError && (
        <p className="text-red-600 text-sm mb-4">No se pudo completar la búsqueda.</p>
      )}

      {cargando && <p className="text-gray-500">Cargando…</p>}

      {listaVisible && (
        <table className="w-full bg-white rounded-card shadow border border-gray-200 text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-200">
              <th className="p-3">Cédula</th>
              <th className="p-3">Nombre</th>
              <th className="p-3">Email</th>
              <th className="p-3">Rol</th>
              <th className="p-3">Estado</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {listaVisible.map((u) => (
              <Fragment key={u.id}>
                <tr
                  key={u.id}
                  className="border-b border-gray-100 last:border-0 cursor-pointer hover:bg-gray-50"
                  onClick={() => setSeleccionadoId(seleccionadoId === u.id ? null : u.id)}
                >
                  <td className="p-3 text-gray-900">{u.cedula ?? '—'}</td>
                  <td className="p-3 text-gray-900">{u.nombre ?? '—'}</td>
                  <td className="p-3 text-gray-900">{u.email ?? '—'}</td>
                  <td className="p-3 text-gray-900">{u.rol}</td>
                  <td className="p-3 text-gray-900">{u.estado}</td>
                  <td className="p-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        eliminar.mutate(u.id);
                      }}
                      className="text-sm text-red-600 border border-red-200 rounded px-2 py-1 hover:bg-red-50"
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
                {seleccionadoId === u.id && (
                  <tr>
                    <td colSpan={6} className="p-4 bg-member-bg">
                      <label className="block text-xs text-gray-600 mb-1" htmlFor={`nombre-${u.id}`}>
                        Editar nombre
                      </label>
                      <div className="flex gap-2 mb-2">
                        <input
                          id={`nombre-${u.id}`}
                          defaultValue={u.nombre ?? ''}
                          onBlur={(e) => {
                            if (e.target.value !== u.nombre) {
                              editarNombre.mutate({ id: u.id, nombre: e.target.value });
                            }
                          }}
                          className="w-56 border border-gray-300 rounded px-2 py-1 text-sm"
                        />
                      </div>
                      <MembershipPanel userId={u.id} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default UsersPage;
