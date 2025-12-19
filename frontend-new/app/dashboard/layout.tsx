'use client'

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
    LayoutDashboard,
    MessageSquare,
    Settings,
    Menu,
    LogOut,
    PlusCircle,
    Database
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { IngestModal } from "@/components/ingest-modal"
import { signout } from '@/app/auth/actions'

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
    const [isIngestOpen, setIsIngestOpen] = useState(false)
    const pathname = usePathname()

    const navItems = [
        { href: "/dashboard", icon: MessageSquare, label: "Chat" },
        { href: "/dashboard/settings", icon: Settings, label: "Settings" },
    ]

    return (
        <div className="flex h-screen w-full bg-muted/40 font-sans antialiased">
            {/* Desktop Sidebar */}
            <aside className="hidden w-64 flex-col border-r bg-slate-900 text-slate-50 md:flex shadow-2xl z-20">
                <div className="flex h-16 items-center border-b border-slate-800 px-6 backdrop-blur-sm">
                    <Link href="/" className="flex items-center gap-2 font-bold text-lg tracking-tight">
                        <div className="rounded-lg bg-blue-600 p-1">
                            <LayoutDashboard className="h-5 w-5 text-white" />
                        </div>
                        <span className="bg-gradient-to-r from-blue-100 to-white bg-clip-text text-transparent">Axial Newton</span>
                    </Link>
                </div>
                <div className="flex-1 overflow-auto py-6 px-4">
                    <Button
                        className="w-full justify-start mb-8 bg-blue-600 hover:bg-blue-700 text-white shadow-lg transition-all hover:shadow-blue-500/25"
                        onClick={() => setIsIngestOpen(true)}
                    >
                        <PlusCircle className="mr-2 h-4 w-4" />
                        Add Data Source
                    </Button>
                    <nav className="grid items-start gap-1">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                                    pathname === item.href
                                        ? "bg-slate-800 text-blue-400 shadow-inner"
                                        : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-50"
                                )}
                            >
                                <item.icon className="h-4 w-4" />
                                {item.label}
                            </Link>
                        ))}
                    </nav>
                </div>
                <div className="mt-auto p-4 border-t border-slate-800 bg-slate-900/50">
                    <div className="mb-4 px-2 flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center">
                            <span className="text-xs font-bold">JD</span>
                        </div>
                        <div className="text-xs">
                            <p className="font-medium text-slate-200">John Doe</p>
                            <p className="text-slate-500">Pro Plan</p>
                        </div>
                    </div>
                    <form action={signout}>
                        <Button variant="ghost" className="w-full justify-start text-red-400 hover:text-red-300 hover:bg-red-950/30">
                            <LogOut className="mr-2 h-4 w-4" />
                            Logout
                        </Button>
                    </form>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex flex-1 flex-col overflow-hidden bg-slate-50 relative">
                {/* Decorative background gradient */}
                <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 via-transparent to-transparent pointer-events-none" />

                {/* Mobile Header */}
                <header className="flex h-16 items-center gap-4 border-b bg-white/80 px-6 backdrop-blur-md md:hidden sticky top-0 z-10 transition-all">
                    <Button variant="ghost" size="icon" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
                        <Menu className="h-6 w-6" />
                        <span className="sr-only">Toggle navigation menu</span>
                    </Button>
                    <div className="font-bold tracking-tight">Axial Newton</div>
                </header>

                {/* Mobile Menu Overlay */}
                {isMobileMenuOpen && (
                    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm md:hidden animate-in fade-in" onClick={() => setIsMobileMenuOpen(false)}>
                        <div className="fixed inset-y-0 left-0 w-3/4 max-w-sm bg-slate-900 p-6 shadow-2xl ring-1 ring-white/10" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center gap-2 font-bold text-lg tracking-tight mb-8 text-white">
                                <LayoutDashboard className="h-5 w-5 text-blue-500" />
                                <span>Axial Newton</span>
                            </div>
                            <div className="flex flex-col space-y-4">
                                <Button className="w-full justify-start bg-blue-600 hover:bg-blue-700" onClick={() => { setIsIngestOpen(true); setIsMobileMenuOpen(false); }}>
                                    <PlusCircle className="mr-2 h-4 w-4" />
                                    Add Data Source
                                </Button>
                                <nav className="flex flex-col gap-1">
                                    {navItems.map((item) => (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={cn(
                                                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-slate-400 transition-all hover:text-white",
                                                pathname === item.href ? "bg-slate-800 text-blue-400" : ""
                                            )}
                                            onClick={() => setIsMobileMenuOpen(false)}
                                        >
                                            <item.icon className="h-4 w-4" />
                                            {item.label}
                                        </Link>
                                    ))}
                                </nav>
                            </div>
                        </div>
                    </div>
                )}

                <main className="flex flex-1 flex-col p-4 lg:p-8 overflow-hidden relative z-0">
                    {children}
                </main>
            </div>

            <IngestModal isOpen={isIngestOpen} onClose={() => setIsIngestOpen(false)} />
        </div >
    )
}
