/* Tiếng Anh không khó – lưu kết quả bài tập vào Google Sheets (miễn phí, thay cho api.php).
   Cách dùng: xem file HUONG-DAN-GITHUB-PAGES.txt */

const ADMIN_PASSWORD = 'TiengAnhkokho@123!';   // <-- ĐỔI thành mật khẩu của anh/chị (dùng để xem kết quả trong Quản trị)
const MAX_RECORDS = 50000;

function sheet_(name, head) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(head); sh.setFrozenRows(1); }
  return sh;
}
const RES_HEAD = ['Học sinh', 'Mã bài', 'Tên bài', 'Số câu', 'Đúng', 'Giây', 'Giới hạn (giây)', 'Thời điểm', 'uid'];
const resSheet_ = () => sheet_('KetQua', RES_HEAD);
const stuSheet_ = () => sheet_('HocSinh', ['Học sinh']);

function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function fail_(m) { return out_({ ok: false, error: m }); }
function cleanName_(s) { return String(s || '').replace(/\s+/g, ' ').replace(/[<>"\\]/g, '').trim().slice(0, 24); }

function students_() {
  const v = stuSheet_().getDataRange().getValues().slice(1).map(r => String(r[0])).filter(Boolean);
  return v;
}
function addStudent_(name) {
  const sh = stuSheet_();
  if (students_().indexOf(name) < 0) sh.appendRow([name]);
}
function rowToRec_(r) {
  return { s: String(r[0]), id: String(r[1]), title: String(r[2]), n: +r[3], ok: +r[4], sec: +r[5], lim: +r[6], at: +r[7], uid: String(r[8] || '') };
}
function allRows_() {
  const sh = resSheet_();
  if (sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 9).getValues();
}
function adminOk_(pw) {
  const c = CacheService.getScriptCache();
  const bad = +(c.get('bad') || 0);
  if (bad >= 5) throw new Error('Nhập sai mật khẩu nhiều lần. Thử lại sau ít phút.');
  if (String(pw || '') === ADMIN_PASSWORD && ADMIN_PASSWORD !== 'doi-mat-khau-nay') { c.remove('bad'); return; }
  c.put('bad', String(bad + 1), 120);
  throw new Error(ADMIN_PASSWORD === 'doi-mat-khau-nay' ? 'Chưa đặt mật khẩu trong Apps Script (dòng ADMIN_PASSWORD).' : 'Mật khẩu chưa đúng.');
}
function cleanRec_(r) {
  if (!r) return null;
  const n = +r.n || 0, ok = +r.ok;
  if (n < 1 || n > 500 || !(ok >= 0) || ok > n) return null;
  const now = Date.now(); let at = +r.at || 0;
  if (!(at > 1500000000000 && at < now + 86400000)) at = now;
  return [String(r.id || '').replace(/[^A-Za-z0-9:_-]/g, '').slice(0, 80), String(r.title || '').replace(/<[^>]*>/g, '').slice(0, 120),
    n, ok, Math.max(0, Math.min(86400, +r.sec || 0)), Math.max(0, Math.min(86400, +r.lim || 0)), at, String(r.uid || '').replace(/[^A-Za-z0-9-]/g, '').slice(0, 40)];
}

function handle_(a, body, p) {
  if (a === 'ping') return { ok: true, v: 1, writable: true };
  if (a === 'students') return { ok: true, students: students_() };
  if (a === 'mine') {
    const name = cleanName_(p.student); if (!name) throw new Error('Thiếu tên học sinh.');
    const list = allRows_().filter(r => String(r[0]) === name).slice(-400).map(rowToRec_);
    list.forEach(x => delete x.s);
    return { ok: true, results: list };
  }
  if (a === 'save') {
    const name = cleanName_(body.student); if (!name) throw new Error('Thiếu tên học sinh.');
    const recs = Array.isArray(body.recs) ? body.recs.slice(0, 50) : [body.rec];
    const lock = LockService.getScriptLock(); lock.waitLock(20000);
    try {
      addStudent_(name);
      const sh = resSheet_(), rows = allRows_();
      const have = {}; rows.slice(-2000).forEach(r => { if (r[8]) have[String(r[8])] = 1; });
      const add = []; let n = 0;
      recs.forEach(r => { const c = cleanRec_(r); if (!c) return; n++; if (c[7] && have[c[7]]) return; have[c[7]] = 1; add.push([name].concat(c)); });
      if (add.length) sh.getRange(sh.getLastRow() + 1, 1, add.length, 9).setValues(add);
      if (sh.getLastRow() - 1 > MAX_RECORDS) sh.deleteRows(2, sh.getLastRow() - 1 - MAX_RECORDS);
      return { ok: true, saved: n };
    } finally { lock.releaseLock(); }
  }
  if (a === 'add-student') {
    const name = cleanName_(body.student); if (!name) throw new Error('Thiếu tên học sinh.');
    const lock = LockService.getScriptLock(); lock.waitLock(20000);
    try { addStudent_(name); } finally { lock.releaseLock(); }
    return { ok: true };
  }
  if (a === 'all') { adminOk_(body.pw); return { ok: true, students: students_(), results: allRows_().map(rowToRec_) }; }
  if (a === 'delete') {
    adminOk_(body.pw);
    const name = cleanName_(body.student);
    const lock = LockService.getScriptLock(); lock.waitLock(20000);
    try {
      const keep = allRows_().filter(r => String(r[0]) !== name);
      const sh = resSheet_(); if (sh.getLastRow() > 1) sh.getRange(2, 1, sh.getLastRow() - 1, 9).clearContent();
      if (keep.length) sh.getRange(2, 1, keep.length, 9).setValues(keep);
      if (body.dropName) {
        const st = stuSheet_(), left = students_().filter(s => s !== name);
        if (st.getLastRow() > 1) st.getRange(2, 1, st.getLastRow() - 1, 1).clearContent();
        if (left.length) st.getRange(2, 1, left.length, 1).setValues(left.map(s => [s]));
      }
    } finally { lock.releaseLock(); }
    return { ok: true };
  }
  throw new Error('Yêu cầu không hợp lệ.');
}
function doGet(e) { try { return out_(handle_(e.parameter.a || '', {}, e.parameter)); } catch (err) { return fail_(err.message); } }
function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents || '{}');
    return out_(handle_(body.a || '', body, e.parameter || {}));
  } catch (err) { return fail_(err.message); }
}
