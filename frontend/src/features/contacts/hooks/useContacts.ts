import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchContacts } from '../api/contacts'
import type { ContactListOut, ContactListParams, ContactType } from '../api/contacts'

const PAGE_SIZE = 20

interface UseContactsState {
  data: ContactListOut | null
  loading: boolean
  error: string | null
}

interface UseContactsResult extends UseContactsState {
  page: number
  search: string
  contactType: ContactType | ''
  setPage: (p: number) => void
  setSearch: (s: string) => void
  setContactType: (t: ContactType | '') => void
  reload: () => void
}

export function useContacts(): UseContactsResult {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [contactType, setContactType] = useState<ContactType | ''>('')
  const [state, setState] = useState<UseContactsState>({ data: null, loading: true, error: null })

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRef = useRef(search)
  searchRef.current = search

  const load = useCallback(
    (params: ContactListParams) => {
      setState((s) => ({ ...s, loading: true, error: null }))
      fetchContacts(params)
        .then((data) => setState({ data, loading: false, error: null }))
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : 'Error al cargar contactos'
          setState((s) => ({ ...s, loading: false, error: msg }))
        })
    },
    [],
  )

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      load({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        contact_type: (contactType as ContactType) || undefined,
      })
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [page, search, contactType, load])

  const handleSetSearch = useCallback((s: string) => {
    setSearch(s)
    setPage(1)
  }, [])

  const handleSetContactType = useCallback((t: ContactType | '') => {
    setContactType(t)
    setPage(1)
  }, [])

  const reload = useCallback(() => {
    load({
      page,
      page_size: PAGE_SIZE,
      search: search || undefined,
      contact_type: (contactType as ContactType) || undefined,
    })
  }, [page, search, contactType, load])

  return {
    ...state,
    page,
    search,
    contactType,
    setPage,
    setSearch: handleSetSearch,
    setContactType: handleSetContactType,
    reload,
  }
}
