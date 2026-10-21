import { ChartLine, Flask, Microscope, Stack, TreeStructure } from '@phosphor-icons/react';

const icons = {
  'research-room': Microscope,
  study: Flask,
  strategy: TreeStructure,
  run: ChartLine,
  series: Stack,
};
export function ResearchIcon({
  kind,
  className = 'research-icon',
}: {
  kind: keyof typeof icons;
  className?: string;
}) {
  const Icon = icons[kind];
  return <Icon weight="light" aria-hidden="true" data-icon={kind} className={className} />;
}
