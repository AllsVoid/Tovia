import { TripDetail } from "@/components/trip-detail";

export default async function Page({
  params,
}: {
  params: Promise<{ tripId: string }>;
}) {
  const { tripId } = await params;
  return <TripDetail id={tripId} />;
}
