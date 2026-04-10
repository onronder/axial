import * as React from "react";
import * as RechartsPrimitive from "recharts";

import { cn } from "@/lib/utils";

// Recharts exposes these in multiple files with differing paths per version; define locally for stability.
type NameType = string | number;
type ValueType = number | string | Array<number | string>;

// Format: { THEME_NAME: CSS_SELECTOR }
const THEMES = { light: "", dark: ".dark" } as const;
const SAFE_COLOR_KEYWORDS = new Set([
  "transparent",
  "currentcolor",
  "inherit",
  "initial",
  "unset",
  "revert",
  "revert-layer",
  "white",
  "black",
]);

function isSafeChartColor(value: string) {
  const color = value.trim();
  if (!color) {
    return false;
  }

  if (SAFE_COLOR_KEYWORDS.has(color.toLowerCase())) {
    return true;
  }

  return (
    /^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(color) ||
    /^(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch)\([^;{}<>]+\)$/i.test(color) ||
    /^var\(\s*--[\w-]+(?:\s*,\s*[^;{}<>]+)?\)$/i.test(color)
  );
}

function buildChartStyleContent(id: string, config: ChartConfig) {
  return Object.entries(THEMES)
    .map(
      ([theme, prefix]) => `
${prefix} [data-chart=${id}] {
${Object.entries(config)
          .filter(([_, itemConfig]) => itemConfig.theme || itemConfig.color)
          .map(([key, itemConfig]) => {
            const rawColor =
              itemConfig.theme?.[theme as keyof typeof itemConfig.theme] || itemConfig.color;
            const color = rawColor && isSafeChartColor(rawColor) ? rawColor : null;
            return color ? `  --color-${key}: ${color};` : null;
          })
          .filter(Boolean)
          .join("\n")}
}
`,
    )
    .join("\n");
}

export type ChartConfig = {
  [k in string]: {
    label?: React.ReactNode;
    icon?: React.ComponentType;
  } & ({ color?: string; theme?: never } | { color?: never; theme: Record<keyof typeof THEMES, string> });
};

type ChartContextProps = {
  config: ChartConfig;
};

const ChartContext = React.createContext<ChartContextProps | null>(null);

function useChart() {
  const context = React.useContext(ChartContext);

  if (!context) {
    throw new Error("useChart must be used within a <ChartContainer />");
  }

  return context;
}

const ChartContainer = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<"div"> & {
    config: ChartConfig;
    children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>["children"];
  }
>(({ id, className, children, config, ...props }, ref) => {
  const uniqueId = React.useId();
  const chartId = `chart-${id || uniqueId.replace(/:/g, "")}`;

  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-chart={chartId}
        ref={ref}
        className={cn(
          "flex aspect-video justify-center text-xs [&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-border/50 [&_.recharts-curve.recharts-tooltip-cursor]:stroke-border [&_.recharts-dot[stroke='#fff']]:stroke-transparent [&_.recharts-layer]:outline-none [&_.recharts-polar-grid_[stroke='#ccc']]:stroke-border [&_.recharts-radial-bar-background-sector]:fill-muted [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-muted [&_.recharts-reference-line_[stroke='#ccc']]:stroke-border [&_.recharts-sector[stroke='#fff']]:stroke-transparent [&_.recharts-sector]:outline-none [&_.recharts-surface]:outline-none",
          className,
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>{children}</RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
});
ChartContainer.displayName = "Chart";

const ChartStyle = ({ id, config }: { id: string; config: ChartConfig }) => {
  const styleContent = buildChartStyleContent(id, config);

  if (!styleContent.trim()) {
    return null;
  }

  return (
    <style
      dangerouslySetInnerHTML={{
        __html: styleContent,
      }}
    />
  );
};

const ChartTooltip = RechartsPrimitive.Tooltip;

// Lightweight payload shape used in tooltips/legends; permissive enough for all Recharts series.
type ChartPayload = {
  name?: NameType;
  value?: ValueType;
  dataKey?: string | number;
  color?: string;
  fill?: string;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
};
type ChartLabelFormatter = (
  label: string | number | null,
  payload?: ReadonlyArray<ChartPayload>,
) => React.ReactNode;
type ChartValueFormatter = (
  value: ValueType,
  name: NameType,
  item: ChartPayload,
  index: number,
  payload?: ReadonlyArray<ChartPayload>,
) => React.ReactNode;

// Keep the props local to avoid tight coupling with Recharts generics that differ across versions.
type TooltipContentProps = React.HTMLAttributes<HTMLDivElement> & {
  active?: boolean;
  label?: string | number | null;
  payload?: ReadonlyArray<ChartPayload>;
  // Optional keys used to look up labels in config/payload
  labelKey?: string;
  nameKey?: string;
  hideLabel?: boolean;
  hideIndicator?: boolean;
  indicator?: "line" | "dot" | "dashed";
  labelClassName?: string;
  labelFormatter?: ChartLabelFormatter;
  formatter?: ChartValueFormatter;
  color?: string;
};

const ChartTooltipContent = React.forwardRef<
  HTMLDivElement,
  TooltipContentProps
>(({ active, payload = [], className, indicator = "dot", hideLabel = false, hideIndicator = false, label, labelFormatter, labelClassName, formatter, color, nameKey, labelKey, ...divProps }, ref) => {
  const { config } = useChart();
  const tooltipPayload = React.useMemo<ChartPayload[]>(
    () => (Array.isArray(payload) ? (payload as ChartPayload[]) : []),
    [payload],
  );

  const tooltipLabel = React.useMemo(() => {
    if (hideLabel || !tooltipPayload.length) {
      return null;
    }

    const [item] = tooltipPayload;
    const key = `${labelKey || item.dataKey || item.name || "value"}`;
    const itemConfig = getPayloadConfigFromPayload(config, item, key);
    const value =
      !labelKey && typeof label === "string"
        ? config[label as keyof typeof config]?.label || label
        : itemConfig?.label;

    const labelValue: string | number | null | undefined =
      typeof value === "string" || typeof value === "number"
        ? value
        : typeof label === "string" || typeof label === "number"
        ? label
        : null;

    if (labelFormatter) {
      return (
        <div className={cn("font-medium", labelClassName)}>
          {labelFormatter(labelValue ?? null, tooltipPayload)}
        </div>
      );
    }

    if (!value) {
      return null;
    }

    return <div className={cn("font-medium", labelClassName)}>{value}</div>;
  }, [label, labelFormatter, tooltipPayload, hideLabel, labelClassName, config, labelKey]);

  if (!active || !tooltipPayload?.length) {
    return null;
  }

  const nestLabel = tooltipPayload.length === 1 && indicator !== "dot";

  return (
    <div
      ref={ref}
      className={cn(
        "grid min-w-[8rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl",
        className,
      )}
      {...divProps}
    >
      {!nestLabel ? tooltipLabel : null}
      <div className="grid gap-1.5">
        {tooltipPayload.map((item, index) => {
          const dataKey = item.dataKey;
          const itemKey =
            typeof dataKey === "string" || typeof dataKey === "number"
              ? String(dataKey)
              : typeof item.name === "string" || typeof item.name === "number"
              ? String(item.name)
              : `${index}`;
          const key = `${nameKey || item.name || item.dataKey || "value"}`;
          const itemConfig = getPayloadConfigFromPayload(config, item, key);
          const indicatorColor = color || item.payload?.fill || item.color;

          return (
            <div
              key={itemKey}
              className={cn(
                "flex w-full flex-wrap items-stretch gap-2 [&>svg]:h-2.5 [&>svg]:w-2.5 [&>svg]:text-muted-foreground",
                indicator === "dot" && "items-center",
              )}
            >
              {formatter && item?.value !== undefined && item.name ? (
                formatter(item.value as ValueType, item.name as NameType, item as ChartPayload, index, tooltipPayload)
              ) : (
                <>
                  {itemConfig?.icon ? (
                    <itemConfig.icon />
                  ) : (
                    !hideIndicator && (
                      <div
                        className={cn("shrink-0 rounded-[2px] border-[--color-border] bg-[--color-bg]", {
                          "h-2.5 w-2.5": indicator === "dot",
                          "w-1": indicator === "line",
                          "w-0 border-[1.5px] border-dashed bg-transparent": indicator === "dashed",
                          "my-0.5": nestLabel && indicator === "dashed",
                        })}
                        style={
                          {
                            "--color-bg": indicatorColor,
                            "--color-border": indicatorColor,
                          } as React.CSSProperties
                        }
                      />
                    )
                  )}
                  <div
                    className={cn(
                      "flex flex-1 justify-between leading-none",
                      nestLabel ? "items-end" : "items-center",
                    )}
                  >
                    <div className="grid gap-1.5">
                      {nestLabel ? tooltipLabel : null}
                      <span className="text-muted-foreground">{itemConfig?.label || item.name}</span>
                    </div>
                    {typeof item.value === "number" && (
                      <span className="font-mono font-medium tabular-nums text-foreground">
                        {item.value.toLocaleString()}
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
});
ChartTooltipContent.displayName = "ChartTooltip";

const ChartLegend = RechartsPrimitive.Legend;

type LegendPayload = {
  dataKey?: string | number;
  value?: string | number;
  color?: string;
};

const ChartLegendContent = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<"div"> & {
    payload?: LegendPayload[];
    verticalAlign?: "top" | "middle" | "bottom";
    hideIcon?: boolean;
    nameKey?: string;
  }
>(({ className, hideIcon = false, payload, verticalAlign = "bottom", nameKey }, ref) => {
  const { config } = useChart();

  if (!payload?.length) {
    return null;
  }

  return (
    <div
      ref={ref}
      className={cn("flex items-center justify-center gap-4", verticalAlign === "top" ? "pb-3" : "pt-3", className)}
    >
      {payload.map((item, index) => {
        const key = `${nameKey || item.dataKey || "value"}`;
        const itemConfig = getPayloadConfigFromPayload(config, item, key);
        const itemKey = String(item.value ?? item.dataKey ?? index);

        return (
          <div
            key={itemKey}
            className={cn("flex items-center gap-1.5 [&>svg]:h-3 [&>svg]:w-3 [&>svg]:text-muted-foreground")}
          >
            {itemConfig?.icon && !hideIcon ? (
              <itemConfig.icon />
            ) : (
              <div
                className="h-2 w-2 shrink-0 rounded-[2px]"
                style={{
                  backgroundColor: item.color,
                }}
              />
            )}
            {itemConfig?.label}
          </div>
        );
      })}
    </div>
  );
});
ChartLegendContent.displayName = "ChartLegend";

// Helper to extract item config from a payload.
function getPayloadConfigFromPayload(config: ChartConfig, payload: unknown, key: string) {
  if (typeof payload !== "object" || payload === null) {
    return undefined;
  }

  const payloadPayload =
    "payload" in payload && typeof payload.payload === "object" && payload.payload !== null
      ? payload.payload
      : undefined;

  let configLabelKey: string = key;

  if (key in payload && typeof payload[key as keyof typeof payload] === "string") {
    configLabelKey = payload[key as keyof typeof payload] as string;
  } else if (
    payloadPayload &&
    key in payloadPayload &&
    typeof payloadPayload[key as keyof typeof payloadPayload] === "string"
  ) {
    configLabelKey = payloadPayload[key as keyof typeof payloadPayload] as string;
  }

  return configLabelKey in config ? config[configLabelKey] : config[key as keyof typeof config];
}

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartStyle,
  buildChartStyleContent,
  isSafeChartColor,
};
