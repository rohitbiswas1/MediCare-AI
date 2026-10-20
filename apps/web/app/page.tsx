"use client";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight,
  FileHeart,
  ScanText,
  MapPin,
  ShieldCheck,
  LockKeyhole,
  Check,
  HeartPulse,
} from "lucide-react";
import { Brand, LanguageSelect, ThemeToggle } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useLocale } from "@/lib/i18n";
export default function Home() {
  const { t, locale } = useLocale();
  const reduce = useReducedMotion();
  return (
    <div className="landing">
      <nav className="landing-nav">
        <Brand />
        <div className="landing-links">
          <a href="#how">How it works</a>
          <a href="#features">Our tools</a>
          <Link href="/policy">Your privacy</Link>
        </div>
        <div className="row">
          <LanguageSelect />
          <ThemeToggle />
          <Button asChild variant="outline" size="sm">
            <Link href="/login">{t("login")}</Link>
          </Button>
        </div>
      </nav>
      <main>
        <section className="hero">
          <motion.div
            initial={reduce ? false : { opacity: 1, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="badge teal">
              <span
                style={{
                  height: 6,
                  width: 6,
                  borderRadius: "50%",
                  background: "#0d9488",
                }}
              />{" "}
              A LITTLE CLARITY GOES A LONG WAY
            </span>
            <h1>
              {locale === "en" ? (
                <>
                  Understand
                  <br />
                  your health.
                  <br />
                  <span>Find your care.</span>
                </>
              ) : (
                t("footer")
              )}
            </h1>
            <p>
              {t("reportToolSub")} {t("rxToolSub")} {t("pharmacyToolSub")}
            </p>
            <div className="hero-actions">
              <Button asChild>
                <Link href="/register">
                  {t("start")}
                  <ArrowRight />
                </Link>
              </Button>
              <Button asChild variant="outline">
                <a href="#how">{t("learn")}</a>
              </Button>
            </div>
            <div className="hero-trust">
              <span>
                <LockKeyhole /> Private by design
              </span>
              <span>
                <ShieldCheck /> You stay in control
              </span>
            </div>
          </motion.div>
          <motion.div
            className="hero-art"
            initial={reduce ? false : { opacity: 1, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.15 }}
          >
            <div className="sample-report">
              <div className="between">
                <div className="row">
                  <div className="icon-box">
                    <FileHeart />
                  </div>
                  <div>
                    <h3>A clearer look at your report</h3>
                    <small className="muted">
                      Illustrative example · not patient data
                    </small>
                  </div>
                </div>
                <span className="badge teal">
                  <Check size={11} /> Extracted
                </span>
              </div>
              <div className="sample-wave" aria-hidden="true">
                <svg viewBox="0 0 400 90" fill="none">
                  <path
                    d="M0 48H72L82 35L95 59L109 46H143L153 19L164 77L177 4L191 63L207 45H244L257 35L268 53L279 46H400"
                    stroke="#2563eb"
                    strokeWidth="2.5"
                  />
                  <path
                    d="M0 82H400M0 12H400"
                    stroke="#dce8f7"
                    strokeDasharray="4 5"
                  />
                </svg>
              </div>
              <span className="eyebrow">FROM COMPLEX TO CLEAR</span>
              <p>
                See the measurements written in your report, where they came
                from, and what to discuss with your clinician.
              </p>
              <div className="notice">
                <ShieldCheck size={15} />
                <span>{t("disclaimer")}</span>
              </div>
            </div>
            <div className="floating-note">
              <div className="icon-box teal" style={{ height: 32, width: 32 }}>
                <LockKeyhole size={16} />
              </div>
              <div>
                <strong>Your records belong to you</strong>
                <p style={{ fontSize: 10, margin: 0 }}>
                  Private storage. Clear consent.
                </p>
              </div>
            </div>
          </motion.div>
        </section>
        <div className="landing-band">
          MADE FOR EVERYDAY UNDERSTANDING &nbsp; · &nbsp; ENGLISH &nbsp; हिन्दी
          &nbsp; বাংলা &nbsp; · &nbsp; BUILT WITH YOUR PRIVACY IN MIND
        </div>
        <section id="features" className="landing-section">
          <div className="section-heading">
            <div className="eyebrow" style={{ marginBottom: 14 }}>
              YOUR NEXT STEP, MADE SIMPLER
            </div>
            <h2>
              Less confusion.
              <br />
              More informed conversations.
            </h2>
            <p>{t("overviewSub")}</p>
          </div>
          <div className="three-grid">
            {[
              {
                key: "reportTool" as const,
                sub: "reportToolSub" as const,
                Icon: FileHeart,
                color: "",
              },
              {
                key: "rxTool" as const,
                sub: "rxToolSub" as const,
                Icon: ScanText,
                color: "purple",
              },
              {
                key: "pharmacyTool" as const,
                sub: "pharmacyToolSub" as const,
                Icon: MapPin,
                color: "teal",
              },
            ].map(({ key, sub, Icon, color }) => (
              <Link href="/register" key={key}>
                <Card className="tool-card">
                  <div className={`icon-box ${color}`}>
                    <Icon />
                  </div>
                  <ArrowRight className="arrow" />
                  <h3>{t(key)}</h3>
                  <p>{t(sub)}</p>
                </Card>
              </Link>
            ))}
          </div>
        </section>
        <section
          id="how"
          style={{
            background: "var(--bg)",
            borderBlock: "1px solid var(--border)",
          }}
        >
          <div className="landing-section">
            <div className="section-heading">
              <span className="eyebrow">A THOUGHTFUL PROCESS</span>
              <h2 style={{ marginTop: 15 }}>
                From a document to a better question.
              </h2>
            </div>
            <div className="three-grid">
              {[
                {
                  n: "01",
                  title: t("upload"),
                  body: "Choose a document and give permission for private processing.",
                },
                {
                  n: "02",
                  title: t("source"),
                  body: "Review extracted text and supported measurements against the original.",
                },
                {
                  n: "03",
                  title: t("care"),
                  body: "Take your questions to a qualified clinician or pharmacist.",
                },
              ].map((item) => (
                <div className="card" key={item.n}>
                  <div className="eyebrow">{item.n}</div>
                  <h3 style={{ margin: "15px 0 10px" }}>{item.title}</h3>
                  <p className="muted" style={{ fontSize: 13 }}>
                    {item.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
        <section className="landing-section">
          <div className="notice warning">
            <HeartPulse />
            <span>{t("emergency")}</span>
          </div>
          <p
            className="muted"
            style={{ fontSize: 11, marginTop: 18, textAlign: "center" }}
          >
            {t("disclaimer")} Specialized diagnostic models are unavailable
            pending clinical validation.
          </p>
        </section>
      </main>
      <footer className="landing-bottom">
        <Brand />
        <span>{t("footer")}</span>
        <Link href="/policy">Privacy & information use</Link>
      </footer>
    </div>
  );
}
