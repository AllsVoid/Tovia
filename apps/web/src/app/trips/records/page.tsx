import Link from "next/link";
import { TripFinance } from "@/components/trip-finance";

export default function RecordsPage() {
  return (
    <section className="space-y-6">
      <Link className="text-link" href="/trips">
        ← 我的旅行
      </Link>
      <header className="page-heading">
        <div>
          <p className="eyebrow">TRAVEL RECORDS</p>
          <h1>全部预订与费用</h1>
          <p className="muted mt-3">
            独立账目与各次旅行的记录。删除旅行后，预订和费用仍可在这里维护或重新关联。
          </p>
        </div>
      </header>
      <TripFinance />
    </section>
  );
}
