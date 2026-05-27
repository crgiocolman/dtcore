import { useEffect, useState } from 'react'
import { Check, FolderOpen, Pencil, Plus, Trash2, X } from 'lucide-react'
import {
  createCategory,
  deleteCategory,
  fetchCategoryTree,
  updateCategory,
  type CategoryTreeNode,
} from '../api/categories'

// ---- Helpers ----

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return 'Error desconocido'
  try {
    const parsed = JSON.parse(err.message)
    return parsed?.detail ?? err.message
  } catch {
    return err.message
  }
}

function replaceNode(
  tree: CategoryTreeNode[],
  id: string,
  updater: (n: CategoryTreeNode) => CategoryTreeNode,
): CategoryTreeNode[] {
  return tree.map((n) => {
    if (n.id === id) return updater(n)
    const updated = replaceNode(n.children, id, updater)
    if (updated === n.children) return n
    return { ...n, children: updated }
  })
}

function removeNode(tree: CategoryTreeNode[], id: string): CategoryTreeNode[] {
  return tree
    .filter((n) => n.id !== id)
    .map((n) => ({ ...n, children: removeNode(n.children, id) }))
}

function appendChild(
  tree: CategoryTreeNode[],
  parentId: string | null,
  node: CategoryTreeNode,
): CategoryTreeNode[] {
  if (!parentId) return [...tree, node]
  return tree.map((n) => {
    if (n.id === parentId) return { ...n, children: [...n.children, node] }
    return { ...n, children: appendChild(n.children, parentId, node) }
  })
}

// ---- Context object passed down the tree ----

interface TreeCtx {
  editingId: string | null
  editingName: string
  addingParentId: string | null // '' = root, uuid = child
  addingName: string
  deletingId: string | null
  busy: boolean
  onStartEdit: (node: CategoryTreeNode) => void
  onEditChange: (v: string) => void
  onSaveEdit: (id: string) => void
  onCancelEdit: () => void
  onStartAdd: (parentId: string) => void
  onAddChange: (v: string) => void
  onSaveAdd: (parentId: string) => void
  onCancelAdd: () => void
  onStartDelete: (id: string) => void
  onConfirmDelete: (id: string) => void
  onCancelDelete: () => void
}

// ---- AddRow ----

function AddRow({
  parentId,
  depth,
  ctx,
}: {
  parentId: string
  depth: number
  ctx: TreeCtx
}) {
  return (
    <form
      className="flex items-center gap-1.5 py-1"
      style={{ paddingLeft: 12 + depth * 20, paddingRight: 8 }}
      onSubmit={(e) => {
        e.preventDefault()
        ctx.onSaveAdd(parentId)
      }}
    >
      <input
        className="input h-8 flex-1 max-w-xs py-1 text-sm"
        type="text"
        placeholder="Nombre de la categoría"
        value={ctx.addingName}
        onChange={(e) => ctx.onAddChange(e.target.value)}
        autoFocus
        disabled={ctx.busy}
      />
      <button
        type="submit"
        className="btn-ghost px-2 py-1"
        disabled={ctx.busy || !ctx.addingName.trim()}
        aria-label="Confirmar"
      >
        <Check className="h-4 w-4 text-success-500" />
      </button>
      <button
        type="button"
        className="btn-ghost px-2 py-1"
        onClick={ctx.onCancelAdd}
        disabled={ctx.busy}
        aria-label="Cancelar"
      >
        <X className="h-4 w-4" />
      </button>
    </form>
  )
}

// ---- CategoryNode ----

function CategoryNode({
  node,
  depth,
  ctx,
}: {
  node: CategoryTreeNode
  depth: number
  ctx: TreeCtx
}) {
  const isEditing = ctx.editingId === node.id
  const isDeleting = ctx.deletingId === node.id
  const isAdding = ctx.addingParentId === node.id

  return (
    <div>
      {/* Node row */}
      <div
        className="group flex items-center gap-2 rounded-md py-1.5 transition-colors hover:bg-bg-elevated/50"
        style={{ paddingLeft: 12 + depth * 20, paddingRight: 8 }}
      >
        {isEditing ? (
          <form
            className="flex flex-1 items-center gap-1.5"
            onSubmit={(e) => {
              e.preventDefault()
              ctx.onSaveEdit(node.id)
            }}
          >
            <input
              className="input h-8 flex-1 max-w-xs py-1 text-sm"
              type="text"
              value={ctx.editingName}
              onChange={(e) => ctx.onEditChange(e.target.value)}
              autoFocus
              disabled={ctx.busy}
            />
            <button
              type="submit"
              className="btn-ghost px-2 py-1"
              disabled={ctx.busy || !ctx.editingName.trim()}
              aria-label="Guardar"
            >
              <Check className="h-4 w-4 text-success-500" />
            </button>
            <button
              type="button"
              className="btn-ghost px-2 py-1"
              onClick={ctx.onCancelEdit}
              disabled={ctx.busy}
              aria-label="Cancelar"
            >
              <X className="h-4 w-4" />
            </button>
          </form>
        ) : isDeleting ? (
          <>
            <span
              className={`flex-1 text-sm ${
                node.is_active ? 'text-text-primary' : 'text-text-muted line-through'
              }`}
            >
              {node.name}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">¿Eliminar?</span>
              <button
                type="button"
                className="btn-danger px-2 py-0.5 text-xs"
                disabled={ctx.busy}
                onClick={() => ctx.onConfirmDelete(node.id)}
              >
                {ctx.busy ? '…' : 'Sí'}
              </button>
              <button
                type="button"
                className="btn-ghost px-2 py-0.5 text-xs"
                onClick={ctx.onCancelDelete}
                disabled={ctx.busy}
              >
                No
              </button>
            </div>
          </>
        ) : (
          <>
            <span
              className={`flex-1 select-none text-sm ${
                node.is_active ? 'text-text-primary' : 'text-text-muted line-through'
              }`}
            >
              {node.name}
            </span>
            <div className="flex items-center gap-0.5 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100">
              <button
                type="button"
                className="btn-ghost px-2 py-1"
                aria-label={`Renombrar ${node.name}`}
                onClick={() => ctx.onStartEdit(node)}
                disabled={ctx.busy}
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                className="btn-ghost px-2 py-1"
                aria-label={`Agregar subcategoría en ${node.name}`}
                onClick={() => ctx.onStartAdd(node.id)}
                disabled={ctx.busy}
              >
                <Plus className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                className="btn-ghost px-2 py-1 text-danger-500"
                aria-label={`Eliminar ${node.name}`}
                onClick={() => ctx.onStartDelete(node.id)}
                disabled={ctx.busy}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </>
        )}
      </div>

      {/* Children */}
      {node.children.map((child) => (
        <CategoryNode key={child.id} node={child} depth={depth + 1} ctx={ctx} />
      ))}

      {/* Add child row (shown below last child when user clicks Plus on this node) */}
      {isAdding && <AddRow parentId={node.id} depth={depth + 1} ctx={ctx} />}
    </div>
  )
}

// ---- Page ----

export function Categories() {
  const [tree, setTree] = useState<CategoryTreeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')
  const [addingParentId, setAddingParentId] = useState<string | null>(null)
  const [addingName, setAddingName] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchCategoryTree()
      .then(setTree)
      .catch((err) => setApiError(parseApiError(err)))
      .finally(() => setLoading(false))
  }, [])

  function cancelAll() {
    setEditingId(null)
    setEditingName('')
    setAddingParentId(null)
    setAddingName('')
    setDeletingId(null)
    setApiError(null)
  }

  async function handleSaveEdit(id: string) {
    if (!editingName.trim()) return
    setBusy(true)
    setApiError(null)
    try {
      const updated = await updateCategory(id, { name: editingName.trim() })
      setTree((prev) =>
        replaceNode(prev, id, (n) => ({ ...n, name: updated.name, is_active: updated.is_active })),
      )
      setEditingId(null)
      setEditingName('')
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setBusy(false)
    }
  }

  async function handleSaveAdd(parentId: string) {
    if (!addingName.trim()) return
    setBusy(true)
    setApiError(null)
    const resolvedParentId = parentId === '' ? null : parentId
    try {
      const created = await createCategory({
        id: crypto.randomUUID(),
        name: addingName.trim(),
        parent_id: resolvedParentId,
        is_active: true,
      })
      const newNode: CategoryTreeNode = {
        id: created.id,
        name: created.name,
        parent_id: created.parent_id,
        is_active: created.is_active,
        children: [],
      }
      setTree((prev) => appendChild(prev, resolvedParentId, newNode))
      setAddingParentId(null)
      setAddingName('')
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setBusy(false)
    }
  }

  async function handleConfirmDelete(id: string) {
    setBusy(true)
    setApiError(null)
    try {
      await deleteCategory(id)
      setTree((prev) => removeNode(prev, id))
      setDeletingId(null)
    } catch (err) {
      setApiError(parseApiError(err))
      setDeletingId(null)
    } finally {
      setBusy(false)
    }
  }

  const ctx: TreeCtx = {
    editingId,
    editingName,
    addingParentId,
    addingName,
    deletingId,
    busy,
    onStartEdit: (node) => {
      cancelAll()
      setEditingId(node.id)
      setEditingName(node.name)
    },
    onEditChange: setEditingName,
    onSaveEdit: handleSaveEdit,
    onCancelEdit: () => {
      setEditingId(null)
      setEditingName('')
      setApiError(null)
    },
    onStartAdd: (parentId) => {
      cancelAll()
      setAddingParentId(parentId)
      setAddingName('')
    },
    onAddChange: setAddingName,
    onSaveAdd: handleSaveAdd,
    onCancelAdd: () => {
      setAddingParentId(null)
      setAddingName('')
      setApiError(null)
    },
    onStartDelete: (id) => {
      cancelAll()
      setDeletingId(id)
    },
    onConfirmDelete: handleConfirmDelete,
    onCancelDelete: () => {
      setDeletingId(null)
      setApiError(null)
    },
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-shrink-0 items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Categorías</h1>
          <p className="mt-1 text-sm text-text-secondary">Organización jerárquica de productos</p>
        </div>
        <button
          className="btn-primary flex flex-shrink-0 items-center gap-1.5"
          disabled={busy}
          onClick={() => {
            cancelAll()
            setAddingParentId('')
          }}
        >
          <Plus className="h-4 w-4" />
          Nueva categoría
        </button>
      </div>

      {/* Error banner */}
      {apiError && (
        <div className="mb-4 flex flex-shrink-0 items-center justify-between rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
          <span>{apiError}</span>
          <button
            type="button"
            onClick={() => setApiError(null)}
            className="ml-4 shrink-0"
            aria-label="Cerrar error"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Tree card */}
      <div className="card flex min-h-0 flex-1 flex-col overflow-hidden p-0">
        {loading ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <p className="text-sm text-text-muted">Cargando…</p>
          </div>
        ) : tree.length === 0 && addingParentId === null ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
            <FolderOpen className="h-12 w-12 text-text-muted" />
            <p className="text-sm text-text-muted">No hay categorías registradas</p>
            <button
              className="btn-secondary flex items-center gap-1.5 text-sm"
              onClick={() => setAddingParentId('')}
            >
              <Plus className="h-4 w-4" />
              Agregar primera categoría
            </button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto py-2">
            {tree.map((node) => (
              <CategoryNode key={node.id} node={node} depth={0} ctx={ctx} />
            ))}
            {addingParentId === '' && <AddRow parentId="" depth={0} ctx={ctx} />}
          </div>
        )}
      </div>
    </div>
  )
}
