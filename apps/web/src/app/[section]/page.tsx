import { notFound } from "next/navigation";
const sections: Record<string, { title: string; description: string }> = {
  inbox: {
    title: "收件箱",
    description: "未来可以在这里保存旅途中的原始资料。",
  },
  profile: {
    title: "我的",
    description: "当前为本地开发版本，使用独立的开发用户。",
  },
};
export default async function Section({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  const content = sections[section];
  if (!content) notFound();
  return (
    <section>
      <h1 className="text-3xl">{content.title}</h1>
      <p className="mt-6 opacity-70">{content.description}</p>
    </section>
  );
}
