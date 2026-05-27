import { apiFetch } from '../../../lib/api'
export type { CategoryTreeNode } from '../../products/api/categories'
export { fetchCategoryTree } from '../../products/api/categories'

export interface CategoryOut {
  id: string
  name: string
  parent_id: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export function createCategory(data: {
  id: string
  name: string
  parent_id: string | null
  is_active: boolean
}): Promise<CategoryOut> {
  return apiFetch<CategoryOut>('/categories', { method: 'POST', body: JSON.stringify(data) })
}

export function updateCategory(
  id: string,
  data: { name?: string; is_active?: boolean },
): Promise<CategoryOut> {
  return apiFetch<CategoryOut>(`/categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteCategory(id: string): Promise<void> {
  return apiFetch<void>(`/categories/${id}`, { method: 'DELETE' })
}
