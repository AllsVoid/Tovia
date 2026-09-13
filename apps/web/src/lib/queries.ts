import type { QueryClient } from "@tanstack/react-query";
export async function refreshTravel(client: QueryClient): Promise<void> {
  await Promise.all(
    ["trips", "trip", "visits", "days", "activities", "map", "calendar"].map(
      (key) => client.invalidateQueries({ queryKey: [key] }),
    ),
  );
}
