const metrics = [
  {
    label: "AI予想1位の馬が勝った割合",
    value: "確認中",
    note: "過去レース研究評価の公開可否を権利台帳と照合中です。",
  },
  {
    label: "AI予想上位3頭に勝ち馬が含まれた割合",
    value: "確認中",
    note: "3連単・3連複の的中率ではありません。",
  },
  {
    label: "評価対象",
    value: "確認中",
    note: "東京ダート2100mの時系列テストに関する過去レース研究評価です。",
  },
];

export function PresentationOverview() {
  return <section className="presentation-overview" aria-labelledby="presentation-title">
    <div className="shell">
      <div className="presentation-heading">
        <p>COMPANY PRESENTATION · PUBLIC-SAFE OVERVIEW</p>
        <h2 id="presentation-title">過去レースを使ったAIモデルの研究評価</h2>
        <span>個別レースの予想とは独立した、東京ダート2100mの時系列テストに関する研究評価です。</span>
      </div>
      <div className="presentation-grid">
        <article className="presentation-story">
          <h3>研究評価の位置づけ</h3>
          <p>過去の着順・距離実績・競馬場経験・騎手の過去成績など、予測時点より前に利用可能な特徴量を用いてLightGBMを研究評価しています。結果や将来情報を予測特徴量には使いません。</p>
          <ol className="presentation-flow" aria-label="AI予想の流れ">
            <li><b>1</b><span>予測前に利用可能な情報を確認</span></li>
            <li><b>2</b><span>馬ごとの過去成績を集計</span></li>
            <li><b>3</b><span>LightGBMで比較用スコアを算出</span></li>
            <li><b>4</b><span>スコア順に候補を並べる</span></li>
          </ol>
        </article>
        <article className="presentation-evaluation">
          <h3>研究評価の公開状態</h3>
          <div className="presentation-metrics">
            {metrics.map((metric) => <div key={metric.label}><small>{metric.label}</small><strong>{metric.value}</strong><span>{metric.note}</span></div>)}
          </div>
          <p className="presentation-caution">評価の集計値は、個別レース（例: 11月7日の神奈川新聞杯）の予想精度ではありません。公開用の利用権限を確認できるまで、数値は表示しません。</p>
        </article>
      </div>
      <div className="presentation-proof">
        <div><b>評価指標について</b><span>公開可否が確認された場合、Top1はAI予想1位の馬が勝った割合、Top3はAI予想上位3頭に勝ち馬が含まれた割合として説明します。馬券の3連単・3連複の的中率ではありません。</span></div>
        <div><b>公開境界</b><span>研究用の馬名・個別予測・元CSVはVercelへ送らず、公開可能と確認された情報だけを掲載します。</span></div>
      </div>
      <div className="presentation-roadmap">
        <b>現在の表示</b><span>過去レースを使ったAIモデルの研究評価であること、評価条件、公開数値の確認状況を表示しています。</span>
        <b>次の段階</b><span>評価集計値の公開権限と再現可能な検証記録がそろった場合に限り、検証済み成果物を参照して数値を掲載します。</span>
      </div>
    </div>
  </section>;
}
