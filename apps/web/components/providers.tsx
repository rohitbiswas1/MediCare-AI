"use client";
import { ThemeProvider } from "next-themes";
import { LocaleProvider } from "@/lib/i18n";
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <LocaleProvider>{children}</LocaleProvider>
    </ThemeProvider>
  );
}
