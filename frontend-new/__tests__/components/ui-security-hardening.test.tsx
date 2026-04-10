import { describe, expect, it } from "vitest";

import { buildChartStyleContent, isSafeChartColor } from "@/components/ui/chart";
import { buildSidebarStateCookieValue } from "@/components/ui/sidebar";

describe("UI security hardening helpers", () => {
  describe("buildSidebarStateCookieValue", () => {
    it("adds SameSite=Lax without Secure on http", () => {
      expect(buildSidebarStateCookieValue(true, "http:")).toBe(
        "sidebar:state=true; path=/; max-age=604800; samesite=lax",
      );
    });

    it("adds SameSite=Lax and Secure on https", () => {
      expect(buildSidebarStateCookieValue(false, "https:")).toBe(
        "sidebar:state=false; path=/; max-age=604800; samesite=lax; secure",
      );
    });
  });

  describe("chart color sanitization", () => {
    it("accepts supported CSS color formats", () => {
      expect(isSafeChartColor("#22c55e")).toBe(true);
      expect(isSafeChartColor("rgba(34, 197, 94, 0.5)")).toBe(true);
      expect(isSafeChartColor("hsl(var(--chart-1))")).toBe(true);
      expect(isSafeChartColor("var(--color-green-500, #22c55e)")).toBe(true);
      expect(isSafeChartColor("white")).toBe(true);
    });

    it("rejects unsafe style-breaking values", () => {
      expect(isSafeChartColor("url(javascript:alert(1))")).toBe(false);
      expect(isSafeChartColor("#22c55e; background:red")).toBe(false);
      expect(isSafeChartColor("</style><script>alert(1)</script>")).toBe(false);
    });

    it("omits unsafe colors from generated chart CSS", () => {
      const css = buildChartStyleContent("chart-safe", {
        safe: { label: "Safe", color: "var(--color-green-500, #22c55e)" },
        unsafe: { label: "Unsafe", color: "#22c55e; background:red" },
      });

      expect(css).toContain("--color-safe: var(--color-green-500, #22c55e);");
      expect(css).not.toContain("--color-unsafe:");
      expect(css).not.toContain("background:red");
    });
  });
});
