// Steuert die Spotify-App per Web-API (Spotify Connect). Erfordert Premium + eigene Client-ID.
const SC = (() => {
  const CLIENT_ID = 'DEINE_CLIENT_ID_HIER';   // <- hier deine Client-ID eintragen
  const BASE = location.origin + location.pathname;
  const K = 'sc_tok';
  let tok = null, dev = null;
  try { tok = JSON.parse(localStorage.getItem(K) || 'null'); } catch (e) {}
  const b64 = a => btoa(String.fromCharCode(...new Uint8Array(a))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  async function login() {
    const v = b64(crypto.getRandomValues(new Uint8Array(48)));
    sessionStorage.setItem('sc_v', v); sessionStorage.setItem('sc_ret', location.href);
    const ch = b64(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(v)));
    location.href = 'https://accounts.spotify.com/authorize?' + new URLSearchParams({
      client_id: CLIENT_ID, response_type: 'code', redirect_uri: BASE,
      scope: 'user-modify-playback-state user-read-playback-state',
      code_challenge_method: 'S256', code_challenge: ch });
  }
  async function token(body) {
    const r = await fetch('https://accounts.spotify.com/api/token', { method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ client_id: CLIENT_ID, ...body }) });
    if (!r.ok) throw new Error('token');
    const j = await r.json();
    tok = { a: j.access_token, r: j.refresh_token || (tok && tok.r), e: Date.now() + j.expires_in * 1000 - 60000 };
    localStorage.setItem(K, JSON.stringify(tok));
  }
  async function init() {   // nach der Rückkehr von Spotify aufrufen
    const c = new URLSearchParams(location.search).get('code');
    if (c) {
      try { await token({ grant_type: 'authorization_code', code: c, redirect_uri: BASE,
        code_verifier: sessionStorage.getItem('sc_v') }); } catch (e) {}
      history.replaceState(null, '', sessionStorage.getItem('sc_ret') || BASE);
    }
  }
  async function api(method, path, body) {
    if (Date.now() > tok.e) await token({ grant_type: 'refresh_token', refresh_token: tok.r });
    return fetch('https://api.spotify.com/v1' + path, { method,
      headers: { Authorization: 'Bearer ' + tok.a, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined });
  }
  async function play(id) {
    const body = { uris: ['spotify:track:' + id], position_ms: 0 };
    let r = await api('PUT', '/me/player/play' + (dev ? '?device_id=' + dev : ''), body);
    if (r.status === 404) {   // kein aktives Gerät: erstes verfügbares nehmen
      const d = (await (await api('GET', '/me/player/devices')).json()).devices || [];
      if (!d.length) return 'nodev';
      dev = (d.find(x => x.is_active) || d[0]).id;
      r = await api('PUT', '/me/player/play?device_id=' + dev, body);
    }
    return r.ok ? 'ok' : 'err' + r.status;
  }
  async function pause() { try { await api('PUT', '/me/player/pause'); } catch (e) {} }
  async function toggle() {   // gibt zurück, ob jetzt gespielt wird
    const r = await api('GET', '/me/player');
    const j = r.status === 200 ? await r.json() : null;
    if (j && j.is_playing) { await api('PUT', '/me/player/pause'); return false; }
    await api('PUT', '/me/player/play'); return true;
  }
  return { init, login, play, pause, toggle,
    configured: () => !CLIENT_ID.startsWith('DEINE'), on: () => !!tok && !CLIENT_ID.startsWith('DEINE') };
})();
