"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, ShieldCheck, FileHeart, LoaderCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import { Brand, LanguageSelect, ErrorNotice } from "./common";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
const schema = z.object({
  email: z.email(),
  password: z.string().min(12).max(128),
  name: z.string().max(100).optional(),
  consent: z.boolean().optional(),
});
type Values = z.infer<typeof schema>;
export function AuthForm({ register = false }: { register?: boolean }) {
  const router = useRouter();
  const { t } = useLocale();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const form = useForm<Values>({ resolver: zodResolver(schema) });
  async function submit(values: Values) {
    setError("");
    try {
      const result = await api<{
        requires_email_verification?: boolean;
        message?: string;
      }>(register ? "/auth/register" : "/auth/login", {
        method: "POST",
        body: JSON.stringify(values),
      });
      if (result.requires_email_verification) {
        setMessage(result.message || "Check your email.");
        return;
      }
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <div className="auth-page">
      <aside className="auth-story">
        <Brand />
        <div>
          <span className="eyebrow">CARE BEGINS WITH CLARITY</span>
          <h1 style={{ marginTop: 20 }}>{t("footer")}</h1>
          <p>{t("emptyBody")}</p>
          <div
            className="sample-report"
            style={{ marginTop: 40, maxWidth: 350, transform: "rotate(-3deg)" }}
          >
            <div className="row">
              <div className="icon-box">
                <FileHeart />
              </div>
              <h3>{t("reportTool")}</h3>
            </div>
            <p>{t("disclaimer")}</p>
            <div className="badge teal">
              <ShieldCheck size={12} />
              {t("privacyTitle")}
            </div>
          </div>
        </div>
        <small className="muted">
          Private by design. Made for understanding.
        </small>
      </aside>
      <main className="auth-form-wrap">
        <div className="auth-lang">
          <LanguageSelect />
        </div>
        <div className="auth-form">
          <h1>{t(register ? "register" : "signin")}</h1>
          <p className="intro">{t(register ? "registerSub" : "signinSub")}</p>
          <form
            method="post"
            className="stack"
            onSubmit={form.handleSubmit(submit)}
          >
            <ErrorNotice message={error} />
            {message && (
              <div role="status" className="notice">
                {message}
              </div>
            )}
            {register && (
              <div className="field">
                <label htmlFor="name">{t("name")}</label>
                <Input
                  id="name"
                  autoComplete="name"
                  required
                  {...form.register("name")}
                />
              </div>
            )}
            <div className="field">
              <label htmlFor="email">{t("email")}</label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                {...form.register("email")}
              />
              {form.formState.errors.email && (
                <small role="alert">Enter a valid email address.</small>
              )}
            </div>
            <div className="field">
              <label htmlFor="password">{t("password")}</label>
              <Input
                id="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={12}
                maxLength={128}
                required
                {...form.register("password")}
              />
              <small>{t("passwordHint")}</small>
            </div>
            {register && (
              <label className="checkbox">
                <input type="checkbox" required {...form.register("consent")} />
                <span>
                  {t("terms")}{" "}
                  <Link className="source-link" href="/policy">
                    Privacy policy
                  </Link>
                </span>
              </label>
            )}
            <Button
              type="submit"
              disabled={!form.formState.isReady || form.formState.isSubmitting}
            >
              {form.formState.isSubmitting ? (
                <LoaderCircle className="spinner" />
              ) : (
                <>
                  {t(register ? "create" : "login")}
                  <ArrowRight />
                </>
              )}
            </Button>
          </form>
          <div className="auth-alt">
            {t(register ? "haveAccount" : "newAccount")}{" "}
            <Link href={register ? "/login" : "/register"}>
              {t(register ? "login" : "create")}
            </Link>
          </div>
          <div className="notice" style={{ marginTop: 35 }}>
            <ShieldCheck />
            <span>{t("disclaimer")}</span>
          </div>
        </div>
      </main>
    </div>
  );
}
