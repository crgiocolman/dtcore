import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { Placeholder } from './components/Placeholder'
import { RequireAuth } from './components/RequireAuth'
import { Categories } from './features/admin/pages/Categories'
import { Currencies } from './features/admin/pages/Currencies'
import { Settings } from './features/admin/pages/Settings'
import { UnitCatalog } from './features/admin/pages/UnitCatalog'
import { Login } from './features/auth/pages/Login'
import { useAuthStore } from './features/auth/store'
import { ContactForm } from './features/contacts/pages/ContactForm'
import { ContactsList } from './features/contacts/pages/ContactsList'
import { ProductForm } from './features/products/pages/ProductForm'
import { ProductsList } from './features/products/pages/ProductsList'

export default function App() {
  const initFromStorage = useAuthStore((s) => s.initFromStorage)

  useEffect(() => {
    initFromStorage()
  }, [initFromStorage])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Placeholder title="Inicio" />} />
          <Route path="pos" element={<Placeholder title="POS" />} />
          <Route path="ventas" element={<Placeholder title="Ventas" />} />
          <Route path="compras" element={<Placeholder title="Compras" />} />
          <Route path="productos" element={<ProductsList />} />
          <Route path="productos/nuevo" element={<ProductForm />} />
          <Route path="productos/:id" element={<ProductForm />} />
          <Route path="contactos" element={<ContactsList />} />
          <Route path="contactos/nuevo" element={<ContactForm />} />
          <Route path="contactos/:id" element={<ContactForm />} />
          <Route path="inventario" element={<Placeholder title="Inventario" />} />
          <Route path="reportes" element={<Placeholder title="Reportes" />} />
          <Route path="admin/settings" element={<Settings />} />
          <Route path="admin/currencies" element={<Currencies />} />
          <Route path="admin/categorias" element={<Categories />} />
          <Route path="admin/units" element={<UnitCatalog />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
