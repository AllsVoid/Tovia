import { Suspense } from "react";
import { MyWorld } from "@/components/my-world";
export default function Home() {
  return (
    <Suspense fallback={<p role="status">正在打开我的世界…</p>}>
      <MyWorld />
    </Suspense>
  );
}
