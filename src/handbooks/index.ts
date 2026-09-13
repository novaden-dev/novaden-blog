import type { HandbookConfig } from "./types";
import { oscp } from "./oscp";

// The handbook registry: the single place that knows which handbooks exist.
// Register a new handbook by importing its config and adding it here. No UI,
// route, or utility changes are required.
//
//   import { devops } from "./devops";
//   export const HANDBOOKS = { oscp, devops };
export const HANDBOOKS: Record<string, HandbookConfig> = {
  oscp,
};

export type { HandbookConfig } from "./types";

export const handbookConfigs = (): HandbookConfig[] => Object.values(HANDBOOKS);

export const handbookIds = (): string[] => Object.keys(HANDBOOKS);

export const getHandbookConfig = (
  id: string | undefined
): HandbookConfig | undefined => (id ? HANDBOOKS[id] : undefined);

export const isHandbookId = (id: string | undefined): boolean =>
  !!id && id in HANDBOOKS;
