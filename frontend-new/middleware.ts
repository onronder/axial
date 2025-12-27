import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
    let response = NextResponse.next({
        request: { headers: request.headers },
    })

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) => {
                        request.cookies.set(name, value)
                        response = NextResponse.next({
                            request: { headers: request.headers },
                        })
                        response.cookies.set(name, value, options)
                    })
                },
            },
        }
    )

    // Refresh session if expired
    const { data: { user } } = await supabase.auth.getUser()

    // 1. Audit: Avoid intercepting Server Actions (POST requests) unless necessary
    // If this is a POST request (likely a Server Action), let it pass through.
    // The Action itself should handle auth/validation if needed.
    if (request.method === 'POST') {
        return response
    }

    // Protected Routes Logic
    const path = request.nextUrl.pathname
    const isProtectedRoute = path.startsWith('/dashboard')
    const isAuthRoute = path.startsWith('/login') || path.startsWith('/auth')

    // Redirect unauthenticated users trying to access protected routes
    if (isProtectedRoute && !user) {
        return NextResponse.redirect(new URL('/auth/login', request.url))
    }

    // Redirect authenticated users away from login page
    if (isAuthRoute && user) {
        return NextResponse.redirect(new URL('/dashboard', request.url))
    }

    return response
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
