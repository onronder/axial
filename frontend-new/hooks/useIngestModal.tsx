"use client";

import { createContext, useContext, useState, ReactNode, useCallback } from "react";

type IngestModalTab = 'file' | 'url' | 'drive';

interface IngestModalContextType {
    isOpen: boolean;
    activeTab: IngestModalTab;
    openModal: (tab?: IngestModalTab) => void;
    closeModal: () => void;
}

const IngestModalContext = createContext<IngestModalContextType | undefined>(undefined);

export function IngestModalProvider({ children }: { children: ReactNode }) {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<IngestModalTab>('file');

    const openModal = useCallback((tab: IngestModalTab = 'file') => {
        setActiveTab(tab);
        setIsOpen(true);
    }, []);

    const closeModal = useCallback(() => {
        setIsOpen(false);
    }, []);

    return (
        <IngestModalContext.Provider value={{ isOpen, activeTab, openModal, closeModal }}>
            {children}
        </IngestModalContext.Provider>
    );
}

export function useIngestModal() {
    const context = useContext(IngestModalContext);
    if (context === undefined) {
        throw new Error("useIngestModal must be used within an IngestModalProvider");
    }
    return context;
}
