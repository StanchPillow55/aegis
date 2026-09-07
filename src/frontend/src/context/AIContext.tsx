import React, { createContext, useContext, useState, ReactNode } from 'react';

interface AIContextState {
  currentPage: string;
  focusedElement: string | null;
  activeData: any | null;
}

interface AIContextType {
  state: AIContextState;
  setPage: (page: string) => void;
  setFocused: (element: string | null, data?: any) => void;
}

const AIContext = createContext<AIContextType | undefined>(undefined);

export function AIContextProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AIContextState>({
    currentPage: 'Dashboard',
    focusedElement: null,
    activeData: null
  });

  const setPage = (page: string) => {
    setState(prev => ({ ...prev, currentPage: page, focusedElement: null, activeData: null }));
  };

  const setFocused = (element: string | null, data?: any) => {
    setState(prev => ({ ...prev, focusedElement: element, activeData: data || null }));
  };

  return (
    <AIContext.Provider value={{ state, setPage, setFocused }}>
      {children}
    </AIContext.Provider>
  );
}

export function useAIContext() {
  const context = useContext(AIContext);
  if (context === undefined) {
    throw new Error('useAIContext must be used within an AIContextProvider');
  }
  return context;
}
