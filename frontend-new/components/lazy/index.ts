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

export const LazyS3ConnectModal = lazy(() =>
  import("@/components/data-sources/S3ConnectModal").then((module) => ({
    default: module.S3ConnectModal,
  }))
);

export const LazySftpConnectModal = lazy(() =>
  import("@/components/data-sources/SftpConnectModal").then((module) => ({
    default: module.SftpConnectModal,
  }))
);

export const LazyHelpModal = lazy(() =>
  import("@/components/help/HelpModal").then((module) => ({
    default: module.HelpModal,
  }))
);
