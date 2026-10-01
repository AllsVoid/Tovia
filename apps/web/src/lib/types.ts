export type TripStatus =
  "IDEA" | "PLANNING" | "BOOKED" | "TRAVELING" | "COMPLETED" | "ARCHIVED";
export type Scope = "domestic" | "international" | "all";
export type PlaceStatus = "visited" | "upcoming" | "wishlist";
export interface User {
  id: string;
  display_name: string;
  avatar_url: string | null;
  timezone: string;
  locale: string;
  created_at: string;
  updated_at: string;
}
export type BookingType =
  "FLIGHT" | "TRAIN" | "BUS" | "HOTEL" | "TICKET" | "RESTAURANT" | "OTHER";
export type BookingStatus = "PLANNED" | "CONFIRMED" | "COMPLETED" | "CANCELLED";
export interface BookingInput {
  trip_id: string | null;
  activity_id: string | null;
  type: BookingType;
  status: BookingStatus;
  title: string;
  provider_name: string | null;
  reference_no: string | null;
  start_at: string;
  end_at: string | null;
  timezone: string;
  end_timezone: string;
  origin_place_id: string | null;
  destination_place_id: string | null;
  address: string | null;
  amount: string | null;
  currency: string | null;
  note: string | null;
}
export interface Booking extends BookingInput {
  id: string;
  version: number;
}
export interface ExpenseInput {
  trip_id: string | null;
  trip_day_id: string | null;
  activity_id: string | null;
  place_id: string | null;
  merchant: string | null;
  category: string;
  original_amount: string;
  original_currency: string;
  settled_amount: string | null;
  settled_currency: string | null;
  exchange_rate: string | null;
  payment_method: string | null;
  occurred_at: string;
  timezone: string;
  note: string | null;
}
export interface Expense extends ExpenseInput {
  id: string;
  version: number;
}
export interface MoneyTotal {
  currency: string;
  amount: string;
}
export interface TripSummary {
  booking_count: number;
  expense_count: number;
  original_totals: MoneyTotal[];
  paid_totals: MoneyTotal[];
  categories: (MoneyTotal & { category: string })[];
}
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
  metadata?: { region_id?: string };
}
export interface Region {
  id: string;
  parent_id: string | null;
  name: string;
  short_name: string;
  path: string;
  pinyin: string;
  level: number;
  country_code: string;
  admin1: string | null;
  city: string | null;
  timezone: string;
  longitude: number;
  latitude: number;
  bbox: [number, number, number, number];
  boundary_file: string;
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
  region_id?: string | null;
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
