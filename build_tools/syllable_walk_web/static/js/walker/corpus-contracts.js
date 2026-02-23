/*
   walker/corpus-contracts.js
   Shared JSDoc typedef contracts for Walker corpus/session frontend modules.
*/

'use strict';

export {};

/**
 * Generic API error payload shape used by Walker endpoints.
 *
 * @typedef {object} WalkerApiErrorPayload
 * @property {string} error
 * @property {string=} lock_status
 * @property {string=} active_session_id
 * @property {Record<string, any>|null=} lock
 */

/**
 * Session lock metadata from API.
 *
 * @typedef {object} WalkerSessionLockMetadata
 * @property {string=} holder_id
 * @property {string=} expires_at_utc
 */

/**
 * Session lock status payload.
 *
 * @typedef {object} SessionLockStatusResponse
 * @property {string} status
 * @property {string} reason
 * @property {WalkerSessionLockMetadata|null} lock
 */

/**
 * Session lock model used by UI state/rendering.
 *
 * @typedef {object} SessionLockState
 * @property {string} status
 * @property {string} reason
 * @property {string|null} sessionId
 * @property {WalkerSessionLockMetadata|null} lock
 */

/**
 * One saved session entry from ``/api/walker/sessions``.
 *
 * @typedef {object} WalkerSessionListEntry
 * @property {string} session_id
 * @property {string|null=} created_at_utc
 * @property {string|null=} label
 * @property {string|null=} patch_a_run_id
 * @property {string|null=} patch_b_run_id
 * @property {string=} verification_status
 * @property {string=} verification_reason
 * @property {string|null=} root_session_id
 * @property {string|null=} parent_session_id
 * @property {number|null=} revision
 * @property {string|null=} lock_status
 * @property {WalkerSessionLockMetadata|null=} lock
 */

/**
 * ``/api/walker/sessions`` payload.
 *
 * @typedef {object} WalkerSessionsPayload
 * @property {WalkerSessionListEntry[]} sessions
 */

/**
 * Per-patch load result block in ``/api/walker/load-session`` response.
 *
 * @typedef {object} WalkerSessionLoadPatchResult
 * @property {boolean} loaded
 * @property {boolean} restored
 * @property {string} verification_status
 * @property {string} verification_reason
 * @property {string|null=} run_id
 * @property {string[]=} restored_kinds
 * @property {string|null=} status
 * @property {string|null=} source
 * @property {number|null=} syllable_count
 * @property {string|null=} run_state_ipc_input_hash
 * @property {string|null=} run_state_ipc_output_hash
 */

/**
 * ``/api/walker/load-session`` payload.
 *
 * @typedef {object} WalkerSessionLoadPayload
 * @property {string} status
 * @property {string} reason
 * @property {string} session_id
 * @property {string|null=} ipc_input_hash
 * @property {string|null=} ipc_output_hash
 * @property {boolean=} recovered_from_stale_session
 * @property {SessionLockStatusResponse=} session_lock
 * @property {WalkerSessionLoadPatchResult=} patch_a
 * @property {WalkerSessionLoadPatchResult=} patch_b
 */

/**
 * Per-patch save status block in ``/api/walker/save-session`` response.
 *
 * @typedef {object} WalkerSessionSavePatchStatus
 * @property {string|null=} status
 * @property {string|null=} reason
 */

/**
 * ``/api/walker/save-session`` payload.
 *
 * @typedef {object} WalkerSessionSavePayload
 * @property {string=} status
 * @property {string=} reason
 * @property {string|null=} session_id
 * @property {string|null=} session_path
 * @property {string=} sessions_base
 * @property {WalkerSessionSavePatchStatus=} patch_a
 * @property {WalkerSessionSavePatchStatus=} patch_b
 * @property {string|null=} ipc_input_hash
 * @property {string|null=} ipc_output_hash
 * @property {string|null=} root_session_id
 * @property {string|null=} parent_session_id
 * @property {number|null=} revision
 */

/**
 * ``/api/walker/load-corpus`` payload.
 *
 * @typedef {object} WalkerLoadCorpusResponse
 * @property {string=} patch
 * @property {string=} run_id
 * @property {string=} corpus_type
 * @property {number=} syllable_count
 * @property {string=} source
 * @property {string=} status
 */

/**
 * ``/api/walker/rebuild-reach-cache`` payload.
 *
 * @typedef {object} WalkerRebuildReachCacheResponse
 * @property {string=} patch
 * @property {string=} run_id
 * @property {string=} status
 * @property {string|null=} ipc_input_hash
 * @property {string|null=} ipc_output_hash
 * @property {string|null=} verification_status
 * @property {string|null=} verification_reason
 */

/**
 * One pipeline run entry from ``/api/pipeline/runs``.
 *
 * @typedef {object} WalkerPipelineRun
 * @property {string=} run_id
 * @property {string=} path
 * @property {number=} syllable_count
 * @property {number=} selection_count
 * @property {string=} extractor_type
 */

/**
 * ``/api/pipeline/runs`` payload.
 *
 * @typedef {object} WalkerPipelineRunsPayload
 * @property {WalkerPipelineRun[]} runs
 */

/**
 * Stats patch sub-block from ``/api/walker/stats``.
 *
 * @typedef {object} WalkerPatchStats
 * @property {string|null=} corpus
 * @property {string|null=} corpus_type
 * @property {number=} syllable_count
 * @property {boolean=} walker_ready
 * @property {string|null=} loading_stage
 * @property {string|null=} loading_error
 * @property {string=} loader_status
 * @property {string|null=} manifest_ipc_input_hash
 * @property {string|null=} manifest_ipc_output_hash
 * @property {string|null=} manifest_ipc_verification_status
 * @property {string|null=} manifest_ipc_verification_reason
 * @property {string|null=} reach_cache_status
 * @property {string|null=} reach_cache_ipc_input_hash
 * @property {string|null=} reach_cache_ipc_output_hash
 * @property {string|null=} reach_cache_ipc_verification_status
 * @property {string|null=} reach_cache_ipc_verification_reason
 * @property {Record<string, any>=} reaches
 */

/**
 * Patch comparison block from ``/api/walker/stats``.
 *
 * @typedef {object} WalkerPatchComparison
 * @property {'same'|'different'|'unknown'|string=} corpus_hash_relation
 * @property {string=} policy
 * @property {string=} reason
 */

/**
 * ``/api/walker/stats`` payload.
 *
 * @typedef {object} WalkerStatsPayload
 * @property {WalkerPatchStats=} patch_a
 * @property {WalkerPatchStats=} patch_b
 * @property {WalkerPatchComparison=} patch_comparison
 */

/**
 * Session integrity UI model.
 *
 * @typedef {object} SessionIntegrityState
 * @property {'unknown'|'verified'|'stale'|'mismatch'|'missing'|'error'} status
 * @property {string} reason
 * @property {boolean} recoveredFromStale
 * @property {WalkerSessionLoadPatchResult|null} patchA
 * @property {WalkerSessionLoadPatchResult|null} patchB
 * @property {string} topStatus
 * @property {string} topReason
 */

/**
 * Shared corpus module context.
 *
 * @typedef {object} WalkerCorpusContext
 * @property {Record<string, any>} state
 * @property {(msg: string) => void} setStatus
 * @property {(patch: string, reaches: Record<string, any>) => void} updateReachValues
 */
