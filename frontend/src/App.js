import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import Clients from "@/pages/Clients";
import Products from "@/pages/Products";
import Invoices from "@/pages/Invoices";
import InvoiceNew from "@/pages/InvoiceNew";
import InvoiceDetail from "@/pages/InvoiceDetail";
import Settings from "@/pages/Settings";
import Reports from "@/pages/Reports";
import Manifesto from "@/pages/Manifesto";

function Protected({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen flex items-center justify-center text-slate-400">Carregando...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return null;
  if (user) return <Navigate to="/" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
            <Route path="/register" element={<PublicOnly><Register /></PublicOnly>} />
            <Route path="/" element={<Protected><Dashboard /></Protected>} />
            <Route path="/clientes" element={<Protected><Clients /></Protected>} />
            <Route path="/produtos" element={<Protected><Products /></Protected>} />
            <Route path="/notas" element={<Protected><Invoices /></Protected>} />
            <Route path="/notas/nova" element={<Protected><InvoiceNew /></Protected>} />
            <Route path="/notas/:id" element={<Protected><InvoiceDetail /></Protected>} />
            <Route path="/configuracoes" element={<Protected><Settings /></Protected>} />
            <Route path="/relatorios" element={<Protected><Reports /></Protected>} />
            <Route path="/manifestacao" element={<Protected><Manifesto /></Protected>} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </div>
  );
}

export default App;
