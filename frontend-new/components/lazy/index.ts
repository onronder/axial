import { lazy } from "react";

export const LazyGlobalIngestModal = lazy(() =>
  import("@/components/GlobalIngestModal").then((module) => ({
    default: module.GlobalIngestModal,
  }))
);

export const LazyGlobalProgress = lazy(() =>
  import("@/components/layout/global-progress").then((module) => ({
    default: module.GlobalProgress,
  }))
);
