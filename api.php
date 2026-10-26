<?php
/* Tiếng Anh Nhà Mình – lưu kết quả bài tập trên hosting.
   Đặt file này cùng thư mục với index.html. Dữ liệu nằm trong thư mục tanm-data/ (tự tạo, được chặn truy cập trực tiếp).
   Mật khẩu quản trị được kiểm tra bằng chính mật khẩu đang dùng trong index.html, không cần cấu hình gì thêm. */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

const MAX_RECORDS = 50000;      // tổng số lần làm bài tối đa được lưu
const MAX_BODY = 20000;         // kích thước tối đa một lần gửi (byte)

$dir = __DIR__ . '/tanm-data';
$file = $dir . '/results.php';  // đuôi .php + dòng exit ở đầu: mở trực tiếp sẽ không thấy dữ liệu
$lockFile = $dir . '/admin-lock.php';

function out($data, $code = 200){ http_response_code($code); echo json_encode($data, JSON_UNESCAPED_UNICODE); exit; }
function fail($msg, $code = 400){ out(['ok' => false, 'error' => $msg], $code); }

function ensure_dir($dir){
  if(!is_dir($dir) && !@mkdir($dir, 0755, true)) fail('Không tạo được thư mục lưu dữ liệu trên hosting (tanm-data). Hãy cấp quyền ghi cho thư mục web.', 500);
  if(!file_exists("$dir/.htaccess")) @file_put_contents("$dir/.htaccess", "Require all denied\nDeny from all\n");
  if(!file_exists("$dir/index.html")) @file_put_contents("$dir/index.html", "");
}
function load_db($file){
  if(!file_exists($file)) return ['v' => 1, 'students' => [], 'results' => []];
  $raw = file_get_contents($file);
  $p = strpos($raw, "\n");
  $db = json_decode($p === false ? '' : substr($raw, $p + 1), true);
  return is_array($db) ? $db : ['v' => 1, 'students' => [], 'results' => []];
}
/* đọc – sửa – ghi trong một khóa file để nhiều máy gửi cùng lúc không bị mất dữ liệu */
function with_db($file, $fn){
  $fh = fopen($file, 'c+'); if(!$fh) fail('Không ghi được dữ liệu trên hosting.', 500);
  flock($fh, LOCK_EX);
  $raw = stream_get_contents($fh); $p = strpos($raw, "\n");
  $db = json_decode($p === false ? '' : substr($raw, $p + 1), true);
  if(!is_array($db)) $db = ['v' => 1, 'students' => [], 'results' => []];
  $res = $fn($db);
  ftruncate($fh, 0); rewind($fh);
  fwrite($fh, "<?php http_response_code(404); exit; ?>\n" . json_encode($db, JSON_UNESCAPED_UNICODE));
  fflush($fh); flock($fh, LOCK_UN); fclose($fh);
  return $res;
}
function clean_name($s){
  $s = trim(preg_replace('/\s+/u', ' ', (string)$s));
  $s = preg_replace('/[<>"\\\\]/u', '', $s);
  return function_exists('mb_substr') ? mb_substr($s, 0, 24, 'UTF-8') : substr($s, 0, 48);
}
function clean_rec($r){
  if(!is_array($r)) return null;
  $n = (int)($r['n'] ?? 0); $ok = (int)($r['ok'] ?? -1);
  if($n < 1 || $n > 500 || $ok < 0 || $ok > $n) return null;
  $title = trim(strip_tags((string)($r['title'] ?? '')));
  return [
    'id' => substr(preg_replace('/[^A-Za-z0-9:_-]/', '', (string)($r['id'] ?? '')), 0, 80),
    'title' => function_exists('mb_substr') ? mb_substr($title, 0, 120, 'UTF-8') : substr($title, 0, 200),
    'n' => $n, 'ok' => $ok,
    'sec' => max(0, min(86400, (int)($r['sec'] ?? 0))),
    'lim' => max(0, min(86400, (int)($r['lim'] ?? 0))),
    'at' => (int)($r['at'] ?? 0) > 1500000000000 && (int)$r['at'] < (time() + 86400) * 1000 ? (int)$r['at'] : time() * 1000,
    'uid' => substr(preg_replace('/[^A-Za-z0-9-]/', '', (string)($r['uid'] ?? '')), 0, 40),
  ];
}
/* mật khẩu quản trị = mật khẩu đã đặt trong index.html (PBKDF2-SHA256) */
function admin_ok($pw, $lockFile){
  $lock = file_exists($lockFile) ? json_decode(substr(file_get_contents($lockFile), strpos(file_get_contents($lockFile), "\n") + 1), true) : null;
  if(is_array($lock) && ($lock['until'] ?? 0) > time()) fail('Nhập sai mật khẩu nhiều lần. Thử lại sau ít phút.', 429);
  $html = @file_get_contents(__DIR__ . '/index.html');
  if(!$html || !preg_match('#<script type="application/json" id="site-data">(.*?)</script>#s', $html, $m)) fail('Không đọc được index.html trên hosting.', 500);
  $data = json_decode($m[1], true); $a = $data['site']['auth'] ?? null;
  if(!$a || empty($a['salt']) || empty($a['hash'])) fail('Trang chưa đặt mật khẩu quản trị.', 500);
  if(class_exists('Normalizer')) $pw = Normalizer::normalize((string)$pw, Normalizer::FORM_C);
  $h = hash_pbkdf2('sha256', (string)$pw, hex2bin($a['salt']), (int)$a['iter'], 64);
  if(hash_equals(strtolower($a['hash']), $h)){ @unlink($lockFile); return true; }
  $n = (is_array($lock) ? (int)($lock['n'] ?? 0) : 0) + 1;
  @file_put_contents($lockFile, "<?php exit; ?>\n" . json_encode($n >= 5 ? ['n' => 0, 'until' => time() + 120] : ['n' => $n]));
  fail('Mật khẩu chưa đúng.', 403);
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$a = $_GET['a'] ?? '';
$body = [];
if($method === 'POST'){
  $raw = file_get_contents('php://input', false, null, 0, MAX_BODY + 1);
  if(strlen($raw) > MAX_BODY) fail('Dữ liệu gửi lên quá lớn.', 413);
  $body = json_decode($raw, true); if(!is_array($body)) fail('Dữ liệu không hợp lệ.');
  $a = $body['a'] ?? $a;
}

if($a === 'ping'){
  $writable = (is_dir($dir) ? is_writable($dir) : is_writable(__DIR__));
  out(['ok' => true, 'v' => 1, 'writable' => $writable]);
}
ensure_dir($dir);

if($a === 'students'){
  $db = load_db($file);
  out(['ok' => true, 'students' => array_values($db['students'] ?? [])]);
}
if($a === 'mine'){
  $name = clean_name($_GET['student'] ?? '');
  if($name === '') fail('Thiếu tên học sinh.');
  $db = load_db($file);
  $list = array_values(array_filter($db['results'] ?? [], function($r) use ($name){ return ($r['s'] ?? '') === $name; }));
  $list = array_map(function($r){ unset($r['s']); return $r; }, array_slice($list, -400));
  out(['ok' => true, 'results' => $list]);
}
if($a === 'save' && $method === 'POST'){
  $name = clean_name($body['student'] ?? '');
  if($name === '') fail('Thiếu tên học sinh.');
  $recs = isset($body['recs']) && is_array($body['recs']) ? array_slice($body['recs'], 0, 50) : [$body['rec'] ?? null];
  $saved = with_db($file, function(&$db) use ($name, $recs){
    if(!in_array($name, $db['students'], true)) $db['students'][] = $name;
    $have = []; foreach(array_slice($db['results'], -2000) as $r) if(!empty($r['uid'])) $have[$r['uid']] = 1;
    $n = 0;
    foreach($recs as $r){ $c = clean_rec($r); if(!$c) continue; if($c['uid'] && isset($have[$c['uid']])){ $n++; continue; } $c['s'] = $name; $db['results'][] = $c; $n++; }
    if(count($db['results']) > MAX_RECORDS) $db['results'] = array_slice($db['results'], -MAX_RECORDS);
    return $n;
  });
  out(['ok' => true, 'saved' => $saved]);
}
if($a === 'add-student' && $method === 'POST'){
  $name = clean_name($body['student'] ?? '');
  if($name === '') fail('Thiếu tên học sinh.');
  with_db($file, function(&$db) use ($name){ if(!in_array($name, $db['students'], true)) $db['students'][] = $name; });
  out(['ok' => true]);
}
if($a === 'all' && $method === 'POST'){
  admin_ok($body['pw'] ?? '', $lockFile);
  $db = load_db($file);
  out(['ok' => true, 'students' => $db['students'] ?? [], 'results' => $db['results'] ?? []]);
}
if($a === 'delete' && $method === 'POST'){
  admin_ok($body['pw'] ?? '', $lockFile);
  $name = clean_name($body['student'] ?? '');
  $dropName = !empty($body['dropName']);
  with_db($file, function(&$db) use ($name, $dropName){
    $db['results'] = array_values(array_filter($db['results'], function($r) use ($name){ return ($r['s'] ?? '') !== $name; }));
    if($dropName) $db['students'] = array_values(array_filter($db['students'], function($s) use ($name){ return $s !== $name; }));
  });
  out(['ok' => true]);
}
fail('Yêu cầu không hợp lệ.', 404);
