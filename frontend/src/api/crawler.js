import client from './client'

export const getStatus = () => client.get('/status').then((r) => r.data)
export const runCrawl = () => client.post('/run').then((r) => r.data)
export const runMaps = (payload = {}) => client.post('/run/maps', payload).then((r) => r.data)
export const stopCrawl = () => client.post('/stop').then((r) => r.data)
export const getLogs = () => client.get('/logs').then((r) => r.data)
export const getHealth = () => client.get('/health').then((r) => r.data)
export const getResults = () => client.get('/results').then((r) => r.data)
export const fetchDomains = () => client.get('/domains').then((r) => r.data)
export const fetchDomainChanges = () => client.get('/domains/changes').then((r) => r.data)
export const deleteDomain = (domain) => client.delete(`/domains/${domain}`).then((r) => r.data)
