/**
 * @param {Object} payload
 * @param {Array} payload.injected_inputs
 * @param {Array} payload.injected_states
 * @param {Array} payload.original_inputs
 * @param {Array} payload.original_states
 */
(function(payload) {
    if (!payload.original_inputs[0]) return window.dash_clientside.no_update;
})