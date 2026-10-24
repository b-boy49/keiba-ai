import { BackToHome, SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";

export function PublicPredictionPage() {
  return (
    <div className="public-analysis-page public-prediction-page">
      <SiteHeader />
      <main className="shell public-analysis-content">
        <BackToHome />
        <header className="public-analysis-hero">
          <p>KEIBA AI · RACE STATUS</p>
          <h1>個別レースのAI予想</h1>
          <span>公開用の予想は、確定出馬表・推論結果・掲載可否を確認した後にだけ掲載します。</span>
        </header>

        <section className="prediction-readiness" aria-labelledby="kanagawa-title">
          <div className="readiness-orb" aria-hidden="true">…</div>
          <div>
            <p>UPCOMING RACE</p>
            <h2 id="kanagawa-title">11月7日 神奈川新聞杯</h2>
            <span>予測準備中</span>
          </div>
          <dl>
            <div><dt>確定出馬表</dt><dd>未取得</dd></div>
            <div><dt>公開用予測</dt><dd>未取得</dd></div>
            <div><dt>公開可否</dt><dd>確認中</dd></div>
          </dl>
        </section>

        <section className="analysis-boundary prediction-boundary" aria-labelledby="prediction-boundary-title">
          <div>
            <p>PUBLICATION CONTROL</p>
            <h2 id="prediction-boundary-title">未確認の予想や研究データは表示しません</h2>
          </div>
          <ul>
            <li>確定出馬表と推論結果が未取得のため、順位・スコア・馬名は掲載していません。</li>
            <li>個別予測CSV、モデルファイル、研究環境のデータは公開サイトから取得できません。</li>
            <li>掲載可能なデータだけを、権利と内容を確認してから公開します。</li>
          </ul>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
