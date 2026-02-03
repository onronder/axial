import type { Config } from "tailwindcss";

export default {
    darkMode: "class",
    content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
    prefix: "",
    theme: {
        container: { center: true, padding: "2rem", screens: { "2xl": "1400px" } },
        extend: {
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                display: ['Space Grotesk', 'system-ui', 'sans-serif']
            },
            colors: {
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
                secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
                destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
                success: { DEFAULT: "hsl(var(--success))", foreground: "hsl(var(--success-foreground))" },
                warning: { DEFAULT: "hsl(var(--warning))", foreground: "hsl(var(--warning-foreground))" },
                muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                    violet: "#8B5CF6",
                    cyan: "#06B6D4",
                },
                popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
                card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
                sidebar: {
                    DEFAULT: "hsl(var(--sidebar-background))",
                    foreground: "hsl(var(--sidebar-foreground))",
                    primary: "hsl(var(--sidebar-primary))",
                    "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
                    accent: "hsl(var(--sidebar-accent))",
                    "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
                    border: "hsl(var(--sidebar-border))",
                    ring: "hsl(var(--sidebar-ring))",
                    muted: "hsl(var(--sidebar-muted))"
                },
                brand: { blue: "#2563EB", violet: "#7C3AED" },
                axio: { navy: "#0F172A", slate: "#64748B", cloud: "#F8FAFC", border: "#E2E8F0" },
                dark: { bg: "#030712", surface: "#0F172A", text: "#F8FAFC", muted: "#94A3B8", border: "#1E293B" },
                void: {
                    black: "#030712",
                    glass: "rgba(255, 255, 255, 0.05)",
                }
            },
            backgroundImage: {
                "axio-gradient": "linear-gradient(to right, #8B5CF6, #06B6D4)",
                "axio-gradient-hover": "linear-gradient(to right, #7C3AED, #0891B2)",
                "glass-glow": "linear-gradient(135deg, rgba(139, 92, 246, 0.15), transparent, rgba(6, 182, 212, 0.15))",
                "void-gradient": "radial-gradient(circle at center, #1e1b4b 0%, #020617 100%)",
            },
            boxShadow: {
                brand: "0 4px 14px 0 rgba(139, 92, 246, 0.25)",
                "brand-lg": "0 10px 30px -5px rgba(139, 92, 246, 0.4)",
                glow: "0 0 20px rgba(139, 92, 246, 0.35)",
            },
            borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
            keyframes: {
                "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
                "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
                shimmer: {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" }
                },
                // Ghost Protocol animations
                shred: {
                    "0%": { transform: "translateY(0) rotateZ(0)", opacity: "1" },
                    "50%": { opacity: "1" },
                    "100%": { transform: "translateY(200px) rotateZ(15deg)", opacity: "0" }
                },
                "pulse-border": {
                    "0%, 100%": { borderColor: "hsl(var(--warning) / 0.5)", boxShadow: "0 0 20px hsl(var(--warning) / 0.3)" },
                    "50%": { borderColor: "hsl(var(--destructive) / 0.7)", boxShadow: "0 0 30px hsl(var(--destructive) / 0.4)" }
                },
                "matrix-scroll": {
                    "0%": { transform: "translateY(0)" },
                    "100%": { transform: "translateY(-10px)" }
                },
                "countdown-pulse": {
                    "0%, 100%": { opacity: "1" },
                    "50%": { opacity: "0.5" }
                },
                "glow-pulse": {
                    "0%, 100%": { boxShadow: "0 0 5px currentColor, 0 0 10px currentColor" },
                    "50%": { boxShadow: "0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor" }
                }
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                shimmer: "shimmer 2s linear infinite",
                // Ghost Protocol animations
                shred: "shred 1.5s ease-in forwards",
                "pulse-border": "pulse-border 2s ease-in-out infinite",
                "matrix-scroll": "matrix-scroll 0.5s linear infinite",
                "countdown-pulse": "countdown-pulse 1s linear infinite",
                "glow-pulse": "glow-pulse 2s ease-in-out infinite"
            },
        },
    },
    plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
} satisfies Config;
