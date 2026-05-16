import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "maymayinvest v1",
  description: "AI-native investment management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex">
          <aside className="w-56 border-r border-[var(--border)] p-4 space-y-1 bg-[var(--surface)]">
            <div className="text-sm font-semibold tracking-wide mb-4">maymayinvest</div>
            <nav className="space-y-1 text-sm">
              {[
                { href: "/", label: "Dashboard" },
                { href: "/orders", label: "Orders" },
                { href: "/operator", label: "Operator Console" },
              ].map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="block px-3 py-2 rounded hover:bg-[var(--bg)] text-[var(--text-dim)] hover:text-[var(--text)]"
                >
                  {l.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="flex-1 p-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
