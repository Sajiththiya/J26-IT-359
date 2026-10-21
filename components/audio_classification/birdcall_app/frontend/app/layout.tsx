import type { Metadata } from "next";
import Link from "next/link";
import { Bird, ArrowUpRight } from "lucide-react";
import { SessionProvider } from "@/components/session";
import "./globals.css";
export const metadata: Metadata = {
  title: "Birdcall | Listen to the wild",
  description:
    "Component 02: Noise-Robust Bioacoustic Bird Call Recognition for Sri Lankan Endemic Birds",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <header className="nav">
            <Link className="brand" href="/">
              <span className="brand-icon">
                <Bird size={25} />
              </span>
              birdcall<span className="brand-dot">.</span>
            </Link>
            <nav aria-label="Main navigation">
              <Link href="/#model">Model results</Link>
              <Link href="/#species">
                The species <ArrowUpRight size={14} />
              </Link>
              <span className="research-tag">COMPONENT 02</span>
            </nav>
          </header>
          {children}
          <footer>
            <span>
              <Bird size={18} /> Listening closer. Understanding nature.
            </span>
            <span>Final-year research · Sri Lanka · Component 02</span>
          </footer>
        </SessionProvider>
      </body>
    </html>
  );
}
