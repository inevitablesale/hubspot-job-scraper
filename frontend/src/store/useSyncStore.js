import { create } from 'zustand'
import { getSchema, getState, getResults, getVersion, fetchSettings } from '../api/crawler'

const initial = {
  schema: null,
  state: null,
  results: { jobs: [], coverage: [] },
  version: null,
  settings: null,
  loading: false,
  error: null,
}

export const useSyncStore = create((set, get) => ({
  ...initial,
  async syncSchema() {
    try {
      const data = await getSchema()
      set({ schema: data, error: null })
    } catch (err) {
      set({ error: err })
    }
  },
  async syncState() {
    try {
      const data = await getState()
      set({ state: data, error: null })
    } catch (err) {
      set({ error: err })
    }
  },
  async syncResults() {
    try {
      const res = await getResults()
      set({ results: res, error: null })
    } catch (err) {
      set({ error: err })
    }
  },
  async syncSettings() {
    try {
      const data = await fetchSettings()
      set({ settings: data, error: null })
    } catch (err) {
      set({ error: err })
    }
  },
  async syncVersion() {
    try {
      const data = await getVersion()
      set({ version: data, error: null })
    } catch (err) {
      set({ error: err })
    }
  },
  async bootstrap() {
    const { syncSchema, syncState, syncResults, syncVersion, syncSettings } = get()
    set({ loading: true })
    try {
      await Promise.all([syncSchema(), syncState(), syncResults(), syncVersion(), syncSettings()])
    } finally {
      set({ loading: false })
    }
  },
}))
