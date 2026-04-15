import type { Metadata } from "next";
import "./globals.css";
import { GlobalErrorToaster } from "@/components/global-error-toaster";
import { ThemeProvider } from "@/components/theme-provider";
import { Header } from "@/components/header";

export const metadata: Metadata = {
  title: "Crypto Analytics - Deteccao de Oportunidades",
  description: "Sistema de monitoramento e deteccao de oportunidades em criptomoedas",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col">
        <ThemeProvider>
          <Header />
          <main className="flex-1">{children}</main>
          <GlobalErrorToaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
