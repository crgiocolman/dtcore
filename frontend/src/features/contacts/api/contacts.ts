import { apiFetch } from '../../../lib/api'

export type ContactType = 'customer' | 'supplier' | 'both'
export type DocumentType = 'ruc' | 'ci' | 'passport' | 'none'

export interface ContactOut {
  id: string
  contact_type: ContactType
  document_type: DocumentType
  document_number: string | null
  business_name: string
  trade_name: string | null
  phone: string | null
  email: string | null
  address: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
  created_by_user_id: string | null
  updated_by_user_id: string | null
}

export interface ContactListOut {
  items: ContactOut[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ContactCreate {
  id: string
  contact_type: ContactType
  document_type?: DocumentType
  document_number?: string | null
  business_name: string
  trade_name?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface ContactUpdate {
  contact_type?: ContactType
  document_type?: DocumentType
  document_number?: string | null
  business_name?: string
  trade_name?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface ContactListParams {
  contact_type?: ContactType
  search?: string
  page?: number
  page_size?: number
}

export function fetchContacts(params: ContactListParams = {}): Promise<ContactListOut> {
  const qs = new URLSearchParams()
  if (params.contact_type) qs.set('contact_type', params.contact_type)
  if (params.search) qs.set('search', params.search)
  if (params.page != null) qs.set('page', String(params.page))
  if (params.page_size != null) qs.set('page_size', String(params.page_size))
  const query = qs.toString()
  return apiFetch<ContactListOut>(`/contacts${query ? `?${query}` : ''}`)
}

export function fetchContact(id: string): Promise<ContactOut> {
  return apiFetch<ContactOut>(`/contacts/${id}`)
}

export function createContact(data: ContactCreate): Promise<ContactOut> {
  return apiFetch<ContactOut>('/contacts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateContact(id: string, data: ContactUpdate): Promise<ContactOut> {
  return apiFetch<ContactOut>(`/contacts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteContact(id: string): Promise<void> {
  return apiFetch<void>(`/contacts/${id}`, { method: 'DELETE' })
}
