export type TripStatus =
  "IDEA" | "PLANNING" | "BOOKED" | "TRAVELING" | "COMPLETED" | "ARCHIVED";
export type Scope = "domestic" | "international" | "all";
export type PlaceStatus = "visited" | "upcoming" | "wishlist";
export interface Trip {
  id: string;
  title: string;
  status: TripStatus;
  start_date: string | null;
  end_date: string | null;
  timezone: string;
  summary: string | null;
}
export interface Place {
  id: string;
  canonical_name: string;
  country_code: string | null;
  admin1: string | null;
  city: string | null;
  timezone: string;
  latitude: number;
  longitude: number;
}
export interface PlaceInput {
  canonical_name: string;
  country_code: string;
  city?: string;
  timezone: string;
  latitude: number;
  longitude: number;
}
export interface Visit {
  id: string;
  place_id: string;
  trip_id: string | null;
  trip_day_id: string | null;
  visited_at: string;
  ended_at: string | null;
  note: string | null;
}
export interface VisitInput {
  place_id: string;
  trip_id?: string | null;
  trip_day_id?: string | null;
  visited_at: string;
  ended_at?: string | null;
  note?: string | null;
}
export interface TripDay {
  id: string;
  trip_id: string;
  date: string;
  title: string | null;
  note: string | null;
  sort_order: number;
}
export interface Activity {
  id: string;
  trip_id: string;
  trip_day_id: string;
  place_id: string | null;
  type: string;
  title: string;
  start_at: string | null;
  end_at: string | null;
  status: string;
  note: string | null;
  sort_order: number;
}
export interface MapPlace {
  id: string;
  name: string;
  country_code: string | null;
  city: string | null;
  admin1: string | null;
  timezone: string;
  latitude: number;
  longitude: number;
  visit_count: number;
  upcoming_count: number;
  wishlist: boolean;
  last_visited_at: string | null;
  next_visit_at: string | null;
}
export interface MapPage {
  places: MapPlace[];
  total: number;
  limit: number;
  offset: number;
}
export interface MapSummary {
  places_count: number;
  visited_places: number;
  upcoming_places: number;
  wishlist_places: number;
  visit_count: number;
  countries_count: number;
  unknown_country_places: number;
}
export interface MapDetail {
  place: MapPlace;
  visits: Visit[];
  visits_total: number;
  wishlist_note: string | null;
}
export interface CalendarCell {
  date: string;
  trip_ids: string[];
  places_count: number;
  visits_count: number;
  activities_count: number;
  has_memory: boolean;
}
export interface CalendarMonth {
  year: number;
  month: number;
  days: CalendarCell[];
  trips: Trip[];
}
export interface CalendarDay {
  date: string;
  trips: Trip[];
  visits: (Visit & { place_name: string; timezone: string })[];
  activities: (Activity & { place_name: string | null; timezone: string })[];
}
