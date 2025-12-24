import type { Config } from "tailwindcss";
export default {
    darkMode: "class",
    content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
    prefix: "",
    theme: {
        container: { center: true, padding: "2rem", screens: { "2xl": "1400px" } },
        extend: {
            fontFamily: { sans: ['Inter', 'system-ui', 'sans-serif'], display: ['Space Grotesk', 'system-ui', 'sans-serif'] },
            colors: {
                border: "hsl(var(--border))", input: "hsl(var(--input))", ring: "hsl(var(--ring))", background: "hsl(var(--background))", foreground: "hsl(var(--foreground))",
                primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
                secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
                destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
                success: { DEFAULT: "hsl(var(--success))", foreground: "hsl(var(--success-foreground))" },
                warning: { DEFAULT: "hsl(var(--warning))", foreground: "hsl(var(--warning-foreground))" },
                muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
                accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
                popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
                card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
                sidebar: { DEFAULT: "hsl(var(--sidebar-background))", foreground: "hsl(var(--sidebar-foreground))", primary: "hsl(var(--sidebar-primary))", "primary-foreground": "hsl(var(--sidebar-primary-foreground))", accent: "hsl(var(--sidebar-accent))", "accent-foreground": "hsl(var(--sidebar-accent-foreground))", border: "hsl(var(--sidebar-border))", ring: "hsl(var(--sidebar-ring))", muted: "hsl(var(--sidebar-muted))" },
                brand: { blue: "#2563EB", violet: "#7C3AED" },
                axio: { navy: "#0F172A", slate: "#64748B", cloud: "#F8FAFC", border: "#E2E8F0" },
                dark: { bg: "#0B1120", surface: "#1E293B", text: "#F8FAFC", muted: "#94A3B8", border: "#334155" },
            },
            backgroundImage: { "axio-gradient": "linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)", "axio-gradient-hover": "linear-gradient(135deg, #1d4ed8 0%, #6d28d9 100%)" },
            boxShadow: { brand: "0 4px 14px 0 rgba(37, 99, 235, 0.25)", "brand-lg": "0 10px 25px -5px rgba(37, 99, 235, 0.3)" },
            borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
            keyframes: { "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } }, "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } } },
            animation: { "accordion-down": "accordion-down 0.2s ease-out", "accordion-up": "accordion-up 0.2s ease-out" },
        },
    },
    plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
} satisfies Config;
