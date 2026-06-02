import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Trash2, X } from 'lucide-react'
import { parseApiError as _parseErr } from '../../../lib/parseApiError'
import {
  createContact,
  deleteContact,
  fetchContact,
  updateContact,
} from '../api/contacts'
import type { ContactOut, ContactType, DocumentType } from '../api/contacts'

// ---- Delete modal ----

interface DeleteModalProps {
  name: string
  deleting: boolean
  onConfirm: () => void
  onClose: () => void
}

function DeleteModal({ name, deleting, onConfirm, onClose }: DeleteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="card w-full max-w-sm space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-text-primary">Eliminar contacto</h3>
          <button type="button" onClick={onClose} className="btn-ghost p-1">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-sm text-text-secondary">
          ¿Eliminar{' '}
          <span className="font-medium text-text-primary">{name}</span>? Esta acción no se puede deshacer.
        </p>
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="btn-danger" onClick={onConfirm} disabled={deleting}>
            {deleting ? 'Eliminando…' : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---- Toggle ----

interface ToggleProps {
  checked: boolean
  onChange: (v: boolean) => void
}

function Toggle({ checked, onChange }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-bg-surface ${
        checked ? 'bg-primary-500' : 'border border-border bg-bg-elevated'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-text-primary shadow transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

// ---- Helpers ----

function parseApiError(err: unknown): string {
  return _parseErr(err).message
}

// ---- Form state ----

interface FormState {
  contact_type: ContactType
  business_name: string
  trade_name: string
  document_type: DocumentType
  document_number: string
  phone: string
  email: string
  address: string
  notes: string
  is_active: boolean
}

type FormErrors = Partial<Record<keyof FormState, string>>

const DEFAULT_FORM: FormState = {
  contact_type: 'customer',
  business_name: '',
  trade_name: '',
  document_type: 'none',
  document_number: '',
  phone: '',
  email: '',
  address: '',
  notes: '',
  is_active: true,
}

function fromContact(c: ContactOut): FormState {
  return {
    contact_type: c.contact_type,
    business_name: c.business_name,
    trade_name: c.trade_name ?? '',
    document_type: c.document_type,
    document_number: c.document_number ?? '',
    phone: c.phone ?? '',
    email: c.email ?? '',
    address: c.address ?? '',
    notes: c.notes ?? '',
    is_active: c.is_active,
  }
}

// ---- Page ----

export function ContactForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)

  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchContact(id)
      .then((c) => setForm(fromContact(c)))
      .catch((err) => setApiError(parseApiError(err)))
      .finally(() => setLoading(false))
  }, [id])

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const validate = (): boolean => {
    const errs: FormErrors = {}
    if (!form.business_name.trim()) errs.business_name = 'Campo requerido'
    if (form.document_type !== 'none' && !form.document_number.trim()) {
      errs.document_number = 'Requerido cuando se selecciona tipo de documento'
    }
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errs.email = 'Formato de email inválido'
    }
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    setSaving(true)
    setApiError(null)
    const docNumber = form.document_type !== 'none' ? form.document_number.trim() || null : null
    try {
      if (isEdit && id) {
        await updateContact(id, {
          contact_type: form.contact_type,
          business_name: form.business_name.trim(),
          trade_name: form.trade_name.trim() || null,
          document_type: form.document_type,
          document_number: docNumber,
          phone: form.phone.trim() || null,
          email: form.email.trim() || null,
          address: form.address.trim() || null,
          notes: form.notes.trim() || null,
          is_active: form.is_active,
        })
      } else {
        await createContact({
          id: crypto.randomUUID(),
          contact_type: form.contact_type,
          business_name: form.business_name.trim(),
          trade_name: form.trade_name.trim() || null,
          document_type: form.document_type,
          document_number: docNumber,
          phone: form.phone.trim() || null,
          email: form.email.trim() || null,
          address: form.address.trim() || null,
          notes: form.notes.trim() || null,
          is_active: form.is_active,
        })
      }
      navigate('/contactos')
    } catch (err) {
      setApiError(parseApiError(err))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!id) return
    setDeleting(true)
    try {
      await deleteContact(id)
      navigate('/contactos')
    } catch (err) {
      setApiError(parseApiError(err))
      setShowDelete(false)
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-text-muted">Cargando…</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-shrink-0 items-start justify-between gap-4">
        <div>
          <button
            type="button"
            onClick={() => navigate('/contactos')}
            className="mb-2 flex items-center gap-1 text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver a contactos
          </button>
          <h1 className="text-2xl font-semibold text-text-primary">
            {isEdit ? 'Editar contacto' : 'Nuevo contacto'}
          </h1>
        </div>
        {isEdit && (
          <button
            type="button"
            className="btn-danger flex flex-shrink-0 items-center gap-1.5"
            onClick={() => setShowDelete(true)}
          >
            <Trash2 className="h-4 w-4" />
            Eliminar
          </button>
        )}
      </div>

      {/* Form */}
      <form className="flex-1 overflow-y-auto" onSubmit={handleSubmit} noValidate>
        <div className="max-w-2xl space-y-6 pb-6">

          {apiError && (
            <div className="rounded border border-danger-500/30 bg-danger-500/10 px-4 py-3 text-sm text-danger-500">
              {apiError}
            </div>
          )}

          {/* Identificación */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Identificación</h2>

            <div>
              <label className="label" htmlFor="contact_type">Tipo de contacto</label>
              <select
                id="contact_type"
                className="input"
                value={form.contact_type}
                onChange={(e) => set('contact_type', e.target.value as ContactType)}
              >
                <option value="customer">Cliente</option>
                <option value="supplier">Proveedor</option>
                <option value="both">Cliente y proveedor</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label" htmlFor="document_type">Tipo de documento</label>
                <select
                  id="document_type"
                  className="input"
                  value={form.document_type}
                  onChange={(e) => {
                    const newType = e.target.value as DocumentType
                    set('document_type', newType)
                    if (newType === 'none') {
                      setErrors((prev) => ({ ...prev, document_number: undefined }))
                    }
                  }}
                >
                  <option value="none">Sin documento</option>
                  <option value="ruc">RUC</option>
                  <option value="ci">Cédula de identidad</option>
                  <option value="passport">Pasaporte</option>
                </select>
              </div>

              <div>
                <label className="label" htmlFor="document_number">Número de documento</label>
                <input
                  id="document_number"
                  className={`input ${errors.document_number ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                  type="text"
                  placeholder={form.document_type === 'ruc' ? 'ej. 80012345-1' : ''}
                  value={form.document_number}
                  onChange={(e) => set('document_number', e.target.value)}
                  disabled={form.document_type === 'none'}
                />
                {errors.document_number && (
                  <p className="mt-1 text-xs text-danger-500">{errors.document_number}</p>
                )}
              </div>
            </div>
          </div>

          {/* Datos básicos */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Datos del contacto</h2>

            <div>
              <label className="label" htmlFor="business_name">
                Razón social / Nombre completo{' '}
                <span className="text-danger-500">*</span>
              </label>
              <input
                id="business_name"
                className={`input ${errors.business_name ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                type="text"
                placeholder="ej. García Juan Carlos"
                value={form.business_name}
                onChange={(e) => set('business_name', e.target.value)}
              />
              {errors.business_name && (
                <p className="mt-1 text-xs text-danger-500">{errors.business_name}</p>
              )}
            </div>

            <div>
              <label className="label" htmlFor="trade_name">
                Nombre fantasía{' '}
                <span className="font-normal text-text-muted">(opcional)</span>
              </label>
              <input
                id="trade_name"
                className="input"
                type="text"
                placeholder="ej. García y Asociados"
                value={form.trade_name}
                onChange={(e) => set('trade_name', e.target.value)}
              />
            </div>
          </div>

          {/* Comunicación */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Comunicación</h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label" htmlFor="phone">Teléfono</label>
                <input
                  id="phone"
                  className="input"
                  type="tel"
                  placeholder="ej. 0991-123456"
                  value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                />
              </div>

              <div>
                <label className="label" htmlFor="email">Email</label>
                <input
                  id="email"
                  className={`input ${errors.email ? 'border-danger-500 focus:ring-danger-500' : ''}`}
                  type="email"
                  placeholder="ej. correo@ejemplo.com"
                  value={form.email}
                  onChange={(e) => set('email', e.target.value)}
                />
                {errors.email && (
                  <p className="mt-1 text-xs text-danger-500">{errors.email}</p>
                )}
              </div>
            </div>

            <div>
              <label className="label" htmlFor="address">Dirección</label>
              <textarea
                id="address"
                className="input resize-none"
                rows={2}
                placeholder="ej. Av. España 123, Asunción"
                value={form.address}
                onChange={(e) => set('address', e.target.value)}
              />
            </div>
          </div>

          {/* Notas y estado */}
          <div className="card space-y-4">
            <h2 className="text-base font-medium text-text-primary">Notas y estado</h2>

            <div>
              <label className="label" htmlFor="notes">Notas internas</label>
              <textarea
                id="notes"
                className="input resize-none"
                rows={3}
                placeholder="Condiciones de pago, observaciones, etc."
                value={form.notes}
                onChange={(e) => set('notes', e.target.value)}
              />
            </div>

            <div className="flex items-center gap-3">
              <Toggle checked={form.is_active} onChange={(v) => set('is_active', v)} />
              <span className="text-sm text-text-secondary">
                {form.is_active ? 'Contacto activo' : 'Contacto inactivo'}
              </span>
            </div>
          </div>

          {/* Acciones */}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/contactos')}
              disabled={saving}
            >
              Cancelar
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Crear contacto'}
            </button>
          </div>
        </div>
      </form>

      {showDelete && (
        <DeleteModal
          name={form.business_name}
          deleting={deleting}
          onConfirm={handleDelete}
          onClose={() => setShowDelete(false)}
        />
      )}
    </div>
  )
}
