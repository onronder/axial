import { type NextRequest, NextResponse } from 'next/server';
import { updateSession } from '@/lib/supabase/middleware';

export async function middleware(request: NextRequest) {
    try {
        const { user, response } = await updateSession(request);
        const path = request.nextUrl.pathname;

        if (!user && path.startsWith('/dashboard')) {
            const url = request.nextUrl.clone();
            url.pathname = '/login';
            url.searchParams.set('redirectTo', path + request.nextUrl.search);
            return NextResponse.redirect(url);
        }

        if (user && path === '/login') {
            const url = request.nextUrl.clone();
            url.pathname = '/dashboard';
            return NextResponse.redirect(url);
        }

        return response;
    } catch {
        // If auth check fails (Supabase outage, etc.), allow request through.
        // Client-side auth in dashboard/layout.tsx will handle the redirect.
        return NextResponse.next();
    }
}

export const config = {
    matcher: ['/dashboard/:path*', '/login'],
};
