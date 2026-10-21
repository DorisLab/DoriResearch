// DoriResearch reading contract. The desktop consumes this boundary without owning its database.
export type DataNature = 'real' | 'synthetic' | 'mixed' | 'none';

export type PublicationContent = {
  config?: {
    backtest?: BacktestConfig;
    parameters?: Record<string, unknown>;
    source_commit?: string;
  };
  body: string;
  cover_url?: string | null;
  files: Array<PublicationFile>;
  item: PublicationSummary;
  previous?: PublicationRef | null;
  references: Array<PublicationRef>;
  revision_note: string;
};

export interface BacktestConfig {
  callable: string;
  date_range?: { start?: string; end?: string };
  parameters: Array<{
    name: string;
    label: string;
    type: 'number' | 'text';
    default: string | number;
    min?: number;
    max?: number;
    step?: number;
    unit?: string;
  }>;
}

export type PublicationFile = {
  bytes: number;
  media_type: string;
  path: string;
  role: string;
  sha256: string;
};

export type PublicationKind = 'study' | 'strategy' | 'run' | 'series';

export type PublicationOrigin = 'project' | 'imported' | 'example';

export type PublicationRef = {
  id: string;
  kind: PublicationKind;
  version: string;
};

export type PublicationSummary = {
  cover?: string | null;
  data_nature: DataNature;
  files?: Array<PublicationFile>;
  origin: PublicationOrigin;
  project_format?: string;
  reference: PublicationRef;
  references?: Array<PublicationRef>;
  registered_at: number;
  snippet: string;
  summary: string;
  title: string;
};
