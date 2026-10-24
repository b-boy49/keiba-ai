import type { Race } from "@/types/race";

export type RaceSearch = { date?: string; courseId?: string; query?: string };
export interface RaceRepository { list(search?: RaceSearch): Promise<Race[]>; getById(id: string): Promise<Race | null>; }
