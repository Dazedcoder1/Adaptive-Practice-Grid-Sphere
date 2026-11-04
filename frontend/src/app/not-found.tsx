import Link from "next/link";
import { Logo } from "@/components/layout/logo";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="bg-soft-gradient flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <Logo />
      <h1 className="mt-6 text-3xl font-semibold">Page not found</h1>
      <p className="text-muted-foreground">That page doesn&apos;t exist or has moved.</p>
      <Button asChild variant="gradient">
        <Link href="/">Back to home</Link>
      </Button>
    </main>
  );
}
