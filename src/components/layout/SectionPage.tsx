import Link from "next/link";

export function SectionPage({ title, description }: { title: string; description: string }) {
  return <main className="section-page"><div className="shell section-card"><p>KEIBA AI</p><h1>{title}</h1><p>{description}</p><div className="empty-state"><b>準備中</b><span>このページはトップページ完成後のフェーズで実装します。実データはまだ接続していません。</span></div><Link href="/">← トップページへ戻る</Link></div></main>;
}
