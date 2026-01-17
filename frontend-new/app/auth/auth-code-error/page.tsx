'use client'

import Link from 'next/link'
import { AlertTriangle, ArrowLeft, RefreshCw, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

/**
 * Auth Code Error Page
 * 
 * Displayed when email authentication fails (e.g., expired or invalid magic link).
 * This page is excluded from middleware protection so users can see it without auth.
 */
export default function AuthCodeErrorPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 p-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center space-y-4">
                    <div className="mx-auto w-14 h-14 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                        <AlertTriangle className="w-7 h-7 text-amber-600 dark:text-amber-500" />
                    </div>
                    <CardTitle className="text-2xl">Authentication Error</CardTitle>
                    <CardDescription className="text-base">
                        We couldn&apos;t complete your sign-in. This usually happens when:
                    </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-6">
                    <ul className="space-y-3 text-sm text-muted-foreground">
                        <li className="flex items-start gap-2">
                            <span className="text-amber-500 mt-0.5">•</span>
                            <span>The magic link has expired (links are valid for 1 hour)</span>
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-amber-500 mt-0.5">•</span>
                            <span>The link was already used to sign in</span>
                        </li>
                        <li className="flex items-start gap-2">
                            <span className="text-amber-500 mt-0.5">•</span>
                            <span>The link was modified or incomplete</span>
                        </li>
                    </ul>
                    
                    <div className="flex flex-col gap-3 pt-2">
                        <Button asChild className="w-full">
                            <Link href="/login">
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Try Again
                            </Link>
                        </Button>
                        
                        <Button variant="outline" asChild className="w-full">
                            <Link href="/">
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back to Home
                            </Link>
                        </Button>
                    </div>
                    
                    <div className="text-center text-sm text-muted-foreground border-t pt-4">
                        <p className="flex items-center justify-center gap-2">
                            <Mail className="w-4 h-4" />
                            Need help?{' '}
                            <a 
                                href="mailto:support@axial.ai" 
                                className="text-primary hover:underline"
                            >
                                Contact support
                            </a>
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
