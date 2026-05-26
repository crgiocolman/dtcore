import { ChevronLeft, ChevronRight, Plus, Search, Users } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { ContactType } from '../api/contacts'
import { useContacts } from '../hooks/useContacts'

const CONTACT_TYPE_LABELS: Record<ContactType | '', string> = {
  '': 'Todos',
  customer: 'Clientes',
  supplier: 'Proveedores',
  both: 'Cliente y proveedor',
}

const CONTACT_TYPE_BADGE: Record<ContactType, string> = {
  customer: 'text-primary-500',
  supplier: 'text-success-500',
  both: 'text-warning-500',
}

export function ContactsList() {
  const navigate = useNavigate()
  const {
    data,
    loading,
    error,
    page,
    search,
    contactType,
    setPage,
    setSearch,
    setContactType,
  } = useContacts()

  const items = data?.items ?? []
  const totalPages = data?.total_pages ?? 1
  const total = data?.total ?? 0

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Contactos</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Clientes, proveedores y ambos
          </p>
        </div>
        <button
          className="btn-primary flex flex-shrink-0 items-center gap-1.5"
          onClick={() => navigate('/contactos/nuevo')}
        >
          <Plus className="h-4 w-4" />
          Nuevo contacto
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            className="input pl-9"
            type="text"
            placeholder="Buscar por nombre o documento…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="input w-auto min-w-[180px]"
          value={contactType}
          onChange={(e) => setContactType(e.target.value as ContactType | '')}
        >
          {(Object.keys(CONTACT_TYPE_LABELS) as Array<ContactType | ''>).map((key) => (
            <option key={key} value={key}>
              {CONTACT_TYPE_LABELS[key]}
            </option>
          ))}
        </select>
      </div>

      <div className="card flex min-h-0 flex-1 flex-col p-0 overflow-hidden">
        {error ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-danger-500">{error}</p>
          </div>
        ) : loading && items.length === 0 ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-text-muted">Cargando…</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
            <Users className="h-12 w-12 text-text-muted" />
            <p className="text-sm text-text-muted">
              {search || contactType ? 'Sin resultados para los filtros aplicados' : 'No hay contactos registrados'}
            </p>
            {!search && !contactType && (
              <button
                className="btn-secondary flex items-center gap-1.5 text-sm"
                onClick={() => navigate('/contactos/nuevo')}
              >
                <Plus className="h-4 w-4" />
                Agregar primer contacto
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-bg-surface">
                  <tr className="border-b border-border-subtle">
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Nombre / Razón social</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Documento</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Tipo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Teléfono</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {items.map((c) => (
                    <tr
                      key={c.id}
                      className="cursor-pointer hover:bg-bg-elevated/50 transition-colors"
                      onClick={() => navigate(`/contactos/${c.id}`)}
                    >
                      <td className="px-4 py-3 text-text-primary">
                        <span className="font-medium">{c.business_name}</span>
                        {c.trade_name && (
                          <span className="ml-1.5 text-xs text-text-muted">({c.trade_name})</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-text-secondary tabular-nums">
                        {c.document_number ? (
                          <>
                            <span className="text-xs text-text-muted uppercase">{c.document_type} </span>
                            {c.document_number}
                          </>
                        ) : (
                          <span className="text-text-muted">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${CONTACT_TYPE_BADGE[c.contact_type]}`}>
                          {CONTACT_TYPE_LABELS[c.contact_type]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-text-secondary">
                        {c.phone ?? <span className="text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3 text-text-secondary">
                        {c.email ?? <span className="text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs font-medium ${c.is_active ? 'text-success-500' : 'text-text-muted'}`}
                        >
                          {c.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-border-subtle px-4 py-3">
              <p className="text-xs text-text-muted">
                {total} {total === 1 ? 'registro' : 'registros'}
              </p>
              <div className="flex items-center gap-2">
                <button
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  aria-label="Página anterior"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-text-secondary tabular-nums">
                  {page} / {totalPages}
                </span>
                <button
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  aria-label="Página siguiente"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
