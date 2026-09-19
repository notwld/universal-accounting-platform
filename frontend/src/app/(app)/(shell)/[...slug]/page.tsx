import { notFound } from "next/navigation";
import { ModulePlaceholder } from "@/features/shell/module-placeholder";
import { resolveModulePage } from "@/features/shell/nav";

type Props = { params: Promise<{ slug: string[] }> };

export default async function ModulePage({ params }: Props) {
  const { slug } = await params;
  if (!slug.length) notFound();

  const pathname = "/" + slug.join("/");
  const page = resolveModulePage(pathname);
  if (!page) notFound();

  return <ModulePlaceholder title={page.label} group={page.group} />;
}
