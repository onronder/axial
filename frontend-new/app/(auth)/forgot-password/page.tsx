'use client'

import { useState } from 'react'
import { useFormStatus } from 'react-dom'
import Link from 'next/link'
import { resetPassword } from '@/app/auth/actions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowLeft } from 'lucide-react'

function SubmitButton() {
    const { pending } = useFormStatus()
    return (
        <Button className="w-full" type="submit" disabled={pending}>
            {pending ? "Sending..." : "Send Reset Link"}
        </Button>
    )
}

export default function ForgotPasswordPage() {
    const [error, setError] = useState('')
    const [msg, setMsg] = useState('')

    async function handleSubmit(formData: FormData) {
        setError('')
        setMsg('')
        const res = await resetPassword(formData)
        if (res?.error) setError(res.error)
        if (res?.success) setMsg(res.success)
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Reset Password</CardTitle>
                <CardDescription>
                    Enter your email address and we'll send you a link to reset your password.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <form action={handleSubmit} className="space-y-4">
                    <Input name="email" type="email" placeholder="name@example.com" required />

                    {error && <p className="text-sm text-red-500">{error}</p>}
                    {msg && <p className="text-sm text-green-500">{msg}</p>}

                    <SubmitButton />

                    <Button variant="link" className="w-full" asChild>
                        <Link href="/login" className="flex items-center gap-2">
                            <ArrowLeft className="h-4 w-4" />
                            Back to Login
                        </Link>
                    </Button>
                </form>
            </CardContent>
        </Card>
    )
}
