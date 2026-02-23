/*
   walker/corpus-actions-session.js
   Session action wiring for walker corpus controls.
*/

'use strict';

/** @typedef {import('./corpus-contracts.js').WalkerApiErrorPayload} WalkerApiErrorPayload */
/** @typedef {import('./corpus-contracts.js').SessionIntegrityState} SessionIntegrityState */
/** @typedef {import('./corpus-contracts.js').SessionLockState} SessionLockState */
/** @typedef {import('./corpus-contracts.js').WalkerSessionListEntry} WalkerSessionListEntry */
/** @typedef {import('./corpus-contracts.js').WalkerSessionLoadPayload} WalkerSessionLoadPayload */
/** @typedef {import('./corpus-contracts.js').WalkerSessionSavePayload} WalkerSessionSavePayload */
/** @typedef {import('./corpus-contracts.js').SessionLockStatusResponse} SessionLockStatusResponse */

/**
 * Wire session save/load/takeover/release/repair controls.
 *
 * @param {{
 *   ctx: { setStatus: (msg: string) => void },
 *   getWalkerSessionLockHolderId: () => string,
 *   deriveSessionIntegrity: (payload: unknown) => SessionIntegrityState,
 *   setSessionIntegrity: (integrity: SessionIntegrityState) => void,
 *   applySessionLockFromLoadPayload: (payload: WalkerSessionLoadPayload, sessionId: string) => void,
 *   formatSessionLoadSummary: (payload: WalkerSessionLoadPayload) => string,
 *   loadSessionRunIntoPatch: (patch: string, runId: string) => void,
 *   loadWalkerSession: (args: {sessionId: string, lockHolderId: string, forceLock: boolean}) => Promise<WalkerSessionLoadPayload|WalkerApiErrorPayload>,
 *   saveWalkerSession: (body: Record<string, any>) => Promise<WalkerSessionSavePayload|WalkerApiErrorPayload>,
 *   refreshSessionList: (opts?: Record<string, any>) => Promise<void>,
 *   refreshWalkerStatsMicroState: () => Promise<void>,
 *   setSessionLockSignal: (lockState: SessionLockState) => void,
 *   getSessionLockState: () => SessionLockState,
 *   releaseSessionLock: (sessionId: string) => Promise<SessionLockStatusResponse>,
 *   stopSessionLockHeartbeat: () => void,
 *   getSessionEntry: (sessionId: string) => WalkerSessionListEntry | null
 * }} deps - Action dependencies.
 * @returns {void}
 */
export function initSessionActions(deps) {
  const summaryEl = document.getElementById('walker-session-summary');
  const labelInput = document.getElementById('walker-session-label');
  const saveBtn = document.getElementById('walker-save-session');
  const refreshBtn = document.getElementById('walker-refresh-sessions');
  const loadBtn = document.getElementById('walker-load-session');
  const repairBtn = document.getElementById('walker-repair-session');
  const takeoverBtn = document.getElementById('walker-takeover-session-lock');
  const releaseLockBtn = document.getElementById('walker-release-session-lock');
  const selectEl = document.getElementById('walker-session-select');
  const holderId = deps.getWalkerSessionLockHolderId();

  const setSessionIntegrityError = reason => {
    deps.setSessionIntegrity({
      status: 'error',
      reason,
      recoveredFromStale: false,
      patchA: null,
      patchB: null,
      topStatus: 'error',
      topReason: reason,
    });
  };

  const setSessionLockError = (reason, sessionId = null, lockPayload = null) => {
    deps.setSessionLockSignal({
      status: 'error',
      reason,
      sessionId,
      lock: lockPayload,
    });
  };

  /** @param {WalkerSessionLoadPayload} payload @param {string} sessionId */
  const applySessionLoadPayload = (payload, sessionId) => {
    deps.setSessionIntegrity(deps.deriveSessionIntegrity(payload));
    deps.applySessionLockFromLoadPayload(payload, payload.session_id || sessionId);
    if (summaryEl) {
      summaryEl.textContent = deps.formatSessionLoadSummary(payload);
    }
    if (payload.patch_a && payload.patch_a.loaded && typeof payload.patch_a.run_id === 'string') {
      deps.loadSessionRunIntoPatch('a', payload.patch_a.run_id);
    }
    if (payload.patch_b && payload.patch_b.loaded && typeof payload.patch_b.run_id === 'string') {
      deps.loadSessionRunIntoPatch('b', payload.patch_b.run_id);
    }
    deps.ctx.setStatus(`Session loaded: ${payload.session_id || sessionId}`);
  };

  const loadSessionById = async (sessionId, opts = {}) => {
    const forceLock = Boolean(opts.forceLock);
    const payload = await deps.loadWalkerSession({
      sessionId,
      lockHolderId: holderId,
      forceLock,
    });
    if (payload.error) {
      const error = new Error(payload.error);
      error.payload = payload;
      throw error;
    }
    applySessionLoadPayload(payload, sessionId);
    await deps.refreshWalkerStatsMicroState();
    return payload;
  };

  if (saveBtn && labelInput && summaryEl) {
    saveBtn.addEventListener('click', async () => {
      const rawLabel = labelInput.value;
      const normalizedLabel = rawLabel.trim();
      const body = {};
      if (normalizedLabel.length > 0) {
        body.label = normalizedLabel;
      }
      body.lock_holder_id = holderId;

      saveBtn.disabled = true;
      deps.ctx.setStatus('Saving walker session…');
      try {
        const payload = await deps.saveWalkerSession(body);
        if (payload.error) {
          summaryEl.textContent = `Save failed: ${payload.error}`;
          deps.ctx.setStatus(`Session save failed: ${payload.error}`);
          return;
        }
        const patchA = payload.patch_a || {};
        const patchB = payload.patch_b || {};
        summaryEl.textContent =
          `${payload.session_id || 'session'} saved · ` +
          `A ${patchA.status || 'unknown'} · B ${patchB.status || 'unknown'}`;
        deps.ctx.setStatus(`Session saved: ${payload.session_id || 'unknown-session'}`);
        if (normalizedLabel.length > 0) {
          labelInput.value = normalizedLabel;
        }
        await deps.refreshSessionList({ selectedId: payload.session_id || null });
      } catch (err) {
        summaryEl.textContent = `Save failed: ${err.message}`;
        deps.ctx.setStatus(`Session save failed: ${err.message}`);
      } finally {
        saveBtn.disabled = false;
      }
    });
  }

  if (refreshBtn && summaryEl) {
    refreshBtn.addEventListener('click', async () => {
      await deps.refreshSessionList();
      summaryEl.textContent = 'Session list refreshed.';
      deps.ctx.setStatus('Session list refreshed');
    });
  }

  if (loadBtn && selectEl && summaryEl) {
    loadBtn.addEventListener('click', async () => {
      const sessionId = selectEl.value;
      if (!sessionId) {
        deps.ctx.setStatus('Select a saved session first');
        return;
      }

      loadBtn.disabled = true;
      deps.ctx.setStatus(`Loading session ${sessionId}…`);
      try {
        await loadSessionById(sessionId, { forceLock: false });
      } catch (err) {
        summaryEl.textContent = `Load failed: ${err.message}`;
        setSessionIntegrityError(err.message);
        if (err && err.payload && err.payload.lock_status === 'locked') {
          deps.setSessionLockSignal({
            status: 'locked',
            reason: err.message,
            sessionId,
            lock: (err.payload.lock && typeof err.payload.lock === 'object') ? err.payload.lock : null,
          });
        } else {
          setSessionLockError(err.message, sessionId, null);
        }
        deps.ctx.setStatus(`Session load failed: ${err.message}`);
      } finally {
        loadBtn.disabled = false;
      }
    });
  }

  if (takeoverBtn && loadBtn && selectEl && summaryEl) {
    takeoverBtn.addEventListener('click', async () => {
      const sessionId = selectEl.value;
      if (!sessionId) {
        deps.ctx.setStatus('Select a saved session first');
        return;
      }
      takeoverBtn.disabled = true;
      loadBtn.disabled = true;
      deps.ctx.setStatus(`Taking over lock for session ${sessionId}…`);
      try {
        await loadSessionById(sessionId, { forceLock: true });
        deps.ctx.setStatus(`Lock taken over and session loaded: ${sessionId}`);
      } catch (err) {
        summaryEl.textContent = `Take over failed: ${err.message}`;
        setSessionIntegrityError(err.message);
        setSessionLockError(err.message, sessionId, null);
        deps.ctx.setStatus(`Session lock takeover failed: ${err.message}`);
      } finally {
        takeoverBtn.disabled = false;
        loadBtn.disabled = false;
      }
    });
  }

  if (releaseLockBtn && summaryEl) {
    releaseLockBtn.addEventListener('click', async () => {
      const selectedSessionId = selectEl && typeof selectEl.value === 'string' ? selectEl.value : '';
      const sessionId = selectedSessionId || deps.getSessionLockState().sessionId;
      if (!sessionId) {
        deps.ctx.setStatus('No session lock to release');
        return;
      }
      releaseLockBtn.disabled = true;
      deps.ctx.setStatus(`Releasing session lock for ${sessionId}…`);
      try {
        await deps.releaseSessionLock(sessionId);
        deps.stopSessionLockHeartbeat();
        deps.setSessionLockSignal({
          status: 'unlocked',
          reason: 'Session lock released.',
          sessionId: null,
          lock: null,
        });
        deps.ctx.setStatus(`Session lock released: ${sessionId}`);
      } catch (err) {
        summaryEl.textContent = `Release lock failed: ${err.message}`;
        setSessionLockError(err.message, sessionId, null);
        deps.ctx.setStatus(`Session lock release failed: ${err.message}`);
      } finally {
        releaseLockBtn.disabled = false;
      }
    });
  }

  if (repairBtn && loadBtn && selectEl && summaryEl) {
    repairBtn.addEventListener('click', async () => {
      const sessionId = selectEl.value;
      if (!sessionId) {
        deps.ctx.setStatus('Select a saved session first');
        return;
      }

      repairBtn.disabled = true;
      loadBtn.disabled = true;
      deps.ctx.setStatus(`Repairing session ${sessionId}…`);
      try {
        /* Ensure patch context matches selected session before writing repair revision. */
        await loadSessionById(sessionId, { forceLock: false });

        const selectedEntry = deps.getSessionEntry(sessionId);
        const body = {
          repair_from_session_id: sessionId,
          lock_holder_id: holderId,
        };
        if (
          selectedEntry
          && typeof selectedEntry.label === 'string'
          && selectedEntry.label.trim().length > 0
        ) {
          body.label = selectedEntry.label.trim();
        }

        const savePayload = await deps.saveWalkerSession(body);
        if (savePayload.error) {
          summaryEl.textContent = `Repair failed: ${savePayload.error}`;
          deps.ctx.setStatus(`Session repair failed: ${savePayload.error}`);
          return;
        }

        const repairedSessionId = (savePayload && typeof savePayload.session_id === 'string')
          ? savePayload.session_id
          : null;
        await deps.refreshSessionList({ selectedId: repairedSessionId });
        if (repairedSessionId) {
          await loadSessionById(repairedSessionId);
          deps.ctx.setStatus(`Session repaired: ${sessionId} -> ${repairedSessionId}`);
        } else {
          deps.ctx.setStatus(`Session repaired: ${sessionId}`);
        }
      } catch (err) {
        summaryEl.textContent = `Repair failed: ${err.message}`;
        setSessionIntegrityError(err.message);
        setSessionLockError(err.message, sessionId, null);
        deps.ctx.setStatus(`Session repair failed: ${err.message}`);
      } finally {
        repairBtn.disabled = false;
        loadBtn.disabled = false;
      }
    });
  }
}
