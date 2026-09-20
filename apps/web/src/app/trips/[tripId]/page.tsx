import { TripDetail } from "@/components/trip-detail";

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ tripId: string }>;
  searchParams: Promise<{ addPlace?: string }>;
}) {
  const { tripId } = await params;
  const { addPlace } = await searchParams;
  return <TripDetail id={tripId} startAdding={addPlace === "1"} />;
}
