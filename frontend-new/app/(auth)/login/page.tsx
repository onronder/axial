import { login, signup } from '@/app/auth/actions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function LoginPage() {
    return (
        <div className="relative w-full h-full min-h-screen flex items-center justify-center bg-slate-50 overflow-hidden">
            {/* Background Pattern */}
            <div className="absolute inset-0 z-0 opacity-[0.4] [mask-image:radial-gradient(#fff,transparent,transparent)]"
                style={{ backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)', backgroundSize: '24px 24px' }}>
            </div>

            <div className="relative z-10 w-full max-w-sm mx-auto p-8 bg-white/80 backdrop-blur-xl border border-white/20 rounded-2xl shadow-2xl ring-1 ring-slate-900/5">
                <div className="text-center space-y-2 mb-8">
                    <div className="flex justify-center mb-4">
                        <div className="h-12 w-12 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/20">
                            {/* Simple Logo Placeholder */}
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-white"><rect width="7" height="9" x="3" y="3" rx="1" /><rect width="7" height="5" x="14" y="3" rx="1" /><rect width="7" height="9" x="14" y="12" rx="1" /><rect width="7" height="5" x="3" y="16" rx="1" /></svg>
                        </div>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">Welcome Back</h1>
                    <p className="text-sm text-slate-500">Sign in to your Axial Newton account</p>
                </div>

                <form className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input id="email" name="email" type="email" placeholder="m@example.com" required />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input id="password" name="password" type="password" required />
                    </div>

                    <div className="flex flex-col gap-3 pt-2">
                        <Button formAction={async (formData) => {
                            'use server'
                            await login(formData)
                        }} className="w-full">Sign In</Button>
                        <Button formAction={async (formData) => {
                            'use server'
                            await signup(formData)
                        }} variant="outline" className="w-full">Sign Up</Button>
                    </div>
                </form>
            </div>
        </div>
    )
}
