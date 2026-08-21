import { createContext, useContext } from 'react';
import type { Profile } from '@/services/api';

export interface DatasetState {
  datasetId: string | null;
  profile: Profile | null;
  setDataset: (id: string, profile: Profile) => void;
  clearDataset: () => void;
}

export const DatasetContext = createContext<DatasetState | null>(null);

export function useDataset(): DatasetState {
  const ctx = useContext(DatasetContext);
  if (!ctx) throw new Error('useDataset must be used within DatasetProvider');
  return ctx;
}
