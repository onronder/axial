# AxioHub UI Refactoring & Design System

**Version:** 1.0  
**Date:** January 2026  
**Theme:** "Void & Glass" (Cinematic, Cyberpunk, Premium)

## 1. Design Philosophy
The new UI for the AxioHub application aims to mirror the premium, cinematic aesthetic of the marketing site (`axiohub.io`). The core principles are:
- **Void Backgrounds**: Deep, rich blacks (`#030712`) rather than generic grays.
- **Glassmorphism**: Translucent surfaces with blur effects for cards, sidebars, and overlays.
- **Neon Accents**: High-contrast Electric Violet (`#8B5CF6`) and Neon Cyan (`#06B6D4`) gradients.
- **Micro-Interactions**: Subtle glows, border shines, and smooth transitions.

## 2. Design Tokens

### Colors
| Token | Value | Description |
|-------|-------|-------------|
| `background` | `#030712` | Deep void black |
| `card` | `rgba(255,255,255, 0.03)` | Ultra-subtle glass |
| `primary` | `#8B5CF6` (Violet) | Primary action color |
| `secondary` | `#06B6D4` (Cyan) | Secondary/Accent color |
| `border` | `rgba(255,255,255, 0.1)` | Subtle dividers |
| `text-muted` | `#94A3B8` | Secondary text |

### Gradients
- **Brand Gradient**: `linear-gradient(to right, #8B5CF6, #06B6D4)`
- **Glass Gradient**: `linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))`
- **Glow Effect**: `box-shadow: 0 0 20px rgba(139, 92, 246, 0.3)`

### Typography
- **Headings**: `Space Grotesk` (Technical, Modern)
- **Body**: `Inter` (Clean, Legible)

## 3. Component Specifications

### 3.1 Sidebar
- **Style**: Floating, Glassmorphic.
- **Behavior**: Detached from the left edge on large screens, translucent background.
- **Active State**: Violet glow indicator, gradient text for active item.

### 3.2 Cards
- **Background**: `.glass-card` (Blur 24px, Border 1px solid white/10%).
- **Hover**: Subtle lift (`-translate-y-1`), border brightness increase.

### 3.3 Buttons
- **Primary**: Brand Gradient background, white text, subtle shadow glow.
- **Secondary/Ghost**: Transparent with thin white/20% border, hover fills with white/10%.
- **Destructive**: Red glow, transparent background until hover.

### 3.4 Inputs
- **Style**: Dark glass background (`bg-white/5`), border `white/10`.
- **Focus**: Border transitions to Violet (`#8B5CF6`) with a subtle ring glow.

### 3.5 Tables
- **Header**: Transparent, uppercase, tracking-wider, text-muted.
- **Rows**: Minimal borders, hover highlights the entire row with `bg-white/5`.
- **Actions**: Floating action buttons that appear on hover.

## 4. Implementation Strategy

### Phase 1: Foundation (Current)
1.  **Tailwind Config**: Add `void`, `glow` colors, animations.
2.  **Globals**: Set root CSS variables for dark mode default.
3.  **Core Components**: Rewrite `Button`, `Input`, `Card`.

### Phase 2: Layout & Data
1.  **Sidebar**: Refactor to support "Floating" variant.
2.  **Tables**: Remove default stripe/borders, apply minimal glass style.
3.  **Modals**: Use `backdrop-blur-xl` for overlays.

### Phase 3: Polish
1.  **Animations**: Add entry animations for page transitions.
2.  **Empty States**: Add graphical/illustration empty states.

## 5. CSS Utility Classes
New utility classes added to `globals.css`:
- `.glass-card`: Standard card container.
- `.input-glass`: Standard input field style.
- `.text-gradient`: Gradient text clip.
- `.border-glow`: Animated border effect.





global.css

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
@import "tailwindcss";
@config "../tailwind.config.ts";

@layer base {
  :root {
    /* Default to Dark Mode "Void" Theme directly in root */
    --background: 224 71% 4%; /* #030712 */
    --foreground: 210 40% 98%;

    --card: 224 71% 4%;
    --card-foreground: 210 40% 98%;

    --popover: 224 71% 4%;
    --popover-foreground: 210 40% 98%;

    --primary: 263 83% 58%; /* #8B5CF6 Violet */
    --primary-foreground: 0 0% 100%;

    --secondary: 189 94% 43%; /* #06B6D4 Cyan */
    --secondary-foreground: 0 0% 100%;

    --muted: 217 33% 17%;
    --muted-foreground: 215 25% 63%;

    --accent: 263 83% 58%;
    --accent-foreground: 0 0% 100%;

    --destructive: 0 62% 50%;
    --destructive-foreground: 0 0% 100%;
    
    --success: 142 76% 36%;
    --success-foreground: 0 0% 100%;
    
    --warning: 38 92% 50%;
    --warning-foreground: 0 0% 100%;

    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 263 83% 58%;

    --radius: 0.75rem;

    /* Sidebar - Glassy Dark */
    --sidebar-background: 224 71% 4%;
    --sidebar-foreground: 210 40% 98%;
    --sidebar-primary: 263 83% 58%;
    --sidebar-primary-foreground: 0 0% 100%;
    --sidebar-accent: 217 33% 17%;
    --sidebar-accent-foreground: 210 40% 98%;
    --sidebar-border: 217 33% 17%;
    --sidebar-ring: 263 83% 58%;
    --sidebar-muted: 215 25% 63%;

    --sidebar-width: 16rem;
    --sidebar-width-icon: 3rem;
  }

  /* Keeping .dark for compatibility if manually toggled, but mapped same as root */
  .dark {
    --background: 224 71% 4%;
    --foreground: 210 40% 98%;
    --card: 224 71% 4%;
    --card-foreground: 210 40% 98%;
    --popover: 224 71% 4%;
    --popover-foreground: 210 40% 98%;
    --primary: 263 83% 58%;
    --primary-foreground: 0 0% 100%;
    --secondary: 189 94% 43%;
    --secondary-foreground: 0 0% 100%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 25% 63%;
    --accent: 263 83% 58%;
    --accent-foreground: 0 0% 100%;
    --destructive: 0 62% 50%;
    --destructive-foreground: 0 0% 100%;
    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 263 83% 58%;

    --sidebar-background: 224 71% 4%;
    --sidebar-foreground: 210 40% 98%;
    --sidebar-primary: 263 83% 58%;
    --sidebar-primary-foreground: 0 0% 100%;
    --sidebar-accent: 217 33% 17%;
    --sidebar-accent-foreground: 210 40% 98%;
    --sidebar-border: 217 33% 17%;
    --sidebar-ring: 263 83% 58%;
    --sidebar-muted: 215 25% 63%;
  }
}

@layer base {
  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground antialiased;
    background-image: radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.05), transparent 40%);
    background-attachment: fixed;
  }
}

@layer utilities {

  /* Glass Effects */
  .glass-card {
    @apply bg-white/5 backdrop-blur-md border border-white/10 shadow-xl;
  }

  .glass-panel {
    @apply bg-background/80 backdrop-blur-xl border-l border-white/5;
  }

  /* Text Effects */
  .text-gradient {
    @apply bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent;
  }
  
  .text-gradient-hover {
    @apply hover:bg-gradient-to-r hover:from-purple-400 hover:to-cyan-400 hover:bg-clip-text hover:text-transparent transition-all;
  }

  /* Form Elements */
  .input-glass {
    @apply bg-white/5 border-white/10 text-foreground placeholder:text-muted-foreground focus-visible:ring-purple-500/50 focus-visible:border-purple-500/50 transition-all duration-200;
  }

  /* Animations */
  .animate-in {
    animation: fadeIn 0.5s ease-out forwards;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
}




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
                    black: "#030712", // The core void color
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
                "glow": "0 0 20px rgba(139, 92, 246, 0.35)",
            },
            borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
            keyframes: { 
                "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } }, 
                "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
                "shimmer": {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" }
                }
            },
            animation: { 
                "accordion-down": "accordion-down 0.2s ease-out", 
                "accordion-up": "accordion-up 0.2s ease-out",
                "shimmer": "shimmer 2s linear infinite"
            },
        },
    },
    plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
} satisfies Config;



badge.tsx

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80 shadow-[0_0_10px_-3px_rgba(139,92,246,0.6)]",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground border-white/20 bg-white/5",
        ai: "border-transparent bg-axio-gradient text-white shadow-brand",
        success: "border-transparent bg-green-500/15 text-green-400 border border-green-500/20",
        warning: "border-transparent bg-yellow-500/15 text-yellow-400 border border-yellow-500/20",
        glass: "border-transparent bg-white/10 backdrop-blur-md text-foreground border border-white/10",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };



button.tsx

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 active:scale-95",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-lg shadow-primary/20 hover:bg-primary/90 hover:shadow-primary/30",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-lg shadow-destructive/20",
        outline: "border border-input bg-background/50 backdrop-blur-sm hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-white/5 backdrop-blur-sm border border-white/10 text-foreground hover:bg-white/10 hover:border-white/20",
        ghost: "hover:bg-white/5 hover:text-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        gradient: "bg-axio-gradient text-white shadow-brand hover:bg-axio-gradient-hover hover:shadow-brand-lg border-0",
        glass: "bg-white/5 backdrop-blur-md border border-white/10 shadow-lg hover:bg-white/10 text-foreground",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };




card.tsx

import * as React from "react";

import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("rounded-xl border bg-card text-card-foreground shadow-sm glass-card", className)} {...props} />
));
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("text-2xl font-semibold leading-none tracking-tight font-display", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />,
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };



input.tsx

import * as React from "react";

import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-lg border border-input bg-background/50 backdrop-blur-sm px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm transition-all duration-200 hover:border-primary/50 focus:bg-background/80",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };



separator.tsx

import * as React from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";

import { cn } from "@/lib/utils";

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(({ className, orientation = "horizontal", decorative = true, ...props }, ref) => (
  <SeparatorPrimitive.Root
    ref={ref}
    decorative={decorative}
    orientation={orientation}
    className={cn(
      "shrink-0 bg-border/50 backdrop-blur-sm",
      orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
      className
    )}
    {...props}
  />
));
Separator.displayName = SeparatorPrimitive.Root.displayName;

export { Separator };

