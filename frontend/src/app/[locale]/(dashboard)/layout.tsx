import { AuthGuard } from "@/components/auth";
import { setRequestLocale } from "next-intl/server";
import { DashboardLayoutClient } from "./layout-client";

export default async function DashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <AuthGuard>
      <DashboardLayoutClient>
        {children}
      </DashboardLayoutClient>
    </AuthGuard>
  );
}
