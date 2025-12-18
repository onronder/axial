'use client'

import { useState, useRef, useEffect } from "react"
import { Send, User, Bot, Paperclip, Sparkles, FileSearch, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card } from "@/components/ui/card"
import { authFetch } from "@/lib/api"


type Message = {
    role: 'user' | 'assistant'
    content: string
    sources?: string[]
}

import { KnowledgeBase } from "@/components/knowledge-base"
import { MessageSquare, Database } from "lucide-react"

export default function DashboardPage() {
    const [messages, setMessages] = useState<Message[]>([])
    const [inputValue, setInputValue] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [activeView, setActiveView] = useState<'chat' | 'knowledge'>('chat')
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages, activeView])

    const handleSendMessage = async (e?: React.FormEvent) => {
        e?.preventDefault()
        if (!inputValue.trim()) return

        const userMsg: Message = { role: 'user', content: inputValue }
        setMessages(prev => [...prev, userMsg])
        setInputValue("")
        setIsLoading(true)

        try {
            // Real API Call
            const response = await authFetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: inputValue,
                    model: 'gpt-4o',
                    history: []
                })
            })

            const botMsg: Message = {
                role: 'assistant',
                content: response.answer,
                sources: response.sources
            }

            setMessages(prev => [...prev, botMsg])
        } catch (error: any) {
            console.error("Failed to send message", error)
            const errorMsg: Message = { role: 'assistant', content: `Error: ${error.message || "Failed to get response"}` }
            setMessages(prev => [...prev, errorMsg])
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="flex flex-col h-full bg-slate-50/50">
            {/* View Toggle */}
            <div className="flex justify-center pt-4 pb-2">
                <div className="bg-slate-200/50 p-1 rounded-lg flex items-center space-x-1">
                    <button
                        onClick={() => setActiveView('chat')}
                        className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-xs font-medium transition-all ${activeView === 'chat'
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <MessageSquare className="h-3.5 w-3.5" />
                        <span>Chat</span>
                    </button>
                    <button
                        onClick={() => setActiveView('knowledge')}
                        className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-xs font-medium transition-all ${activeView === 'knowledge'
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <Database className="h-3.5 w-3.5" />
                        <span>Knowledge</span>
                    </button>
                </div>
            </div>

            {activeView === 'chat' ? (
                <>
                    {/* Messages Area */}
                    <div className="flex-1 overflow-y-auto min-h-0 space-y-4 p-4 pb-4 max-w-4xl mx-auto w-full">
                        {messages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-center space-y-8 animate-in fade-in duration-500">
                                {/* Hero Section */}
                                <div className="relative">
                                    <div className="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full" />
                                    <div className="relative bg-white p-6 rounded-2xl shadow-xl border border-blue-100">
                                        <Sparkles className="h-10 w-10 text-blue-600" />
                                    </div>
                                </div>
                                <div className="space-y-2 max-w-lg">
                                    <h2 className="text-3xl font-bold tracking-tight text-slate-900">Good Morning</h2>
                                    <p className="text-slate-500 text-lg">Ready to analyze your data? Select a starter query or upload a new document to begin.</p>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl px-4">
                                    <button
                                        onClick={() => setInputValue("Summarize the last uploaded file")}
                                        className="flex items-center gap-4 p-4 text-left bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-blue-200 hover:bg-blue-50/50 transition-all group"
                                    >
                                        <div className="p-3 bg-blue-100/50 text-blue-600 rounded-lg group-hover:bg-blue-100 group-hover:scale-110 transition-all">
                                            <FileSearch className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <div className="font-semibold text-slate-900">Summarize data</div>
                                            <div className="text-sm text-slate-500">Extract key insights from documents</div>
                                        </div>
                                    </button>
                                    <button
                                        onClick={() => setInputValue("What are the key risks?")}
                                        className="flex items-center gap-4 p-4 text-left bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:border-red-200 hover:bg-red-50/50 transition-all group"
                                    >
                                        <div className="p-3 bg-red-100/50 text-red-600 rounded-lg group-hover:bg-red-100 group-hover:scale-110 transition-all">
                                            <ShieldCheck className="h-5 w-5" />
                                        </div>
                                        <div>
                                            <div className="font-semibold text-slate-900">Analyze risks</div>
                                            <div className="text-sm text-slate-500">Identify potential issues</div>
                                        </div>
                                    </button>
                                </div>
                            </div>
                        ) : (
                            messages.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                                        }`}
                                >
                                    <Avatar className="h-8 w-8">
                                        <AvatarFallback className={msg.role === 'user' ? 'bg-slate-900 text-white' : 'bg-slate-200'}>
                                            {msg.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div
                                        className={`rounded-lg px-4 py-2 max-w-[80%] text-sm ${msg.role === 'user'
                                            ? 'bg-slate-900 text-white'
                                            : 'bg-white border text-slate-900 shadow-sm'
                                            }`}
                                    >
                                        <p className="whitespace-pre-wrap">{msg.content}</p>
                                        {msg.sources && (
                                            <div className="mt-2 text-xs opacity-70 border-t pt-1 border-slate-200">
                                                Sources: {msg.sources.join(", ")}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                        {isLoading && (
                            <div className="flex gap-3">
                                <Avatar className="h-8 w-8">
                                    <AvatarFallback className="bg-slate-200"><Bot className="h-4 w-4" /></AvatarFallback>
                                </Avatar>
                                <div className="bg-white border rounded-lg px-4 py-2 shadow-sm">
                                    <div className="flex space-x-1">
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="mt-auto p-4 bg-white border-t">
                        <form onSubmit={handleSendMessage} className="relative flex items-center max-w-3xl mx-auto">
                            <Button type="button" variant="ghost" size="icon" className="absolute left-2 text-slate-400 hover:text-slate-600">
                                <Paperclip className="h-5 w-5" />
                            </Button>
                            <Input
                                className="pl-12 pr-12 py-6 rounded-full shadow-sm border-slate-200 focus-visible:ring-slate-400"
                                placeholder="Message Axial..."
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                disabled={isLoading}
                            />
                            <Button
                                type="submit"
                                size="icon"
                                className="absolute right-2 h-8 w-8 rounded-full"
                                disabled={!inputValue.trim() || isLoading}
                            >
                                <Send className="h-4 w-4" />
                            </Button>
                        </form>
                        <div className="text-center mt-2 text-xs text-slate-400">
                            Axial can make mistakes. Check important info.
                        </div>
                    </div>
                </>
            ) : (
                <div className="flex-1 overflow-y-scroll min-h-0 p-8 max-w-5xl mx-auto w-full animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <KnowledgeBase />
                </div>
            )}
        </div>
    )
}
