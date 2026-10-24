import { DataStatusBadge } from "@/components/ui/DataStatusBadge";
import { raceStatusLabel, type RaceStatus } from "@/types/race";
export function RaceStatus({ status, isDemo }: { status: RaceStatus; isDemo: boolean }) { return <span className="status-set"><DataStatusBadge label={raceStatusLabel[status]} />{isDemo && <DataStatusBadge label="デモデータ" />}</span>; }
