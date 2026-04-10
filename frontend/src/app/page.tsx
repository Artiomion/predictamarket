export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="font-heading text-4xl font-semibold tracking-tight">
          PredictaMarket
        </h1>
        <p className="mt-3 font-body text-text-secondary">
          AI-powered stock predictions for S&amp;P 500
        </p>
        <p className="mt-6 font-mono text-sm text-success">
          $260.49 <span className="text-danger">-0.38%</span>
        </p>
      </div>
    </main>
  );
}
