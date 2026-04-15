"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  acceptInvite,
  getInvitePreview,
  setStoredAuthToken,
  setStoredRefreshToken,
  setStoredWorkspaceId,
} from "@/lib/api";
import type { InvitePreview } from "@/lib/types";
import { Check, Loader2, Mail, ShieldCheck } from "lucide-react";


export default function InviteAcceptancePage() {
  const params = useParams<{ code: string }>();
  const router = useRouter();
  const inviteCode = Array.isArray(params?.code) ? params.code[0] : params?.code || "";

  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!inviteCode) {
      setLoading(false);
      setError("Convite inválido.");
      return;
    }

    void getInvitePreview(inviteCode)
      .then((payload) => {
        setPreview(payload);
        setEmail(payload.email);
      })
      .catch((fetchError) => {
        setError(fetchError instanceof Error ? fetchError.message : "Falha ao carregar convite");
      })
      .finally(() => setLoading(false));
  }, [inviteCode]);

  async function handleSubmit() {
    if (!preview) return;
    if (!email.trim()) {
      setError("Informe o email do convite.");
      return;
    }
    if (password.length < 12) {
      setError("A senha precisa ter pelo menos 12 caracteres.");
      return;
    }
    if (password !== confirmPassword) {
      setError("A confirmação de senha não confere.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const response = await acceptInvite({ code: preview.code, email, password });
      setStoredAuthToken(response.access_token);
      setStoredRefreshToken(response.refresh_token);
      setStoredWorkspaceId(response.session.workspaces[0]?.id || "");
      router.push(response.session.must_change_password ? "/settings" : "/");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Falha ao aceitar convite");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-3xl items-center p-4">
      <Card className="w-full border-emerald-500/20 bg-gradient-to-br from-background via-background to-emerald-500/[0.04]">
        <CardHeader className="space-y-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-xl font-semibold">Aceitar convite</CardTitle>
            <CardDescription>
              Entre na organização e finalize a criação da conta para acessar o workspace liberado para você.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Carregando convite...
            </div>
          ) : preview ? (
            <>
              <div className="grid gap-3 rounded-2xl border bg-muted/30 p-4 sm:grid-cols-3">
                <Meta label="Organização" value={preview.organization_name} />
                <Meta label="Workspace" value={preview.workspace_name} />
                <Meta label="Perfil" value={preview.role} />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <label className="text-sm font-medium">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className="pl-9"
                      placeholder="voce@empresa.com"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Senha</label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="Mínimo de 12 caracteres"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Confirmar senha</label>
                  <Input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Repita a senha"
                  />
                </div>
              </div>

              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-muted-foreground">
                O email precisa coincidir com o convite. Depois do cadastro, a sessão já será iniciada automaticamente.
              </div>

              <Button onClick={handleSubmit} disabled={submitting || preview.status !== "pending"} className="gap-2">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {preview.status === "pending" ? "Criar conta e entrar" : "Convite indisponível"}
              </Button>
            </>
          ) : null}

          {preview && preview.status !== "pending" ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-300">
              Este convite está {preview.status === "used" ? "usado" : "expirado"}. Solicite um novo link ao administrador.
            </div>
          ) : null}

          {error ? (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-600 dark:text-red-300">
              {error}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}