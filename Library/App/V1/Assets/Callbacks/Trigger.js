/**
 * @param {Object} payload
 * @param {Array} payload.injected_inputs
 * @param {Array} payload.injected_states
 * @param {Array} payload.original_inputs
 * @param {Array} payload.original_states
 */
(function(payload) {
    const trigger = payload.injected_inputs[0];
    if (!trigger || Object.keys(trigger).length === 0) return window.dash_clientside.no_update;
    let t = Object.assign({}, trigger);
    t.index = (t.index || 0) + 1;
    t.counter = (t.counter || 0) + 1;
    return t;
})