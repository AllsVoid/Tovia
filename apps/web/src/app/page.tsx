import Link from "next/link";
import { Button } from "@/components/ui/button";
export default function Home() {
  return (
    <section className="space-y-8">
      <p className="text-xs tracking-[0.3em]">MY WORLD / 我的世界</p>
      <h1 className="text-4xl font-medium sm:text-5xl">凡我所至，皆有所记。</h1>
      <p className="max-w-xl leading-8 opacity-75">
        把旅途留在时间里，也留在地图上。从一段旅行开始，慢慢积累属于自己的世界。
      </p>
      <div className="flex gap-6 text-sm">
        <span>● 曾至</span>
        <span>◌ 将至</span>
        <span>○ 未至</span>
      </div>
      <div className="rounded-2xl border border-border bg-muted/40 px-8 py-20 text-center">
        <h2 className="text-xl">你的世界，从这里开始</h2>
        <p className="mb-6 mt-3 text-sm opacity-70">
          地图将在下一阶段开放。现在可以先建立旅行档案。
        </p>
        <Button asChild>
          <Link href="/trips">我的旅行</Link>
        </Button>
      </div>
    </section>
  );
}
