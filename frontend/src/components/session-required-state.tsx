"use client";

import Link from "next/link";
import { Lock, Settings } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";


export function SessionRequiredState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="mx-auto max-w-3xl p-4 pt-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <Lock className="h-4 w-4" />
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <Link
            href="/settings"
            className={cn(buttonVariants({ variant: "default", size: "lg" }), "inline-flex")}
          >
            <Settings className="h-4 w-4" />
            Abrir Configuracoes
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}