import { AppShell } from "@/features/shell/app-shell";
import { DashboardHome } from "@/features/shell/dashboard-home";

export default function DashboardPage() {
  return (
    <AppShell>
      <DashboardHome />
    </AppShell>
  );
}
