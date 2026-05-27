import { apiFetch } from '../../../lib/api'

export interface CategoryTreeNode {
  id: string
  name: string
  parent_id: string | null
  is_active: boolean
  children: CategoryTreeNode[]
}

export function fetchCategoryTree(): Promise<CategoryTreeNode[]> {
  return apiFetch<CategoryTreeNode[]>('/categories')
}

export function buildCategoryMap(nodes: CategoryTreeNode[]): Map<string, string> {
  const map = new Map<string, string>()
  function walk(items: CategoryTreeNode[]) {
    for (const n of items) {
      map.set(n.id, n.name)
      walk(n.children)
    }
  }
  walk(nodes)
  return map
}

export function flattenTree(
  nodes: CategoryTreeNode[],
  depth = 0,
): Array<{ id: string; label: string }> {
  const result: Array<{ id: string; label: string }> = []
  for (const node of nodes) {
    const indent = ' '.repeat(depth * 3)
    result.push({ id: node.id, label: indent + node.name })
    result.push(...flattenTree(node.children, depth + 1))
  }
  return result
}
