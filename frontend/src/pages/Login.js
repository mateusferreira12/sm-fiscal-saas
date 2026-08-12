import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api, { formatApiErrorDetail } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileText } from "@phosphor-icons/react";
import { toast } from "sonner";

const BG = "https://images.unsplash.com/photo-1497366754035-f200968a6e72?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODF8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBvZmZpY2UlMjBhY2NvdW50YW50fGVufDB8fHx8MTc4Mjk1ODEyMnww&ixlib=rb-4.1.0&q=85";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      login(data.access_token, data.user);
      toast.success("Bem-vindo de volta!");
      navigate("/");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:block relative">
        <img src={BG} alt="Escritório" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-slate-900/70" />
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <FileText size={40} weight="duotone" className="text-blue-400 mb-4" />
          <h2 className="text-3xl font-bold tracking-tight">Emissão de NF-e simplificada</h2>
          <p className="text-slate-300 mt-3 max-w-md">
            Cadastre clientes e produtos, calcule impostos automaticamente e emita suas notas fiscais eletrônicas com DANFE e XML.
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6" data-testid="login-form">
          <div className="lg:hidden flex items-center gap-2 mb-4">
            <FileText size={28} weight="duotone" className="text-blue-600" />
            <span className="font-bold text-lg">NF-e System</span>
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Entrar</h1>
            <p className="text-sm text-slate-500 mt-1">Acesse seu painel fiscal</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">E-mail</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              required data-testid="login-email-input" placeholder="voce@empresa.com.br" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Senha</Label>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              required data-testid="login-password-input" placeholder="••••••••" />
          </div>
          <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit-button">
            {loading ? "Entrando..." : "Entrar"}
          </Button>
          <p className="text-sm text-center text-slate-500">
            Não tem conta?{" "}
            <Link to="/register" className="text-blue-600 font-medium hover:underline" data-testid="go-register-link">
              Cadastre-se
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
