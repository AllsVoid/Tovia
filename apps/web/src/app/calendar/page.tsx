import { Suspense } from "react";
import { TravelCalendar } from "@/components/travel-calendar";
export default function CalendarPage() {
  return (
    <Suspense fallback={<p role="status">正在打开日历…</p>}>
      <TravelCalendar />
    </Suspense>
  );
}
