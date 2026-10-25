"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LogoutButton } from "@/components/layout/LogoutButton";

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
  const [menuOpen, setMenuOpen] = useState(false);
  return <header className="site-subheader"><div className="shell site-subheader-inner">
    <Link className="site-subbrand" href="/" aria-label="KEIBA AI トップページ"><span aria-hidden="true">♞</span><b>KEIBA <i>AI</i></b></Link>
    <nav aria-label="主要ナビゲーション">{navigation.map((item) => {
      const selected = pathname === item.href || (item.href === "/races" && pathname.startsWith("/races/"));
      return <Link key={item.href} href={item.href} aria-current={selected ? "page" : undefined} className={selected ? "selected" : undefined}>{item.label}</Link>;
    })}</nav>
    <div className="subheader-actions"><div className="desktop-logout"><LogoutButton /></div><button type="button" className="subheader-menu-toggle" aria-expanded={menuOpen} aria-controls="subheader-mobile-menu" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? "閉じる" : "メニュー"}</button></div>
    {menuOpen && <div id="subheader-mobile-menu" className="subheader-mobile-menu"><LogoutButton /></div>}
  </div></header>;
}

export function BackToHome() {
  return <Link className="back-home" href="/" aria-label="トップページに戻る">← トップに戻る</Link>;
}
