"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/races", label: "レース一覧" },
  { href: "/predictions", label: "AI予想" },
  { href: "/analysis", label: "AI分析" },
  { href: "/performance", label: "予想成績" },
  { href: "/results", label: "結果" },
  { href: "/about", label: "サイト紹介" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return <header className="site-subheader"><div className="shell site-subheader-inner">
    <Link className="site-subbrand" href="/" aria-label="KEIBA AI トップページ"><span aria-hidden="true">♞</span><b>KEIBA <i>AI</i></b></Link>
    <nav aria-label="主要ナビゲーション">{navigation.map((item) => {
      const selected = pathname === item.href || (item.href === "/races" && pathname.startsWith("/races/"));
      return <Link key={item.href} href={item.href} aria-current={selected ? "page" : undefined} className={selected ? "selected" : undefined}>{item.label}</Link>;
    })}</nav>
  </div></header>;
}

export function BackToHome() {
  return <Link className="back-home" href="/" aria-label="トップページに戻る">← トップに戻る</Link>;
}
