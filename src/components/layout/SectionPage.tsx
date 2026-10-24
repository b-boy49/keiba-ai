import { BackToHome, SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";

export function SectionPage({ title, description }: { title: string; description: string }) {
  return <div className="section-page"><SiteHeader/><main className="shell section-card"><BackToHome/><p>KEIBA AI</p><h1>{title}</h1><p>{description}</p><div className="empty-state"><b>準備中</b><span>このページはトップページ完成後のフェーズで実装します。実データはまだ接続していません。</span></div></main><SiteFooter/></div>;
}
