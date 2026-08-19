import { InvestigationWorkspace } from "./workspace";

export default async function InvestigationPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <InvestigationWorkspace runId={runId} />;
}
