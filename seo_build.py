# -*- coding: utf-8 -*-
"""SEO cho tienganhkhongkho.com (build.py gọi sau khi tạo dist/index.html)
- dist/bai/<ten-bai>.html : mỗi bài một trang tĩnh, có tiêu đề, mô tả, nội dung đầy đủ để máy tìm kiếm đọc
- dist/sitemap.xml, dist/robots.txt
- seo_head() / seo_home_body(): thẻ meta, dữ liệu có cấu trúc, danh sách bài cho trang chủ
"""
import json, os, re, html, unicodedata, shutil

SITE = 'https://tienganhkhongkho.com'
NAME = 'Tiếng Anh không khó'
STORE = 'https://apps.microsoft.com/detail/9PLP28PDD0X5'
DESC = ('Học tiếng Anh miễn phí cho mọi lứa tuổi, từ bé mầm non, học sinh đến người lớn: ngữ pháp, từ vựng, phát âm, '
        'giao tiếp, đọc, viết, hơn 20.000 câu bài tập chấm điểm ngay, kiểm tra trình độ, thi thử và trò chơi.')

def slug(t):
    t = t.replace('đ', 'd').replace('Đ', 'D')
    t = unicodedata.normalize('NFD', t)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn').lower()
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t[:70].rstrip('-') or 'bai'

def text_of(h):
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    h = re.sub(r'<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', html.unescape(h)).strip()

def desc_of(p):
    t = text_of(p['html'])
    t = re.sub(r'^(Ghi chú\s*)', '', t)
    if len(t) > 155:
        t = t[:155].rsplit(' ', 1)[0].rstrip(',;:–-') + '…'
    return t or (p['title'] + ' – bài học tiếng Anh miễn phí.')

def esc(s): return html.escape(s, quote=True)

def lessons(data):
    menus = {m['id']: m for m in data['menus']}
    def path(mid):
        out = []; m = menus.get(mid)
        while m: out.insert(0, m); m = menus.get(m.get('parent'))
        return out
    def pending(p): return p['html'].startswith('<p class="note">') and len(text_of(p['html'])) < 260
    def order(m):
        ch = sorted([x for x in data['menus'] if x.get('parent') == m], key=lambda x: x.get('order', 0))
        return ch
    out, used = [], set()
    for p in data['posts']:
        if p.get('menu') == 'trang-chu' or p['id'] == 'cai-giong-doc' or pending(p): continue
        s = slug(p['title'])
        if s in used: s = (s[:60] + '-' + slug(p['id']))[:80]
        used.add(s)
        out.append({'p': p, 'slug': s, 'path': path(p.get('menu'))})
    return out

def root_menus(data):
    return sorted([m for m in data['menus'] if not m.get('parent') and m['id'] != 'trang-chu'], key=lambda m: m.get('order', 0))

def seo_head(icon_tag=''):
    ld = [{
        '@context': 'https://schema.org', '@type': 'WebSite', 'name': NAME, 'alternateName': 'tienganhkhongkho.com',
        'url': SITE + '/', 'inLanguage': 'vi', 'description': DESC},
        {'@context': 'https://schema.org', '@type': 'EducationalOrganization', 'name': NAME, 'url': SITE + '/',
         'logo': SITE + '/icons/icon-512.png', 'sameAs': [STORE]}]
    return ('<title>Tiếng Anh không khó – Học tiếng Anh miễn phí cho mọi lứa tuổi</title>'
            '<meta name="description" content="' + esc(DESC) + '">'
            '<link rel="canonical" href="' + SITE + '/">'
            '<meta name="robots" content="index,follow,max-image-preview:large">'
            '<meta property="og:type" content="website"><meta property="og:site_name" content="' + NAME + '">'
            '<meta property="og:title" content="Tiếng Anh không khó – Học tiếng Anh miễn phí"><meta property="og:description" content="' + esc(DESC) + '">'
            '<meta property="og:url" content="' + SITE + '/"><meta property="og:locale" content="vi_VN">'
            '<meta property="og:image" content="' + SITE + '/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            '<meta name="twitter:card" content="summary_large_image">'
            '<meta name="msapplication-TileColor" content="#2747C9">'
            '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>')

def seo_home_body(data):
    """nội dung tạm trong #app: người dùng thấy trong tích tắc trước khi trang chạy, máy tìm kiếm đọc được danh sách bài"""
    ls = lessons(data); by = {}
    for x in ls: by.setdefault(x['path'][0]['id'] if x['path'] else '', []).append(x)
    parts = []
    for m in root_menus(data):
        xs = by.get(m['id'])
        if not xs: continue
        parts.append('<h2>' + esc(m['title'].capitalize() if m['title'].isupper() else m['title']) + '</h2><ul>' +
                     ''.join('<li><a href="/bai/' + x['slug'] + '.html">' + esc(x['p']['title']) + '</a></li>' for x in xs) + '</ul>')
    return ('<div class="seo-home" style="max-width:900px;margin:0 auto;padding:24px 16px;font-family:system-ui,sans-serif">'
            '<h1>Tiếng Anh không khó – học tiếng Anh miễn phí</h1><p>' + esc(DESC) + '</p>'
            '<p><a href="' + STORE + '">Tải ứng dụng trên Microsoft Store</a></p>' + ''.join(parts) + '</div>')

PAGE_CSS = '''
body{margin:0;background:var(--bg)}
.sp-bar{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.sp-bar-in,.sp-main,.sp-foot-in{max-width:980px;margin:0 auto;padding-left:16px;padding-right:16px}
.sp-bar-in{display:flex;align-items:center;gap:12px;height:64px}
.sp-brand{display:flex;align-items:center;gap:10px;color:var(--ink);text-decoration:none;font-family:var(--f-display);font-weight:800;font-size:20px;min-width:0}
.sp-brand svg{width:40px;height:40px;flex:none}
.sp-brand span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sp-bar .btn{margin-left:auto;white-space:nowrap}
.sp-main{padding-top:20px;padding-bottom:40px}
.sp-crumb{font-size:14px;color:var(--muted);margin-bottom:10px}.sp-crumb a{color:var(--muted)}
.sp-cta{display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:var(--accent-soft);border-radius:16px;padding:14px 16px;margin:14px 0 22px}
.sp-cta p{margin:0;flex:1 1 260px}
.sp-rel{margin-top:28px}.sp-rel ul{columns:2 260px;padding-left:18px}.sp-rel li{margin:4px 0}
.sp-foot{border-top:1px solid var(--line);background:#fff}.sp-foot-in{padding-top:18px;padding-bottom:28px;font-size:14px;color:var(--muted)}
.sp-foot a{color:var(--accent)}
.prose .say,.prose button{display:none}
'''

def page(x, all_ls, data, mark, fonts, icon_tag, css_href):
    p = x['p']; t = p['title']; url = SITE + '/bai/' + x['slug'] + '.html'; d = desc_of(p)
    by_id = {y['p']['id']: y for y in all_ls}
    menus = {m['id'] for m in data['menus']}
    def fix(m):
        tgt = m.group(2)
        if tgt in by_id: return m.group(1) + '/bai/' + by_id[tgt]['slug'] + '.html"'
        if tgt and ('id="' + tgt + '"') in p['html']: return m.group(0)   # neo trong bài
        if re.fullmatch(r'cd-\d+', tgt or ''): return m.group(0)       # mục lục: mục thứ N (thẻ h2 thứ N)
        if tgt: return m.group(1) + '/#' + tgt + '"'
        return m.group(0)
    body = re.sub(r'(href=")#([\w-]*)"', fix, p['html'])
    n = [0]
    def h2id(m):
        n[0] += 1
        return m.group(0) if 'id=' in m.group(1) else '<h2 id="cd-' + str(n[0]) + '"' + m.group(1) + '>'
    body = re.sub(r'<h2\b([^>]*)>', h2id, body)
    def wrap(m):
        pre = body[max(0, m.start() - 40):m.start()]
        return m.group(0) if pre.endswith('<div class="table-wrap">') else '<div class="table-wrap">' + m.group(0) + '</div>'
    body = re.sub(r'<table\b.*?</table>', wrap, body, flags=re.S)
    crumbs = [('/', 'Trang chủ')] + [('/#' + m['id'], m['title']) for m in x['path']]
    crumb_html = ' / '.join('<a href="' + h + '">' + esc(n) + '</a>' for h, n in crumbs)
    sib = [y for y in all_ls if y['p'].get('menu') == p.get('menu') and y is not x][:12]
    if len(sib) < 6:
        top = x['path'][0]['id'] if x['path'] else ''
        sib += [y for y in all_ls if y['path'] and y['path'][0]['id'] == top and y is not x and y not in sib][:12 - len(sib)]
    ld = [{'@context': 'https://schema.org', '@type': 'LearningResource', 'name': t, 'headline': t, 'description': d,
           'inLanguage': 'vi', 'url': url, 'isAccessibleForFree': True, 'learningResourceType': 'Bài học',
           'educationalLevel': 'Mọi trình độ', 'dateModified': p.get('updated') or '',
           'publisher': {'@type': 'Organization', 'name': NAME, 'url': SITE + '/', 'logo': SITE + '/icons/icon-512.png'}},
          {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
              {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + h} for i, (h, n) in enumerate(crumbs)]}]
    app = '/#' + p['id']
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + esc(t) + ' – Tiếng Anh không khó</title><meta name="description" content="' + esc(d) + '">'
            '<link rel="canonical" href="' + url + '"><meta name="robots" content="index,follow,max-image-preview:large">'
            '<meta property="og:type" content="article"><meta property="og:site_name" content="' + NAME + '">'
            '<meta property="og:title" content="' + esc(t) + '"><meta property="og:description" content="' + esc(d) + '">'
            '<meta property="og:url" content="' + url + '"><meta property="og:locale" content="vi_VN">'
            '<meta property="og:image" content="' + SITE + '/og-image.png"><meta name="twitter:card" content="summary_large_image">'
            '<meta name="theme-color" content="#2747C9"><link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">'
            + icon_tag + fonts + '<link rel="stylesheet" href="' + css_href + '">'
            '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script></head><body>'
            '<header class="sp-bar"><div class="sp-bar-in"><a class="sp-brand" href="/">' + mark + '<span>' + NAME + '</span></a>'
            '<a class="btn btn-p" href="' + app + '">Học bài này</a></div></header>'
            '<main class="sp-main"><nav class="sp-crumb" aria-label="Vị trí">' + crumb_html + '</nav>'
            '<article class="card article"><h1 class="title">' + esc(t) + '</h1>'
            '<div class="sp-cta"><p>Mở bài trong trang học để <b>nghe đọc từng câu</b>, xem dạng video và <b>làm bài tập chấm điểm ngay</b>. Miễn phí.</p>'
            '<a class="btn btn-p" href="' + app + '">Học tương tác</a></div>'
            '<div class="prose">' + body + '</div></article>'
            + ('<section class="sp-rel card"><h2 class="sub-h">Bài học liên quan</h2><ul>' + ''.join('<li><a href="/bai/' + y['slug'] + '.html">' + esc(y['p']['title']) + '</a></li>' for y in sib) + '</ul></section>' if sib else '')
            + '</main><footer class="sp-foot"><div class="sp-foot-in"><p><b>' + NAME + '</b> – trang học tiếng Anh miễn phí cho mọi lứa tuổi. '
            '<a href="/">Trang chủ</a> · <a href="/#bai-tap">Bài tập</a> · <a href="/#kiem-tra-trinh-do">Kiểm tra trình độ</a> · <a href="' + STORE + '">Ứng dụng cho Windows</a> · <a href="/#quyen-rieng-tu">Quyền riêng tư</a></p></div></footer>'
            '</body></html>')

def write_all(data, mark, fonts, icon_tag, css, release_date):
    ls = lessons(data)
    if os.path.isdir('dist/bai'): shutil.rmtree('dist/bai')
    os.makedirs('dist/bai', exist_ok=True)
    open('dist/bai/style.css', 'w', encoding='utf8').write(css + PAGE_CSS)
    for x in ls:
        open('dist/bai/' + x['slug'] + '.html', 'w', encoding='utf8').write(page(x, ls, data, mark, fonts, icon_tag, '/bai/style.css'))
    urls = [(SITE + '/', release_date, '1.0')] + [(SITE + '/bai/' + x['slug'] + '.html', (x['p'].get('updated') or release_date)[:10], '0.8') for x in ls]
    open('dist/sitemap.xml', 'w', encoding='utf8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join('<url><loc>' + u + '</loc><lastmod>' + d + '</lastmod><priority>' + pr + '</priority></url>\n' for u, d, pr in urls) + '</urlset>\n')
    open('dist/robots.txt', 'w', encoding='utf8').write('User-agent: *\nAllow: /\nDisallow: /api.php\n\nSitemap: ' + SITE + '/sitemap.xml\n')
    return ls

# ===================== chạy trên GitHub Actions =====================
# Đọc index.html (dữ liệu gốc + giao diện), lấy bài đã xuất bản trên Supabase (khóa công khai trong config.json),
# rồi tạo bai/*.html, sitemap.xml, robots.txt. Không cần khóa bí mật nào.
import urllib.request, datetime

MARK = "<svg aria-hidden=\"true\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><rect width=\"100\" height=\"100\" rx=\"23\" fill=\"#2747C9\"/><path d=\"M20 22h60a10 10 0 0 1 10 10v30a10 10 0 0 1-10 10H48l-15 13V72H20a10 10 0 0 1-10-10V32a10 10 0 0 1 10-10z\" fill=\"#FFFFFF\"/><polygon points=\"50.0,28.0 55.0,40.1 68.1,41.1 58.1,49.6 61.2,62.4 50.0,55.5 38.8,62.4 41.9,49.6 31.9,41.1 45.0,40.1\" fill=\"#FFD43B\" stroke=\"#F2B705\" stroke-width=\"2\" stroke-linejoin=\"round\"/><circle cx=\"46.5\" cy=\"45\" r=\"1.8\" fill=\"#1B2A6B\"/><circle cx=\"53.5\" cy=\"45\" r=\"1.8\" fill=\"#1B2A6B\"/><path d=\"M46.5 50q3.5 3 7 0\" stroke=\"#1B2A6B\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/></svg>"

def apply_patch(d, p):
    if not isinstance(p, dict): return d
    for kind in ('menus', 'posts'):
        q = p.get(kind) or {}; dele = set(q.get('del') or [])
        d[kind] = [x for x in d[kind] if x['id'] not in dele]
        for x in q.get('set') or []:
            i = next((n for n, y in enumerate(d[kind]) if y['id'] == x['id']), -1)
            if i < 0: d[kind].append(x); continue
            b = d[kind][i]
            if b.get('fx') and x.get('fx') != b.get('fx'): continue      # bản sửa theo yêu cầu luôn thắng
            y = x
            if kind == 'posts' and isinstance(b.get('html'), str) and isinstance(x.get('html'), str) and 'data-add=' in b['html']:
                h = x['html']
                for m in re.finditer(r'<(section|div)\b[^>]*\bdata-add="([\w-]+)"[^>]*>[\s\S]*?</\1><!--/add-->', b['html']):
                    if 'data-add="' + m.group(2) + '"' in h: continue
                    bf = re.match(r'^<[^>]*\bdata-before="([^"]+)"', m.group(0))
                    at = -1
                    if bf:
                        mm = re.search(r'<h[23][^>]*>\s*' + re.escape(bf.group(1)), h)
                        at = mm.start() if mm else -1
                    h = h[:at] + m.group(0) + h[at:] if at >= 0 else h + m.group(0)
                if h != x['html']: y = dict(x, html=h)
            d[kind][i] = y
    return d

def main():
    src = open('index.html', encoding='utf8').read()
    m = re.search(r'<script type="application/json" id="site-data">(.*?)</script>', src, re.S)
    data = json.loads(m.group(1))
    css = re.search(r'<style id="site-css">(.*?)</style>', src, re.S).group(1)
    fonts = (re.search(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', src) or [''])[0]
    icon = (re.search(r'<link rel="icon"[^>]*>', src) or [''])[0]
    try:
        cfg = json.load(open('config.json', encoding='utf8')).get('supabase') or {}
        if cfg.get('url') and cfg.get('key'):
            url = cfg['url'].rstrip('/') + '/rest/v1/rpc/boot'
            h = {'apikey': cfg['key'], 'Content-Type': 'application/json'}
            if cfg['key'].startswith('eyJ'): h['Authorization'] = 'Bearer ' + cfg['key']
            req = urllib.request.Request(url, data=b'{}', headers=h, method='POST')
            j = json.load(urllib.request.urlopen(req, timeout=60))
            data = apply_patch(data, j.get('patch'))
            print('Đã gộp nội dung đã xuất bản, bản', j.get('rev'))
    except Exception as e:
        print('Không lấy được nội dung đã xuất bản, dùng nội dung trong index.html:', e)
    # rà liên kết trong bài (kể cả bài sửa trên trang Quản trị): in ra nhật ký của GitHub Actions
    posts = {p['id'] for p in data['posts']}; menus = {m['id'] for m in data['menus']}
    special = {'bai-tap', 'luyen-noi', 'phieu-luu', 'quan-tri', 'quyen-rieng-tu', 'so-tu', 'thach-dau', 'thi-thu', 'thu-vien', 'trang-chu', 'vui-choi'}
    broken = []
    for p in data['posts']:
        ids = set(re.findall(r'\bid="([^"]+)"', p['html']))
        for tgt in re.findall(r'href="#([^"]*)"', p['html']):
            if not tgt or tgt in posts or tgt in menus or tgt in special or tgt in ids or re.fullmatch(r'cd-\d+', tgt) \
               or tgt.startswith(('bai-tap/', 'thach-dau/', 'thi-thu/', 'unit/', 'vui-choi/')): continue
            broken.append(p['title'] + ' -> #' + tgt)
    print('Liên kết hỏng trong bài:', len(broken))
    for b in broken[:50]: print('  ', b)
    os.makedirs('dist', exist_ok=True)
    ls = write_all(data, MARK, fonts, icon, css, datetime.date.today().isoformat())
    for f in os.listdir('dist'):   # chép ra gốc trang
        s, t = os.path.join('dist', f), f
        if os.path.isdir(s):
            if os.path.isdir(t): shutil.rmtree(t)
            shutil.copytree(s, t)
        else: shutil.copy(s, t)
    shutil.rmtree('dist')
    print('Đã tạo', len(ls), 'trang bài, sitemap.xml, robots.txt')

if __name__ == '__main__':
    main()
