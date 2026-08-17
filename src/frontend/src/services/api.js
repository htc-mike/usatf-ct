/**
 * api.js — Data access abstraction layer.
 *
 * All data fetching goes through this module.
 * To change the data source (e.g. switch from Google Sheets API to a DB API),
 * update VITE_API_BASE in your .env or change the fetch URLs here.
 */

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'
const STATIC   = import.meta.env.VITE_STATIC === 'true'
const CACHE_BUST = import.meta.env.VITE_GIT_SHA

async function fetchJSON(path) {
  const url = STATIC
    ? `${API_BASE}${path.split('?')[0]}.json${CACHE_BUST ? `?v=${CACHE_BUST.slice(0, 7)}` : ''}`
    : `${API_BASE}${path}`
  const res = await fetch(url, STATIC ? { cache: 'no-store' } : undefined)
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return res.json()
}

export const fetchEvents = () => fetchJSON('/events')
export const fetchResults = () => fetchJSON('/results')
export const fetchIndividual = () => fetchJSON('/individual')
export const fetchIndividualPoints = () => fetchJSON('/individual-points')
export const fetchTeamIndividual = () => fetchJSON('/team-individual')
export const fetchTeamEventDivisionGenderTotals = () =>
  fetchJSON('/team-event-division-gender-totals')
export const fetchTeamPoints = () => fetchJSON('/team-points')
export const fetchTeamTotals = () => fetchJSON('/team-totals')
export const fetchIndividualSeasonTotals = (limit = 50) =>
  fetchJSON(`/individual-season-totals?limit=${limit}`)
export const fetchMembers = () => fetchJSON('/members')
