import * as Sentry from "@sentry/nextjs";
import { NextResponse } from "next/server";

// API route to trigger a server-side Sentry error
export async function GET() {
    try {
        // Capture a manual error
        Sentry.captureException(new Error("Sentry Server-Side Test Error from API Route"));

        return NextResponse.json({
            success: true,
            message: "Test error sent to Sentry from server-side!"
        });
    } catch (error) {
        Sentry.captureException(error);
        return NextResponse.json({
            success: false,
            error: "Failed to send test error"
        }, { status: 500 });
    }
}
