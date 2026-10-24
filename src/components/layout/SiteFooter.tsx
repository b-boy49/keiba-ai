import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell footer-inner">
        <div><b>KEIBA <i>AI</i></b><p>AIで読む、競馬の未来</p></div>
        <div className="footer-links"><Link href="/about">サイト情報・免責事項</Link><Link href="/about#data">データについて</Link></div>
        <p className="disclaimer">現在は初期デモです。出走馬・予想・勝率などの実データは未連携であり、投票や結果を保証するものではありません。</p>
        <small>© 2026 KEIBA AI</small>
      </div>
    </footer>
  );
}
