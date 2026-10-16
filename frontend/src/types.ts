// Page bridge types; formal artifact data is defined in publicationContracts.ts.
export interface Entity {
  id: string;
  version: string;
  title: string;
}
export type ArtifactKind = 'study' | 'strategy' | 'run' | 'series';
export interface Target extends Entity {
  kind: ArtifactKind;
}
export interface Reference {
  schemaVersion: 1;
  source: Target;
  kind: 'object' | 'text' | 'chart';
  locator: string;
  quote: string;
  createdAt: string;
  chart?: {
    metric: string;
    runIds: string[];
    date: string;
    values: Record<string, number>;
    zoom: [number, number];
    hidden: string[];
  };
}
export interface PublicationQuery {
  kind: ArtifactKind;
  query: string;
  series: string;
  sort: string;
  page: number;
}
export interface PublicationPage {
  items: import('./publicationContracts').PublicationSummary[];
  total: number;
  page: number;
}
export interface ResearchHost {
  request?<T>(operation: string, args: Record<string, unknown>): Promise<T>;
  previewFile?(path: string): void;
  publicationActions?: import('../ui/PublicationMore').PublicationActions;
  queryPublications?(request: PublicationQuery): Promise<PublicationPage>;
  readPublicationFile?(
    reference: import('./publicationContracts').PublicationRef,
    path: string,
  ): Promise<string>;
  readCover?(
    reference: import('./publicationContracts').PublicationRef,
    path: string,
  ): Promise<string>;
  readFile?(path: string): Promise<string>;
  readImage?(path: string): Promise<string>;
  protocolVersion: 1;
  open(target: Target): void;
  reference(reference: Reference): void;
}
export const keyOf = (target: Target) => `${target.kind}:${target.id}@${target.version}`;
export const percent = (value: number) => `${(value * 100).toFixed(2)}%`;
export function objectReference(source: Target, locator = 'title'): Reference {
  return {
    schemaVersion: 1,
    source,
    locator,
    kind: 'object',
    quote: source.title,
    createdAt: new Date().toISOString(),
  };
}
