import { create } from "zustand";
interface UiState {
  tripFormOpen: boolean;
  setTripFormOpen: (open: boolean) => void;
}
export const useUiStore = create<UiState>((set) => ({
  tripFormOpen: false,
  setTripFormOpen: (tripFormOpen) => set({ tripFormOpen }),
}));
