const metrics = [
  { label: "Top1 勝ち馬予測率", value: "22.15%", note: "1位候補が勝ち馬だった割合" },
  { label: "Top3候補内 勝ち馬率", value: "48.73%", note: "上位3候補に勝ち馬を含んだ割合" },
  { label: "評価対象", value: "158レース", note: "東京・ダート2100mの時系列テスト" },
];

export function PresentationOverview() {
  return <section className="presentation-overview" aria-labelledby="presentation-title">
    <div className="shell">
      <div className="presentation-heading">
        <p>COMPANY PRESENTATION · PUBLIC-SAFE OVERVIEW</p>
        <h2 id="presentation-title">競馬の「予想前」だけを読み解くAI</h2>
        <span>個別の研究データや実名ランキングは、この公開サイトには掲載していません。</span>
      </div>
      <div className="presentation-grid">
        <article className="presentation-story">
          <h3>どんなAI？</h3>
          <p>過去の着順傾向、距離への適性、競馬場での成績、騎手との組み合わせなど、レース開始前に分かる情報を整理し、LightGBMが各馬の相対的なスコアを計算します。</p>
          <ol className="presentation-flow" aria-label="AI予想の流れ">
            <li><b>1</b><span>発走前の情報を確認</span></li>
            <li><b>2</b><span>馬ごとの特徴量を作成</span></li>
            <li><b>3</b><span>LightGBMでスコアを算出</span></li>
            <li><b>4</b><span>スコア順に候補を並べる</span></li>
          </ol>
        </article>
        <article className="presentation-evaluation">
          <h3>検証済みの研究評価</h3>
          <div className="presentation-metrics">
            {metrics.map((metric) => <div key={metric.label}><small>{metric.label}</small><strong>{metric.value}</strong><span>{metric.note}</span></div>)}
          </div>
          <p className="presentation-caution">この数値は、モデル選択に使っていない時系列テストでの研究評価です。個別レースの成績や将来の的中を保証するものではありません。</p>
        </article>
      </div>
      <div className="presentation-proof">
        <div><b>推論の実施について</b><span>隔離されたローカル環境で、固定したモデルと発走前特徴量を使い、全出走馬のスコアと順位を再計算する検証手順を用意しています。</span></div>
        <div><b>公開範囲</b><span>研究用CSV、モデルファイル、個別の馬名・順位・スコアはVercelへ送信せず、公開APIからも参照できません。</span></div>
      </div>
      <div className="presentation-roadmap">
        <b>現在できること</b><span>研究モデルの評価、隔離環境での再現可能な推論、公開サイトでの仕組みの説明。</span>
        <b>次の段階</b><span>正規データ提供元の利用許諾を確認後、正式出馬表と成績データをローカル隔離環境へ取り込み、実レース予測へ拡張します。</span>
      </div>
    </div>
  </section>;
}
