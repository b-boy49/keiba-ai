import { HomePage } from "@/components/home/HomePage";
import { raceRepository } from "@/lib/data-providers";

export default async function Home() {
  const races = await raceRepository.list();
  const localPresentationDemoEnabled = process.env.NODE_ENV === "development" && process.env.KEIBA_LOCAL_PRESENTATION_DEMO === "true";
  return <HomePage races={races} localPresentationDemoEnabled={localPresentationDemoEnabled} />;
}
