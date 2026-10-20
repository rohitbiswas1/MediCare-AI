import Link from "next/link";
export default function NotFound() {
  return (
    <main className="main-content narrow">
      <h1>Page not found</h1>
      <p className="muted" style={{ margin: "15px 0" }}>
        This page may have moved, or the link is incomplete.
      </p>
      <Link href="/dashboard" className="button button-primary">
        Go to your overview
      </Link>
    </main>
  );
}
