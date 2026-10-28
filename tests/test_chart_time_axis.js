// Check forensic time-axis contract in the actual dashboard source.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const html = fs.readFileSync(path.resolve(__dirname, "../index.html"), "utf8");
const start = html.indexOf("function snapshotClockMs(row)");
const end = html.indexOf("function labelTimeFrom(", start);
assert.ok(start >= 0 && end > start, "Missing time-axis helpers");
const helpers = html.slice(start, end);
const { snapshotClockMs, clockAxisLabel } = vm.runInNewContext(
    helpers + "\n({snapshotClockMs, clockAxisLabel})");
const p = snapshotClockMs({dt:"04/10/2026",ht:"20:04:39"});
const q = snapshotClockMs({dt:"04/10/2026",ht:"20:30:35"});
assert.equal((q-p)/1000, 1556, "Spacing must use elapsed seconds, not record index");
const a = snapshotClockMs({dt:"04/10/2026",ht:"23:59:55"});
const b = snapshotClockMs({dt:"05/10/2026",ht:"00:00:05"});
assert.equal(b-a,10000,"Midnight crossing broken");
assert.equal(clockAxisLabel(p),"04/10 20:04");
assert.ok(Number.isNaN(snapshotClockMs({dt:"04/10/2026",ht:""})));
assert.ok(Number.isNaN(snapshotClockMs({dt:"31/02/2026",ht:"12:20:01"})));
assert.ok(html.includes('effectiveXm==="time"?clockValues[i]:i'),"Real time axis must use timestamps");
assert.ok(html.includes('Eixo: atualização (espaçamento igual)'),"Index mode needs truthful label");
assert.ok(html.includes("Se faltar horario, nao rotular indice como relogio"),"Missing-time fallback must be explicit");
process.stdout.write("Dashboard forensic timeline: true wall-time spacing and midnight rollover OK\n");
