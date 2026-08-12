import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api, { formatApiErrorDetail } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileText } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", { name, email, password });
      login(data.access_token, data.user);
      toast.success("Conta criada com sucesso!");
      navigate("/");
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-slate-50">
      <form onSubmit={submit} className="w-full max-w-sm space-y-6 bg-white p-8 rounded-lg border border-slate-200" data-testid="register-form">
        <div className="flex items-center gap-2">
          <FileText size={28} weight="duotone" className="text-blue-600" />
          <span className="font-bold text-lg">NF-e System</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Criar conta</h1>
          <p className="text-sm text-slate-500 mt-1">Comece a emitir suas notas</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="name">Nome</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required data-testid="register-name-input" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">E-mail</Label>
          <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="register-email-input" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Senha</Label>
          <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} data-testid="register-password-input" />
        </div>
        <Button type="submit" className="w-full" disabled={loading} data-testid="register-submit-button">
          {loading ? "Criando..." : "Criar conta"}
        </Button>
        <p className="text-sm text-center text-slate-500">
          Já tem conta?{" "}
          <Link to="/login" className="text-blue-600 font-medium hover:underline" data-testid="go-login-link">Entrar</Link>
        </p>
      </form>
    </div>
  );
}
