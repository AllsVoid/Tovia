import { notFound } from "next/navigation";
import { ProfilePage } from "@/components/profile-page";
export default async function Section({
  params,
  searchParams,
}: {
  params: Promise<{ section: string }>;
  searchParams: Promise<{ reauth?: string }>;
}) {
  const { section } = await params;
  const query = await searchParams;
  if (section === "profile")
    return <ProfilePage reauthenticated={query.reauth === "delete"} />;
  notFound();
}
