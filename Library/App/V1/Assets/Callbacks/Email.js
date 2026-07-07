/**
 * @param {object} email
 * @param {string|Array} [trigger.to]
 * @param {string|Array} [trigger.cc]
 * @param {string|Array} [trigger.bcc]
 * @param {string} [trigger.subject]
 * @param {string} [trigger.message]
 */
(function(email) {
    if (!email || Object.keys(email).length === 0) return window.dash_clientside.no_update;
    const formatAddresses = (addr) => Array.isArray(addr) ? addr.join(';') : (addr || '');
    let targetTo = formatAddresses(email.to);
    let targetCc = formatAddresses(email.cc);
    let targetBcc = formatAddresses(email.bcc);
    let targetSubject = email.subject || '';
    let targetMessage = email.message || '';
    const params = [];
    if (targetCc) params.push(`cc=${encodeURIComponent(targetCc)}`);
    if (targetBcc) params.push(`bcc=${encodeURIComponent(targetBcc)}`);
    if (targetSubject) params.push(`subject=${encodeURIComponent(targetSubject)}`);
    if (targetMessage) params.push(`body=${encodeURIComponent(targetMessage)}`);
    const queryString = params.length > 0 ? '?' + params.join('&') : '';
    window.location.href = `mailto:${targetTo}${queryString}`;
})