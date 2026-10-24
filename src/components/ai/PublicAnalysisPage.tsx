import { BackToHome, SiteHeader } from "@/components/layout/SiteHeader";
import { SiteFooter } from "@/components/layout/SiteFooter";

const features = [
  ["過去成績", "直近の着順傾向や出走間隔など、予測時点より前の履歴を整理します。"],
  ["距離・コース", "距離経験や開催コースでの過去の傾向を、比較用の特徴量として扱います。"],
  ["騎手との組合せ", "騎手の過去成績や馬との組合せ履歴を、利用可能な範囲で集計します。"],
  ["出走条件", "馬番・枠番・斤量・頭数など、確定した出走条件を入力として扱います。"],
] as const;

export function PublicAnalysisPage() {
  return <div className="public-analysis-page">
    <SiteHeader />
    <main className="shell public-analysis-content">
      <BackToHome />
      <header className="public-analysis-hero">
        <p>KEIBA AI · PUBLIC ANALYSIS GUIDE</p>
        <h1>AI分析の仕組み</h1>
        <span>研究用データや個別予測を公開せず、予測工程と安全な表示範囲を説明します。</span>
      </header>

      <section className="analysis-safety" aria-label="公開状態">
        <div><small>RESEARCH EVALUATION</small><b>確認中</b><span>未承認の研究評価数値は表示しません。</span></div>
        <div><small>NOVEMBER 7 RACE</small><b>予測準備中</b><span>確定出馬表・承認済み予測は未取得です。</span></div>
        <div><small>PUBLIC DATA POLICY</small><b>個別データ非公開</b><span>馬名、予測順位、スコア、CSV、モデルは掲載しません。</span></div>
      </section>

      <section className="analysis-flow" aria-labelledby="flow-title">
        <div className="analysis-heading"><p>MODEL FLOW</p><h2 id="flow-title">レース前情報から順位を作るまで</h2><span>実際の着順やレース後に判明する情報は、予測時点の特徴量には使いません。</span></div>
        <ol>
          <li><i>01</i><b>入力を確認</b><span>確定した出走条件と、利用許諾を確認済みのレース前情報だけを対象にします。</span></li>
          <li><i>02</i><b>特徴量を作成</b><span>馬・騎手・距離・コース・出走条件の履歴を、同じ形式の比較用データへ整えます。</span></li>
          <li><i>03</i><b>LightGBMで算出</b><span>各出走馬について比較用の参照スコアを計算します。スコアは勝率や収益の保証ではありません。</span></li>
          <li><i>04</i><b>スコア順に表示</b><span>承認済みの出走表・モデル・公開権限がすべて揃った場合だけ、順位として表示します。</span></li>
        </ol>
      </section>

      <section className="analysis-feature-section" aria-labelledby="feature-title">
        <div className="analysis-heading"><p>FEATURE CATEGORIES</p><h2 id="feature-title">比較に使う情報の種類</h2></div>
        <div className="analysis-feature-grid">{features.map(([title, text], index) => <article key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className="analysis-boundary" aria-labelledby="boundary-title">
        <div><p>PUBLICATION BOUNDARY</p><h2 id="boundary-title">公開サイトと研究環境を分けています</h2></div>
        <ul>
          <li>公開サイト: AIの仕組み、利用条件、予測準備状況を表示</li>
          <li>研究環境: 元CSV、個別予測、実名馬情報、モデルファイルを隔離</li>
          <li>評価集計値: 公開権限と再現可能な検証記録が確認できるまで「確認中」</li>
        </ul>
      </section>
    </main>
    <SiteFooter />
  </div>;
}
