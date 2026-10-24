type DataStatusBadgeProps = {
  label?: string;
  detail?: string;
};

export function DataStatusBadge({ label = "データ未取得", detail }: DataStatusBadgeProps) {
  return <span className="data-status" title={detail}>{label}</span>;
}
