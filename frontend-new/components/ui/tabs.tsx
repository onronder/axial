import * as React from "react"
import { cn } from "@/lib/utils"

const TabsContext = React.createContext<{
    value: string
    onValueChange: (value: string) => void
} | null>(null)

export function Tabs({
    defaultValue,
    value,
    onValueChange,
    children,
    className,
}: {
    defaultValue?: string
    value?: string
    onValueChange?: (value: string) => void
    children: React.ReactNode
    className?: string
}) {
    const [activeValue, setActiveValue] = React.useState(defaultValue || "")

    const handleValueChange = (newValue: string) => {
        setActiveValue(newValue)
        onValueChange?.(newValue)
    }

    const currentVal = value !== undefined ? value : activeValue

    return (
        <TabsContext.Provider value={{ value: currentVal, onValueChange: handleValueChange }}>
            <div className={cn("", className)}>{children}</div>
        </TabsContext.Provider>
    )
}

export function TabsList({ className, children }: { className?: string; children: React.ReactNode }) {
    return (
        <div
            className={cn(
                "inline-flex h-9 items-center justify-center rounded-lg bg-slate-100 p-1 text-slate-500",
                className
            )}
        >
            {children}
        </div>
    )
}

export function TabsTrigger({
    value,
    className,
    children,
}: {
    value: string
    className?: string
    children: React.ReactNode
}) {
    const context = React.useContext(TabsContext)
    if (!context) throw new Error("TabsTrigger must be used within Tabs")

    const isActive = context.value === value

    return (
        <button
            onClick={() => context.onValueChange(value)}
            className={cn(
                "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
                isActive
                    ? "bg-white text-slate-950 shadow-sm"
                    : "hover:bg-slate-200/50 hover:text-slate-900",
                className
            )}
        >
            {children}
        </button>
    )
}

export function TabsContent({
    value,
    className,
    children,
}: {
    value: string
    className?: string
    children: React.ReactNode
}) {
    const context = React.useContext(TabsContext)
    if (!context) throw new Error("TabsContent must be used within Tabs")

    if (context.value !== value) return null

    return (
        <div
            className={cn(
                "mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2",
                className
            )}
        >
            {children}
        </div>
    )
}
