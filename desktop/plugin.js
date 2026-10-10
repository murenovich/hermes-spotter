// Spotter — desktop half (SPIKE, build card 1). Plain ESM, no JSX, no build step.
// Imports are limited to @hermes/plugin-sdk and react. Colours: --ui-* theme variables only.
// Backend: /api/plugins/hermes-spotter/{notes, notes/<id>/dismiss}.
import { Codicon, STATUSBAR_AREAS, host, useQuery, useQueryClient, useValue } from '@hermes/plugin-sdk'
import { createElement as h, useState } from 'react'

const PLUGIN_ID = 'hermes-spotter'
const POLL_MS = 5000
const KEY = [PLUGIN_ID, 'notes']

let ctx = null

const CSS = `
.sp { display:flex; flex-direction:column; height:100%; min-height:0; color:var(--ui-text-primary); font-size:13px; }
.sp-head { display:flex; align-items:center; gap:8px; padding:12px 14px 10px; }
.sp-head .t { font-weight:600; font-size:13.5px; }
.sp-badge { font-size:11px; font-weight:600; padding:1px 7px; border-radius:999px; color:var(--ui-accent);
  background:color-mix(in srgb, var(--ui-accent) 14%, transparent); }
.sp-seg { margin:0 14px 10px; display:grid; grid-template-columns:1fr 1fr; padding:2px; border-radius:7px; background:var(--ui-stroke-tertiary); }
.sp-seg button { all:unset; text-align:center; padding:4px 0; border-radius:5px; font-size:12px; color:var(--ui-text-secondary); cursor:pointer; }
.sp-seg button[aria-pressed="true"] { background:color-mix(in srgb, var(--ui-text-primary) 10%, transparent); color:var(--ui-text-primary); font-weight:500; }
.sp-list { flex:1; overflow:auto; padding:2px 12px 12px; display:flex; flex-direction:column; gap:10px; }
.sp-card { flex:none; position:relative; overflow:hidden; border:1px solid var(--ui-stroke-secondary); border-radius:10px;
  padding:12px; display:grid; grid-template-columns:30px 1fr; column-gap:10px; }
.sp-card::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--k); }
.sp-card.risk, .sp-row.risk { --k: var(--ui-yellow, var(--ui-accent)); } .sp-card.info, .sp-row.info { --k: var(--ui-accent); }
.sp-ic { width:28px; height:28px; border-radius:50%; display:grid; place-items:center; color:var(--k);
  background:color-mix(in srgb, var(--k) 15%, transparent); }
.sp-kind { font-size:10.5px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--k);
  display:flex; justify-content:space-between; align-items:center; }
.sp-kind .x { display:flex; gap:8px; align-items:center; color:var(--ui-text-tertiary); font-weight:400; letter-spacing:0; text-transform:none; font-size:11px; }
.sp-kind .x button { all:unset; cursor:pointer; color:var(--ui-text-tertiary); display:flex; }
.sp-h { font-size:13.5px; font-weight:600; line-height:1.35; margin:3px 0; }
.sp-b { color:var(--ui-text-secondary); font-size:12.5px; }
.sp-src { margin-top:6px; font-size:11.5px; color:var(--ui-text-tertiary); }
.sp-acts { grid-column:2; display:flex; gap:6px; margin-top:10px; }
.sp-btn { all:unset; cursor:pointer; font-size:12px; font-weight:500; padding:6px 10px; border-radius:6px; }
.sp-btn.o { border:1px solid var(--ui-stroke-secondary); }
.sp-group { font-size:11px; color:var(--ui-text-tertiary); text-transform:uppercase; letter-spacing:.06em; margin:6px 2px 0; }
.sp-row { display:flex; gap:9px; align-items:center; padding:7px 8px; font-size:12.5px; color:var(--ui-text-tertiary); }
.sp-row .dot { width:7px; height:7px; border-radius:50%; background:var(--k); opacity:.45; flex:none; }
.sp-row .tx { flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sp-row .tag { font-size:10.5px; border:1px solid var(--ui-stroke-secondary); border-radius:4px; padding:0 5px; }
.sp-empty { padding:28px 18px; text-align:center; color:var(--ui-text-tertiary); font-size:12.5px; line-height:1.5; }
.sp-foot { border-top:1px solid var(--ui-stroke-tertiary); padding:9px 14px; display:flex; justify-content:space-between; font-size:11.5px; color:var(--ui-text-tertiary); }
.sp-chip { display:inline-flex; align-items:center; gap:5px; }
`

function ago(t) {
  const s = Math.max(0, Date.now() / 1000 - t)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

function useNotes() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => ctx.rest('/notes'),
    refetchInterval: POLL_MS,
    refetchOnWindowFocus: true,
    retry: false
  })
}

function Card({ note, onDismiss }) {
  const risk = note.kind === 'risk'
  return h('div', { className: `sp-card ${note.kind}` },
    h('div', { className: 'sp-ic' }, h(Codicon, { name: risk ? 'warning' : 'lightbulb' })),
    h('div', null,
      h('div', { className: 'sp-kind' }, risk ? 'Heads up' : 'Worth knowing',
        h('span', { className: 'x' }, ago(note.t),
          h('button', { 'aria-label': 'Dismiss', title: 'Dismiss', onClick: () => onDismiss(note.id, 'dismissed') },
            h(Codicon, { name: 'close' })))),
      h('div', { className: 'sp-h' }, note.headline),
      h('div', { className: 'sp-b' }, note.detail),
      h('div', { className: 'sp-src' }, [note.profile, note.platform].filter(Boolean).join(' · '))),
    h('div', { className: 'sp-acts' },
      h('button', { className: 'sp-btn o', onClick: () => onDismiss(note.id, 'knew') }, 'I knew this')))
}

function Pane() {
  const qc = useQueryClient()
  const q = useNotes()
  const [scope, setScope] = useState('this')
  const session = useValue(host.state.activeSessionId) || null

  const dismiss = async (id, reason) => {
    try {
      await ctx.rest(`/notes/${id}/dismiss`, { method: 'POST', body: { reason } })
    } finally {
      qc.invalidateQueries({ queryKey: KEY })
    }
  }

  const all = (q.data && q.data.notes) || []
  const scoped = scope === 'this' && session ? all.filter(n => n.session === session) : all
  const open = scoped.filter(n => n.state === 'open')
  const done = scoped.filter(n => n.state !== 'open').slice(0, 8)
  const stats = (q.data && q.data.stats) || { turns: 0, triggered: 0 }

  let body
  if (q.isError) {
    body = h('div', { className: 'sp-empty' }, 'Spotter\u2019s backend isn\u2019t reachable yet. Restart Hermes Desktop once after installing.')
  } else if (!open.length && !done.length) {
    body = h('div', { className: 'sp-empty' }, 'Nothing to flag. Spotter only speaks up after long turns, and stays quiet when nothing stands out.')
  } else {
    body = [
      ...open.map(n => h(Card, { key: n.id, note: n, onDismiss: dismiss })),
      done.length ? h('div', { key: 'g', className: 'sp-group' }, 'Earlier') : null,
      ...done.map(n => h('div', { key: n.id, className: `sp-row ${n.kind}` },
        h('span', { className: 'dot' }), h('span', { className: 'tx' }, n.headline),
        h('span', { className: 'tag' }, n.state === 'knew' ? 'knew this' : 'dismissed')))
    ]
  }

  return h('div', { className: 'sp' },
    h('style', null, CSS),
    h('div', { className: 'sp-head' },
      h(Codicon, { name: 'lightbulb', style: { color: 'var(--ui-text-secondary)' } }),
      h('span', { className: 't' }, 'Spotter'),
      open.length ? h('span', { className: 'sp-badge' }, `${open.length} new`) : null),
    h('div', { className: 'sp-seg' },
      h('button', { 'aria-pressed': scope === 'this', onClick: () => setScope('this') }, 'This chat'),
      h('button', { 'aria-pressed': scope === 'all', onClick: () => setScope('all') }, 'All chats')),
    h('div', { className: 'sp-list' }, body),
    h('div', { className: 'sp-foot' },
      h('span', null, 'Spike: no model calls'),
      h('span', null, `This week: ${stats.turns} turns \u00b7 ${stats.triggered} long`)))
}

function Chip() {
  const q = useNotes()
  const n = ((q.data && q.data.notes) || []).filter(x => x.state === 'open').length
  if (!n) return null
  return h('span', { className: 'sp-chip', title: `Spotter: ${n} open note${n === 1 ? '' : 's'}` },
    h(Codicon, { name: 'lightbulb', style: { color: 'var(--ui-yellow, var(--ui-accent))' } }), String(n))
}

export default {
  id: PLUGIN_ID,
  name: 'Spotter',
  register(pluginCtx) {
    ctx = pluginCtx
    pluginCtx.registerMany([
      { id: 'pane', area: 'panes', title: 'Spotter', data: { placement: 'right', width: '340px' }, render: () => h(Pane, {}) },
      { id: 'chip', area: STATUSBAR_AREAS.right, order: 130, render: () => h(Chip, {}) }
    ])
  }
}
