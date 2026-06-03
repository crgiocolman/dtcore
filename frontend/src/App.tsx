import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { RequireAuth } from './components/RequireAuth'
import { ToastContainer } from './components/Toast'
import { Categories } from './features/admin/pages/Categories'
import { Currencies } from './features/admin/pages/Currencies'
import { Settings } from './features/admin/pages/Settings'
import { InitialInventory } from './features/admin/pages/InitialInventory'
import { UnitCatalog } from './features/admin/pages/UnitCatalog'
import { Login } from './features/auth/pages/Login'
import { useAuthStore } from './features/auth/store'
import { ContactForm } from './features/contacts/pages/ContactForm'
import { ContactsList } from './features/contacts/pages/ContactsList'
import { ProductForm } from './features/products/pages/ProductForm'
import { ProductsList } from './features/products/pages/ProductsList'
import { AdjustmentForm } from './features/adjustments/pages/AdjustmentForm'
import { AdjustmentsList } from './features/adjustments/pages/AdjustmentsList'
import { Home } from './features/dashboard/pages/Home'
import { InventoryList } from './features/inventory/pages/InventoryList'
import { ProductKardex } from './features/inventory/pages/ProductKardex'
import { Reports } from './features/reports/pages/Reports'
import { PurchaseForm } from './features/purchases/pages/PurchaseForm'
import { PurchasesList } from './features/purchases/pages/PurchasesList'
import { POS } from './features/pos/pages/POS'
import { SalesList } from './features/sales/pages/SalesList'

export default function App() {
  const initFromStorage = useAuthStore((s) => s.initFromStorage)

  useEffect(() => {
    initFromStorage()
  }, [initFromStorage])

  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* POS: pantalla completa sin AppLayout */}
        <Route path="pos" element={<RequireAuth><POS /></RequireAuth>} />

        {/* Resto: con AppLayout + sidebar */}
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Home />} />
          <Route path="ventas" element={<SalesList />} />
          <Route path="compras" element={<PurchasesList />} />
          <Route path="compras/nueva" element={<PurchaseForm />} />
          <Route path="compras/:id" element={<PurchaseForm />} />
          <Route path="productos" element={<ProductsList />} />
          <Route path="productos/nuevo" element={<ProductForm />} />
          <Route path="productos/:id" element={<ProductForm />} />
          <Route path="contactos" element={<ContactsList />} />
          <Route path="contactos/nuevo" element={<ContactForm />} />
          <Route path="contactos/:id" element={<ContactForm />} />
          <Route path="ajustes" element={<AdjustmentsList />} />
          <Route path="ajustes/nuevo" element={<AdjustmentForm />} />
          <Route path="ajustes/:id" element={<AdjustmentForm />} />
          <Route path="inventario" element={<InventoryList />} />
          <Route path="inventario/:product_id" element={<ProductKardex />} />
          <Route path="reportes" element={<Reports />} />
          <Route path="admin/settings" element={<Settings />} />
          <Route path="admin/currencies" element={<Currencies />} />
          <Route path="admin/categorias" element={<Categories />} />
          <Route path="admin/units" element={<UnitCatalog />} />
          <Route path="admin/inventario-inicial" element={<InitialInventory />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
