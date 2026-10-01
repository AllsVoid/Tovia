"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type Booking,
  type BookingInput,
  type BookingType,
  type BookingStatus,
  type Expense,
  type ExpenseInput,
  type Trip,
} from "@/lib/api";
import {
  formatInstant,
  inputToInstant,
  instantToLocalInput,
} from "@/lib/dates";
import { refreshTravel } from "@/lib/queries";
import { Button } from "./ui/button";
import { QueryError } from "./query-error";
import { PlacePicker } from "./place-picker";

const bookingTypes: Record<BookingType, string> = {
  FLIGHT: "航班",
  TRAIN: "火车",
  BUS: "巴士",
  HOTEL: "住宿",
  TICKET: "门票",
  RESTAURANT: "餐厅",
  OTHER: "其他",
};
const bookingStatuses: Record<BookingStatus, string> = {
  PLANNED: "待预订",
  CONFIRMED: "已确认",
  COMPLETED: "已完成",
  CANCELLED: "已取消",
};
const categories = {
  TRANSPORT: "交通",
  HOTEL: "住宿",
  FOOD: "餐饮",
  TICKET: "门票",
  SHOPPING: "购物",
  OTHER: "其他",
};
type Kind = "booking" | "expense";
const money = (amount: string, currency: string) => `${currency} ${amount}`;
const text = (form: FormData, key: string) =>
  String(form.get(key) ?? "").trim();
const nullable = (form: FormData, key: string) => text(form, key) || null;
// Keep seconds and subsecond precision when the user edits only other fields.
const instant = (form: FormData, key: string, previous?: string | null) => {
  const value = text(form, key);
  if (!value) return null;
  return previous && value === instantToLocalInput(previous)
    ? previous
    : inputToInstant(value);
};

function Field({
  label,
  name,
  value,
  required = false,
  type = "text",
  maxLength = 200,
  decimal = false,
  suggestions,
}: {
  label: string;
  name: string;
  value?: string | null;
  required?: boolean;
  type?: string;
  maxLength?: number;
  decimal?: boolean;
  suggestions?: string[];
}) {
  return (
    <label className="field">
      {label}
      <input
        name={name}
        defaultValue={value ?? ""}
        required={required}
        type={type}
        maxLength={maxLength}
        inputMode={decimal ? "decimal" : undefined}
        pattern={decimal ? "[0-9]+(\\.[0-9]{1,8})?" : undefined}
        list={suggestions ? `${name}-choices` : undefined}
      />
      {suggestions && (
        <datalist id={`${name}-choices`}>
          {suggestions.map((choice) => (
            <option key={choice} value={choice} />
          ))}
        </datalist>
      )}
    </label>
  );
}

function PlaceField({
  label,
  name,
  initial,
}: {
  label: string;
  name: string;
  initial?: string | null;
}) {
  const [placeId, setPlaceId] = useState(initial ?? null);
  const place = useQuery({
    queryKey: ["place", placeId],
    queryFn: () => api.place(placeId!),
    enabled: Boolean(placeId),
  });
  return (
    <fieldset className="space-y-2 min-w-0 rounded-lg border border-border p-3">
      <legend className="px-1 text-sm">{label}</legend>
      <input type="hidden" name={name} value={placeId ?? ""} />
      {placeId && !place.data ? (
        <>
          <p className="muted">正在读取地点…</p>
          {place.error && (
            <QueryError
              error={place.error}
              retry={() => void place.refetch()}
            />
          )}
        </>
      ) : (
        <PlacePicker
          value={placeId ? (place.data ?? null) : null}
          onChange={(value) => setPlaceId(value?.id ?? null)}
        />
      )}
      {placeId && (
        <button
          type="button"
          className="text-button"
          onClick={() => setPlaceId(null)}
        >
          清除地点关联
        </button>
      )}
      <p className="muted">可留空，具体站点或酒店地址写入备注/地址。</p>
    </fieldset>
  );
}

function FinanceForm({
  kind,
  trip,
  record,
  onDone,
}: {
  kind: Kind;
  trip?: Trip;
  record?: Booking | Expense;
  onDone: () => void;
}) {
  const client = useQueryClient();
  const booking =
    kind === "booking" ? (record as Booking | undefined) : undefined;
  const expense =
    kind === "expense" ? (record as Expense | undefined) : undefined;
  const [tripId, setTripId] = useState(
    record ? (record.trip_id ?? "") : (trip?.id ?? ""),
  );
  const [dayId, setDayId] = useState(expense?.trip_day_id ?? "");
  const [activityId, setActivityId] = useState(record?.activity_id ?? "");
  const trips = useQuery({ queryKey: ["trips"], queryFn: () => api.trips() });
  const days = useQuery({
    queryKey: ["days", tripId],
    queryFn: () => api.days(tripId),
    enabled: Boolean(tripId),
  });
  const activities = useQuery({
    queryKey: ["activities", tripId],
    queryFn: () => api.activities(tripId),
    enabled: Boolean(tripId),
  });
  const mutation = useMutation({
    mutationFn: async (form: FormData) => {
      if (kind === "booking") {
        const input: BookingInput = {
          trip_id: tripId || null,
          activity_id: activityId || null,
          type: text(form, "type") as BookingType,
          status: text(form, "status") as BookingStatus,
          title: text(form, "title"),
          provider_name: nullable(form, "provider_name"),
          reference_no: nullable(form, "reference_no"),
          start_at: instant(form, "start_at", booking?.start_at)!,
          end_at: instant(form, "end_at", booking?.end_at),
          timezone: text(form, "timezone"),
          end_timezone: text(form, "end_timezone"),
          origin_place_id: nullable(form, "origin_place_id"),
          destination_place_id: nullable(form, "destination_place_id"),
          address: nullable(form, "address"),
          amount: nullable(form, "amount"),
          currency: nullable(form, "currency"),
          note: nullable(form, "note"),
        };
        if ((input.amount === null) !== (input.currency === null))
          throw new Error("预订金额与币种请一起填写或一起留空。");
        if (
          input.end_at &&
          new Date(input.end_at).getTime() < new Date(input.start_at).getTime()
        )
          throw new Error("结束时间不能早于开始时间。");
        return booking
          ? api.updateBooking(booking.id, {
              ...input,
              version: booking.version,
            })
          : api.createBooking(input);
      }
      const input: ExpenseInput = {
        trip_id: tripId || null,
        trip_day_id: dayId || null,
        activity_id: activityId || null,
        place_id: nullable(form, "place_id"),
        merchant: nullable(form, "merchant"),
        category: text(form, "category"),
        original_amount: text(form, "original_amount"),
        original_currency: text(form, "original_currency"),
        settled_amount: nullable(form, "settled_amount"),
        settled_currency: nullable(form, "settled_currency"),
        exchange_rate: nullable(form, "exchange_rate"),
        payment_method: nullable(form, "payment_method"),
        occurred_at: instant(form, "occurred_at", expense?.occurred_at)!,
        timezone: text(form, "timezone"),
        note: nullable(form, "note"),
      };
      if ((input.settled_amount === null) !== (input.settled_currency === null))
        throw new Error("结算金额与币种请一起填写或一起留空。");
      if (input.exchange_rate && !input.settled_amount)
        throw new Error("填写实际汇率时，请同时填写结算金额和币种。");
      return expense
        ? api.updateExpense(expense.id, { ...input, version: expense.version })
        : api.createExpense(input);
    },
    onSuccess: async () => {
      await refreshTravel(client);
      onDone();
    },
  });
  const selectedTimezone =
    trips.data?.find((t) => t.id === tripId)?.timezone ??
    trip?.timezone ??
    "UTC";
  return (
    <form
      aria-label={kind === "booking" ? "预订表单" : "费用表单"}
      className="space-y-4 rounded-xl border border-border bg-muted p-4"
      onSubmit={(event) => {
        event.preventDefault();
        mutation.mutate(new FormData(event.currentTarget));
      }}
    >
      <h3 className="text-lg">
        {record ? "编辑" : "添加"}
        {kind === "booking" ? "预订" : "费用"}
      </h3>
      <p className="muted">
        时间输入使用设备时区（{Intl.DateTimeFormat().resolvedOptions().timeZone}
        ）；保存为明确的时间点，按下方记录时区展示。金额最多 4
        位小数，实际汇率最多 8 位小数。
      </p>
      <div className="form-grid">
        <label className="field">
          所属旅行
          <select
            value={tripId}
            onChange={(e) => {
              setTripId(e.target.value);
              setDayId("");
              setActivityId("");
            }}
          >
            <option value="">独立记录</option>
            {trips.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.title}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          关联活动
          <select
            value={activityId}
            disabled={!tripId || activities.isPending}
            onChange={(e) => setActivityId(e.target.value)}
          >
            <option value="">不关联活动</option>
            {activities.data?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title}
              </option>
            ))}
          </select>
        </label>
        {kind === "booking" ? (
          <>
            <Field
              label="预订名称"
              name="title"
              required
              value={booking?.title}
            />
            <label className="field">
              预订类型
              <select name="type" defaultValue={booking?.type ?? "FLIGHT"}>
                {Object.entries(bookingTypes).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              预订状态
              <select
                name="status"
                defaultValue={booking?.status ?? "CONFIRMED"}
              >
                {Object.entries(bookingStatuses).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <Field
              label="供应商"
              name="provider_name"
              value={booking?.provider_name}
            />
            <Field
              label="确认号"
              name="reference_no"
              value={booking?.reference_no}
            />
            <Field
              label="开始时间（设备时区）"
              name="start_at"
              type="datetime-local"
              required
              value={instantToLocalInput(booking?.start_at ?? null)}
            />
            <Field
              label="结束时间（设备时区）"
              name="end_at"
              type="datetime-local"
              value={instantToLocalInput(booking?.end_at ?? null)}
            />
            <Field
              label="开始地点时区"
              name="timezone"
              required
              value={booking?.timezone ?? selectedTimezone}
              maxLength={64}
            />
            <Field
              label="结束地点时区"
              name="end_timezone"
              required
              value={booking?.end_timezone ?? selectedTimezone}
              maxLength={64}
            />
            <Field
              label="预订价格（选填）"
              name="amount"
              value={booking?.amount}
              decimal
            />
            <Field
              label="预订币种（选填）"
              name="currency"
              value={booking?.currency}
              maxLength={3}
            />
            <Field
              label="详细地址 / 站点"
              name="address"
              value={booking?.address}
              maxLength={10000}
            />
          </>
        ) : (
          <>
            <label className="field">
              关联旅行日
              <select
                value={dayId}
                disabled={!tripId || days.isPending}
                onChange={(e) => {
                  setDayId(e.target.value);
                  setActivityId("");
                }}
              >
                <option value="">不关联旅行日</option>
                {days.data?.map((day) => (
                  <option key={day.id} value={day.id}>
                    {day.date} · {day.title || "自由探索"}
                  </option>
                ))}
              </select>
            </label>
            <Field label="商户" name="merchant" value={expense?.merchant} />
            <Field
              label="费用类别"
              name="category"
              value={expense?.category ?? "其他"}
              suggestions={Object.values(categories)}
              required
              maxLength={64}
            />
            <Field
              label="原币金额"
              name="original_amount"
              required
              value={expense?.original_amount}
              decimal
            />
            <Field
              label="原币币种"
              name="original_currency"
              required
              value={expense?.original_currency ?? "CNY"}
              maxLength={3}
            />
            <Field
              label="结算金额（选填）"
              name="settled_amount"
              value={expense?.settled_amount}
              decimal
            />
            <Field
              label="结算币种（选填）"
              name="settled_currency"
              value={expense?.settled_currency}
              maxLength={3}
            />
            <Field
              label="实际汇率（结算币 / 原币，选填）"
              name="exchange_rate"
              value={expense?.exchange_rate}
              decimal
            />
            <Field
              label="支付方式"
              name="payment_method"
              value={expense?.payment_method}
              maxLength={64}
            />
            <Field
              label="消费时间（设备时区）"
              name="occurred_at"
              type="datetime-local"
              required
              value={instantToLocalInput(expense?.occurred_at ?? null)}
            />
            <Field
              label="记录时区"
              name="timezone"
              required
              value={expense?.timezone ?? selectedTimezone}
              maxLength={64}
            />
          </>
        )}
      </div>
      <p className="muted">
        币种使用大写代码，如
        CNY、HKD、USD、JPY。费用类别可选择交通、住宿、餐饮等，也可填写自定义名称。不会自动换汇。
      </p>
      <div className="form-grid">
        {kind === "booking" ? (
          <>
            <PlaceField
              label="出发 / 入住地点"
              name="origin_place_id"
              initial={booking?.origin_place_id}
            />
            <PlaceField
              label="抵达 / 目的地点"
              name="destination_place_id"
              initial={booking?.destination_place_id}
            />
          </>
        ) : (
          <PlaceField
            label="消费地点"
            name="place_id"
            initial={expense?.place_id}
          />
        )}
      </div>
      <label className="field">
        备注
        <textarea
          name="note"
          defaultValue={record?.note ?? ""}
          maxLength={10000}
          rows={3}
        />
      </label>
      {trips.error && (
        <QueryError error={trips.error} retry={() => void trips.refetch()} />
      )}
      {days.error && tripId && (
        <QueryError error={days.error} retry={() => void days.refetch()} />
      )}
      {activities.error && tripId && (
        <QueryError
          error={activities.error}
          retry={() => void activities.refetch()}
        />
      )}
      {mutation.error && (
        <p role="alert" className="error-message">
          {mutation.error.message}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button disabled={mutation.isPending}>
          {mutation.isPending
            ? "保存中…"
            : kind === "booking"
              ? "保存预订"
              : "保存费用"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={mutation.isPending}
          onClick={onDone}
        >
          取消
        </Button>
      </div>
    </form>
  );
}

export function TripFinance({ trip }: { trip?: Trip }) {
  const client = useQueryClient();
  const [kind, setKind] = useState<Kind>("booking");
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<{
    kind: Kind;
    record?: Booking | Expense;
  } | null>(null);
  const bookings = useQuery({
    queryKey: ["bookings", trip?.id, offset],
    queryFn: () => api.bookings(trip?.id, offset),
    enabled: kind === "booking",
  });
  const expenses = useQuery({
    queryKey: ["expenses", trip?.id, offset],
    queryFn: () => api.expenses(trip?.id, offset),
    enabled: kind === "expense",
  });
  const summary = useQuery({
    queryKey: ["trip-summary", trip?.id],
    queryFn: () => api.tripSummary(trip!.id),
    enabled: Boolean(trip),
  });
  const deletion = useMutation({
    mutationFn: ({
      kind,
      record,
    }: {
      kind: Kind;
      record: Booking | Expense;
    }) =>
      kind === "booking"
        ? api.deleteBooking(record.id, record.version)
        : api.deleteExpense(record.id, record.version),
    onSuccess: () => refreshTravel(client),
  });
  const current = kind === "booking" ? bookings : expenses;
  return (
    <section className="panel space-y-5" aria-label="预订与费用管理">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl">预订与费用</h2>
        {trip && (
          <Link className="text-link" href="/trips/records">
            查看全部及独立记录 ↗
          </Link>
        )}
      </div>
      {summary.isPending && trip && (
        <p role="status" className="muted">
          正在汇总旅行账目…
        </p>
      )}
      {summary.error && (
        <QueryError
          error={summary.error}
          retry={() => void summary.refetch()}
        />
      )}
      {summary.data && (
        <div
          className="space-y-2 rounded-lg bg-muted p-4"
          aria-label="旅行账目汇总"
        >
          <p>
            {summary.data.booking_count} 项预订 · {summary.data.expense_count}{" "}
            笔费用
          </p>
          <p className="font-medium">
            实际花费：
            {summary.data.paid_totals
              .map((m) => money(m.amount, m.currency))
              .join(" / ") || "暂无费用"}
          </p>
          <p className="muted">
            原币合计：
            {summary.data.original_totals
              .map((m) => money(m.amount, m.currency))
              .join(" / ") || "暂无费用"}
          </p>
          <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
            {summary.data.categories.map((m) => (
              <li key={`${m.category}-${m.currency}`}>
                {categories[m.category as keyof typeof categories] ??
                  m.category}{" "}
                · {money(m.amount, m.currency)}
              </li>
            ))}
          </ul>
          <p className="muted">
            已填写结算金额时采用结算值，其余费用按原币分别汇总。预订价格不计入花费。
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={kind === "booking" ? "default" : "outline"}
          onClick={() => {
            setKind("booking");
            setOffset(0);
          }}
        >
          预订
        </Button>
        <Button
          variant={kind === "expense" ? "default" : "outline"}
          onClick={() => {
            setKind("expense");
            setOffset(0);
          }}
        >
          费用
        </Button>
        <Button variant="outline" onClick={() => setEditing({ kind })}>
          {kind === "booking" ? "添加预订" : "添加费用"}
        </Button>
      </div>
      {editing && (
        <FinanceForm
          key={editing.record?.id ?? `new-${editing.kind}`}
          kind={editing.kind}
          trip={trip}
          record={editing.record}
          onDone={() => setEditing(null)}
        />
      )}
      {deletion.error && (
        <p role="alert" className="error-message">
          {deletion.error.message}
        </p>
      )}
      {current.isPending && (
        <p role="status">正在读取{kind === "booking" ? "预订" : "费用"}…</p>
      )}
      {current.error && (
        <QueryError
          error={current.error}
          retry={() => void current.refetch()}
        />
      )}
      {current.data?.length === 0 && (
        <p className="muted">
          这一页暂无{kind === "booking" ? "预订" : "费用"}
          。可手工添加交通、住宿或消费记录。
        </p>
      )}
      <ul className="space-y-3">
        {current.data?.map((record) => (
          <li key={record.id} className="rounded-lg border border-border p-4">
            <div className="flex flex-wrap justify-between gap-3">
              <div className="min-w-0 break-words">
                {"title" in record ? (
                  <>
                    <p className="font-medium">
                      {record.title} · {bookingTypes[record.type]}
                    </p>
                    <p className="muted">
                      {bookingStatuses[record.status]}
                      {record.reference_no && ` · ${record.reference_no}`}
                      {record.provider_name && ` · ${record.provider_name}`}
                    </p>
                    <p className="muted">
                      {formatInstant(record.start_at, record.timezone)} (
                      {record.timezone})
                      {record.end_at &&
                        ` → ${formatInstant(record.end_at, record.end_timezone)} (${record.end_timezone})`}
                    </p>
                    {record.amount !== null && (
                      <p className="text-sm">
                        预订价格：{money(record.amount, record.currency!)}
                      </p>
                    )}
                    {record.address && (
                      <p className="text-sm">{record.address}</p>
                    )}
                  </>
                ) : (
                  <>
                    <p className="font-medium">
                      {record.merchant || "费用记录"} ·{" "}
                      {categories[record.category as keyof typeof categories] ??
                        record.category}
                    </p>
                    <p>
                      {money(record.original_amount, record.original_currency)}
                      {record.settled_amount !== null &&
                        ` → 结算 ${money(record.settled_amount, record.settled_currency!)}`}
                    </p>
                    <p className="muted">
                      {formatInstant(record.occurred_at, record.timezone)} (
                      {record.timezone})
                      {record.payment_method && ` · ${record.payment_method}`}
                    </p>
                    {record.exchange_rate && (
                      <p className="muted">实际汇率：{record.exchange_rate}</p>
                    )}
                  </>
                )}
                {record.note && (
                  <p className="mt-2 text-sm whitespace-pre-wrap">
                    {record.note}
                  </p>
                )}
                {!trip && (
                  <p className="mt-2 text-sm">
                    {record.trip_id ? (
                      <Link
                        className="text-link"
                        href={`/trips/${record.trip_id}`}
                      >
                        查看所属旅行 ↗
                      </Link>
                    ) : (
                      "独立记录"
                    )}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 gap-3">
                <button
                  className="text-button"
                  onClick={() => setEditing({ kind, record })}
                >
                  编辑{kind === "booking" ? "预订" : "费用"}
                </button>
                <button
                  className="text-button"
                  disabled={deletion.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        `删除这${kind === "booking" ? "项预订" : "笔费用"}？不会删除关联旅行、地点或活动。`,
                      )
                    )
                      deletion.mutate({ kind, record });
                  }}
                >
                  删除{kind === "booking" ? "预订" : "费用"}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          disabled={offset === 0 || current.isFetching}
          onClick={() => setOffset(Math.max(0, offset - 50))}
        >
          上一页
        </Button>
        <span className="muted">第 {offset / 50 + 1} 页</span>
        <Button
          variant="outline"
          disabled={current.data?.length !== 50 || current.isFetching}
          onClick={() => setOffset(offset + 50)}
        >
          下一页
        </Button>
      </div>
    </section>
  );
}
