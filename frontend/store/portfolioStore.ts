import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Portfolio } from '@/types';

interface PortfolioState {
  activePortfolio: Portfolio | null;
  setActivePortfolio: (portfolio: Portfolio | null) => void;
}

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set) => ({
      activePortfolio: null,
      setActivePortfolio: (portfolio) => set({ activePortfolio: portfolio }),
    }),
    {
      name: 'tradesense-portfolio',
    }
  )
);
