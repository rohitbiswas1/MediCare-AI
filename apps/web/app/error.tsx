"use client";
export default function ErrorPage({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <main className="main-content narrow">
      <h1>We couldn’t load this page</h1>
      <p className="muted" style={{ margin: "15px 0" }}>
        Try again. If the issue continues, return to your overview.
      </p>
      <button className="button button-primary" onClick={reset}>
        Try again
      </button>
    </main>
  );
}
