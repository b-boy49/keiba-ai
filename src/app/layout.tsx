import type { Metadata, Viewport } from "next";
import "./globals.css";

// The site is password-gated; do not prerender authenticated HTML into a shared cache.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "KEIBA AI | AIで読む、競馬の未来",
  description: "競馬AI予想・分析サービス",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ja"><body>{children}</body></html>;
}
