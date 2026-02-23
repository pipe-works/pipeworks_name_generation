/*
   walker/corpus-actions-cache.js
   Reach-cache action wiring for walker corpus panel controls.
*/

'use strict';

/** @typedef {import('./corpus-contracts.js').WalkerApiErrorPayload} WalkerApiErrorPayload */
/** @typedef {import('./corpus-contracts.js').WalkerRebuildReachCacheResponse} WalkerRebuildReachCacheResponse */
/** @typedef {import('./corpus-contracts.js').WalkerCorpusContext} WalkerCorpusContext */

/**
 * Wire Patch A/B reach-cache rebuild controls.
 *
 * @param {{
 *   ctx: WalkerCorpusContext,
 *   getWalkerSessionLockHolderId: () => string,
 *   setRebuildStatus: (patch: string, model: Record<string, any>) => void,
 *   rebuildWalkerReachCache: (args: {patch: string, runId: string, lockHolderId: string}) => Promise<WalkerRebuildReachCacheResponse|WalkerApiErrorPayload>,
 *   refreshWalkerStatsMicroState: () => Promise<void>
 * }} deps - Action dependencies.
 * @returns {void}
 */
export function initReachCacheActions(deps) {
  ['a', 'b'].forEach(patch => {
    const rebuildBtn = document.getElementById(`rebuild-reach-cache-${patch}`);
    const rebuildStatusEl = document.getElementById(`rebuild-reach-status-${patch}`);
    const rebuildBadgeEl = document.getElementById(`rebuild-reach-badge-${patch}`);
    if (!rebuildBtn || !rebuildStatusEl || !rebuildBadgeEl) return;

    rebuildBtn.addEventListener('click', async () => {
      const P = patch.toUpperCase();
      const runId = deps.ctx.state[`corpus${P}`];
      if (typeof runId !== 'string' || runId.length === 0) {
        deps.ctx.setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      const holderId = deps.getWalkerSessionLockHolderId();
      rebuildBtn.disabled = true;
      deps.setRebuildStatus(patch, {
        state: 'rebuilding',
        reason: 'manual rebuild started',
      });
      deps.ctx.setStatus(`Patch ${P}: rebuilding reach cache…`);

      try {
        const payload = await deps.rebuildWalkerReachCache({
          patch,
          runId,
          lockHolderId: holderId,
        });
        if (payload.error) {
          deps.setRebuildStatus(patch, {
            state: 'error',
            reason: payload.error,
          });
          deps.ctx.setStatus(`Patch ${P}: reach-cache rebuild failed — ${payload.error}`);
          return;
        }

        deps.setRebuildStatus(patch, {
          state: 'rebuilt',
          reason: payload.verification_reason,
          inputHash: payload.ipc_input_hash,
          outputHash: payload.ipc_output_hash,
        });
        deps.ctx.setStatus(`Patch ${P}: reach cache rebuilt`);
        await deps.refreshWalkerStatsMicroState();
      } catch (err) {
        deps.setRebuildStatus(patch, {
          state: 'error',
          reason: err.message,
        });
        deps.ctx.setStatus(`Patch ${P}: reach-cache rebuild failed — ${err.message}`);
      } finally {
        rebuildBtn.disabled = false;
      }
    });
  });
}
