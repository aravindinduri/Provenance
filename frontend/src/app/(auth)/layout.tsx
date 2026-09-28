/**
 * Auth group layout — wraps sign-in and sign-up pages.
 * Centered, minimal chrome. No nav bar.
 */
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background">
      <div className="mb-8 flex flex-col items-center gap-2">
        <span className="text-2xl font-semibold tracking-tight">Provenance</span>
        <p className="text-sm text-muted-foreground">Supply-chain risk intelligence</p>
      </div>
      {children}
    </div>
  );
}
