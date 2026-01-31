import { create } from 'zustand';
import type {
  EnvironmentInfo,
  EnvironmentState,
  EnvironmentConfig,
  EnvironmentType,
} from '@/types';
import {
  getEnvironmentInfo,
  getEnvironmentConfig,
  logEnvironmentChange,
  checkNetworkAvailability,
} from '@/utils/detectEnvironment';

interface EnvironmentStore extends EnvironmentState {
  // Actions
  detectEnvironment: () => EnvironmentInfo | null;
  updateConfig: (envType: EnvironmentType) => void;
  checkNetwork: () => Promise<boolean>;
  reset: () => void;
}

const initialState: EnvironmentState = {
  current: null,
  previous: null,
  config: null,
  transitionCount: 0,
};

export const useEnvironmentStore = create<EnvironmentStore>((set, get) => ({
  ...initialState,

  detectEnvironment: () => {
    const currentInfo = getEnvironmentInfo();

    if (currentInfo) {
      const previousInfo = get().current;

      // Log if environment changed
      if (previousInfo && previousInfo.type !== currentInfo.type) {
        logEnvironmentChange(previousInfo, currentInfo);

        set((state) => ({
          previous: state.current,
          transitionCount: state.transitionCount + 1,
        }));
      }

      // Update environment info and config
      const config = getEnvironmentConfig(currentInfo.type);

      set({
        current: currentInfo,
        config,
      });

      return currentInfo;
    }

    return null;
  },

  updateConfig: (envType: EnvironmentType) => {
    const config = getEnvironmentConfig(envType);
    set({ config });
  },

  checkNetwork: async () => {
    const isAvailable = await checkNetworkAvailability();
    return isAvailable;
  },

  reset: () => {
    set(initialState);
  },
}));
