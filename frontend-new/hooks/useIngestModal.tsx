"use client";

import {
    createContext,
    useContext,
    useState,
    ReactNode,
    useCallback,
    useMemo,
} from "react";

type IngestModalTab = 'file' | 'url';

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

    const value = useMemo(
        () => ({ isOpen, activeTab, openModal, closeModal }),
        [activeTab, closeModal, isOpen, openModal]
    );

    return (
        <IngestModalContext.Provider value={value}>
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
