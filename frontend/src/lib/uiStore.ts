import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type SidebarState = 'expanded' | 'collapsed' | 'hidden'

interface UIStore {
  sidebarState: SidebarState
  cycleSidebar: () => void
}

const CYCLE: Record<SidebarState, SidebarState> = {
  expanded: 'collapsed',
  collapsed: 'hidden',
  hidden: 'expanded',
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      sidebarState: 'expanded',
      cycleSidebar: () => set({ sidebarState: CYCLE[get().sidebarState] }),
    }),
    { name: 'dtcore_sidebar_state' }
  )
)
