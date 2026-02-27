# -*- coding: utf-8 -*-
"""
Web 版因子展示：用浏览器查看 factor_build / factor_test 输出，不依赖 Tk，避免 macOS Tk 崩溃。
"""
from __future__ import print_function

import os
import sys
import urllib.parse
import html
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

# 项目根
_cwd = os.getcwd()
_root = os.path.dirname(_cwd) if os.path.basename(_cwd) == "factor_display" else _cwd
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import config
except ImportError:
    config = None

import pandas as pd


def get_paths():
    if config is None:
        root = _root
        fb_out = os.path.join(root, "factor_build", "outputs")
        ft_out = os.path.join(root, "factor_test", "outputs")
    else:
        root = config.get_base_dir()
        fb_out = os.path.join(root, "factor_build", getattr(config, "FACTOR_BUILD_OUTPUTS", "outputs"))
        ft_out = os.path.join(root, "factor_test", getattr(config, "FACTOR_TEST_OUTPUTS", "outputs"))
    plots_base = os.path.join(ft_out, "02_factor_plots")
    return root, fb_out, ft_out, plots_base


def safe_read_excel(path, sheet_name=0, max_rows=500):
    if not path or not os.path.isfile(path):
        return None, "文件不存在"
    try:
        if sheet_name == 0:
            df = pd.read_excel(path, nrows=max_rows)
        else:
            df = pd.read_excel(path, sheet_name=sheet_name, nrows=max_rows)
        if df is None or df.empty:
            return None, "表为空"
        return df, None
    except Exception as e:
        return None, str(e)


def safe_listdir(path):
    if not path or not os.path.isdir(path):
        return []
    try:
        return sorted(os.listdir(path))
    except Exception:
        return []


def df_to_html_table(df, err_msg=None):
    if err_msg:
        return '<p class="err">' + html.escape(err_msg) + '</p>'
    if df is None or df.empty:
        return '<p class="err">无数据</p>'
    df = df.astype(str).replace("nan", "")
    out = ['<table class="data-table"><thead><tr>']
    for c in df.columns:
        out.append('<th>' + html.escape(str(c)) + '</th>')
    out.append('</tr></thead><tbody>')
    for _, row in df.iterrows():
        out.append('<tr>')
        for v in row:
            out.append('<td>' + html.escape(str(v)) + '</td>')
        out.append('</tr>')
    out.append('</tbody></table>')
    return ''.join(out)


# 全局路径（Handler 内使用）
_paths = None


def init_paths():
    global _paths
    _paths = get_paths()


def get_paths_tuple():
    global _paths
    if _paths is None:
        init_paths()
    return _paths


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        root, fb_out, ft_out, plots_base = get_paths_tuple()
        path = self.path.split('?')[0]
        qs = {}
        if '?' in self.path:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if path == '/' or path == '/index.html':
            self._send_html(self._index_html())
            return
        if path == '/api/overview':
            self._send_html(self._overview_html(root, fb_out, ft_out, plots_base))
            return
        if path == '/api/build':
            idx = int(qs.get('idx', [0])[0])
            self._send_html(self._build_table_html(fb_out, idx))
            return
        if path == '/api/test':
            idx = int(qs.get('idx', [0])[0])
            self._send_html(self._test_table_html(ft_out, idx))
            return
        if path == '/api/config':
            self._send_html(self._config_html(root, fb_out, ft_out, plots_base))
            return
        if path == '/api/chart_folders':
            self._send_json(self._chart_folders(plots_base))
            return
        if path == '/api/chart_images':
            folder = qs.get('folder', [''])[0]
            folder = urllib.parse.unquote(folder)
            self._send_json(self._chart_images(plots_base, folder))
            return
        if path == '/api/chart_image':
            folder = urllib.parse.unquote(qs.get('folder', [''])[0])
            file_ = urllib.parse.unquote(qs.get('file', [''])[0])
            self._send_chart_image(plots_base, folder, file_)
            return
        self.send_error(404)

    def _send_html(self, body, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def _send_json(self, obj):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode('utf-8'))

    def _send_chart_image(self, plots_base, folder, file_):
        if not folder or not file_ or '..' in folder or '..' in file_:
            self.send_error(400)
            return
        path = os.path.join(plots_base, folder, file_)
        if not os.path.isfile(path):
            self.send_error(404)
            return
        ext = os.path.splitext(file_)[1].lower()
        ctype = 'image/png' if ext == '.png' else ('image/jpeg' if ext in ('.jpg', '.jpeg') else 'application/octet-stream')
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except Exception:
            self.send_error(500)
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def _index_html(self):
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>因子展示 · Factor Display</title>
<style>
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 12px; background: #f5f5f5; }
h1 { margin: 0 0 12px 0; font-size: 1.25rem; color: #333; }
.tabs { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.tabs button { padding: 8px 14px; cursor: pointer; border: 1px solid #ccc; background: #fff; border-radius: 4px; }
.tabs button:hover { background: #eee; }
.tabs button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
#content { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 16px; min-height: 400px; overflow: auto; }
#content pre, #content code { font-family: Consolas, monospace; font-size: 13px; }
#content .err { color: #b91c1c; }
.data-table { border-collapse: collapse; width: 100%; font-size: 13px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
.data-table th { background: #f1f5f9; }
.data-table tr:hover { background: #f8fafc; }
.charts-layout { display: flex; gap: 16px; }
.charts-side { width: 220px; flex-shrink: 0; }
.charts-side h3 { margin: 0 0 8px 0; font-size: 14px; }
.charts-side ul { list-style: none; padding: 0; margin: 0; cursor: pointer; }
.charts-side li { padding: 4px 8px; border-radius: 4px; }
.charts-side li:hover, .charts-side li.selected { background: #e0e7ff; }
.charts-main { flex: 1; min-width: 0; }
.charts-main img { max-width: 100%; height: auto; display: block; }
</style>
</head>
<body>
<h1>因子展示 · Factor Display</h1>
<div class="tabs">
  <button data-tab="overview" class="active">概览</button>
  <button data-tab="build">因子构建</button>
  <button data-tab="test">因子测试</button>
  <button data-tab="charts">图表</button>
  <button data-tab="config">配置</button>
</div>
<div id="content">加载中…</div>

<script>
var content = document.getElementById('content');
function show(tab) {
  document.querySelectorAll('.tabs button').forEach(function(b){ b.classList.remove('active'); });
  var btn = document.querySelector('.tabs button[data-tab="' + tab + '"]');
  if (btn) btn.classList.add('active');
  if (tab === 'overview') {
    fetch('/api/overview').then(function(r){ return r.text(); }).then(function(html){ content.innerHTML = html; });
  } else if (tab === 'build') {
    content.innerHTML = '<label>选择表：<select id="buildSelect"><option value="0">01_y_timeseries（预览）</option><option value="1">03_regression_results（全部）</option><option value="2">03_regression_results（显著）</option><option value="3">04_fusion_constituents</option><option value="4">04_fusion_timeseries（预览）</option></select></label><div id="buildTable"></div>';
    var sel = document.getElementById('buildSelect');
    function loadBuild(){ fetch('/api/build?idx=' + sel.value).then(function(r){ return r.text(); }).then(function(html){ document.getElementById('buildTable').innerHTML = html; }); }
    sel.onchange = loadBuild;
    loadBuild();
  } else if (tab === 'test') {
    content.innerHTML = '<label>选择表：<select id="testSelect"><option value="0">01_y_and_implication（预览）</option><option value="1">03_regression_fusion_implication（单因子汇总）</option></select></label><div id="testTable"></div>';
    var sel = document.getElementById('testSelect');
    function loadTest(){ fetch('/api/test?idx=' + sel.value).then(function(r){ return r.text(); }).then(function(html){ document.getElementById('testTable').innerHTML = html; }); }
    sel.onchange = loadTest;
    loadTest();
  } else if (tab === 'charts') {
    content.innerHTML = '<div class="charts-layout"><div class="charts-side"><h3>因子文件夹</h3><ul id="chartFolders"></ul><h3>图片</h3><ul id="chartImages"></ul></div><div class="charts-main"><img id="chartImg" src="" alt="选择左侧图片" style="max-width:100%"></div></div>';
    var foldersUl = document.getElementById('chartFolders');
    var imagesUl = document.getElementById('chartImages');
    var imgEl = document.getElementById('chartImg');
    fetch('/api/chart_folders').then(function(r){ return r.json(); }).then(function(arr){
      foldersUl.innerHTML = '';
      arr.forEach(function(name){
        var li = document.createElement('li');
        li.textContent = name;
        li.dataset.folder = name;
        li.onclick = function(){ document.querySelectorAll('#chartFolders li').forEach(function(l){ l.classList.remove('selected'); }); this.classList.add('selected'); loadImages(this.dataset.folder); };
        foldersUl.appendChild(li);
      });
      if (arr.length) { foldersUl.firstChild.click(); }
    });
    function loadImages(folder){
      fetch('/api/chart_images?folder=' + encodeURIComponent(folder)).then(function(r){ return r.json(); }).then(function(arr){
        imagesUl.innerHTML = '';
        arr.forEach(function(name){
          var li = document.createElement('li');
          li.textContent = name;
          li.dataset.folder = folder;
          li.dataset.file = name;
          li.onclick = function(){ imgEl.src = '/api/chart_image?folder=' + encodeURIComponent(this.dataset.folder) + '&file=' + encodeURIComponent(this.dataset.file); document.querySelectorAll('#chartImages li').forEach(function(l){ l.classList.remove('selected'); }); this.classList.add('selected'); };
          imagesUl.appendChild(li);
        });
      });
    }
  } else if (tab === 'config') {
    fetch('/api/config').then(function(r){ return r.text(); }).then(function(html){ content.innerHTML = html; });
  }
}
document.querySelectorAll('.tabs button').forEach(function(b){
  b.onclick = function(){ show(b.dataset.tab); };
});
show('overview');
</script>
</body>
</html>'''

    def _overview_html(self, root, fb_out, ft_out, plots_base):
        lines = [
            '<pre>',
            '项目根目录: ' + html.escape(root),
            'factor_build 输出: ' + html.escape(fb_out),
            'factor_test 输出: ' + html.escape(ft_out),
            '',
            '【factor_build/outputs】',
        ]
        for name, desc in [
            ('01_y_timeseries.xlsx', '大盘减小盘 y 时序'),
            ('02_relative_factors_timeseries.xlsx', '相对因子时序（多 sheet）'),
            ('03_regression_results.xlsx', '回归结果与显著因子'),
            ('04_fusion_timeseries.xlsx', '融合因子时序'),
            ('04_fusion_constituents.xlsx', '融合成分'),
        ]:
            path = os.path.join(fb_out, name)
            status = '✓ 存在' if os.path.isfile(path) else '✗ 缺失'
            lines.append('  {}  {}  — {}'.format(status, name, desc))
        lines.extend(['', '【factor_test/outputs】'])
        for name, desc in [
            ('01_y_and_implication.xlsx', 'y + 股债/波动率等指标'),
            ('02_factor_plots/', '因子折线图与 event 图'),
            ('03_regression_fusion_implication.xlsx', 'fusion 单因子回归汇总'),
        ]:
            path = os.path.join(ft_out, name.rstrip('/'))
            status = '✓ 存在' if (os.path.isdir(path) if name.endswith('/') else os.path.isfile(path)) else '✗ 缺失'
            lines.append('  {}  {}  — {}'.format(status, name, desc))
        if os.path.isdir(plots_base):
            sub = safe_listdir(plots_base)
            sub = [s for s in sub if os.path.isdir(os.path.join(plots_base, s))]
            lines.append('  子文件夹: ' + ', '.join(sub[:20]) + (' ...' if len(sub) > 20 else ''))
        lines.append('</pre>')
        return '\n'.join(lines)

    def _build_table_html(self, fb_out, idx):
        if idx == 0:
            df, err = safe_read_excel(os.path.join(fb_out, '01_y_timeseries.xlsx'), max_rows=200)
        elif idx == 1:
            df, err = safe_read_excel(os.path.join(fb_out, '03_regression_results.xlsx'), sheet_name=0, max_rows=300)
        elif idx == 2:
            path = os.path.join(fb_out, '03_regression_results.xlsx')
            try:
                sheets = pd.ExcelFile(path).sheet_names if os.path.isfile(path) else []
                sn = 'significant' if 'significant' in sheets else ('显著' if any('显著' in s for s in sheets) else 1)
                df, err = safe_read_excel(path, sheet_name=sn if isinstance(sn, str) else 1, max_rows=100)
            except Exception:
                df, err = None, '无法读取'
        elif idx == 3:
            df, err = safe_read_excel(os.path.join(fb_out, '04_fusion_constituents.xlsx'), max_rows=50)
        else:
            df, err = safe_read_excel(os.path.join(fb_out, '04_fusion_timeseries.xlsx'), max_rows=200)
        return df_to_html_table(df, err)

    def _test_table_html(self, ft_out, idx):
        if idx == 0:
            df, err = safe_read_excel(os.path.join(ft_out, '01_y_and_implication.xlsx'), max_rows=200)
        else:
            path = os.path.join(ft_out, '03_regression_fusion_implication.xlsx')
            df, err = safe_read_excel(path, sheet_name='单因子回归汇总', max_rows=20)
            if err and os.path.isfile(path):
                df, err = safe_read_excel(path, sheet_name=0, max_rows=20)
        return df_to_html_table(df, err)

    def _config_html(self, root, fb_out, ft_out, plots_base):
        lines = [
            '<pre>',
            '项目根: ' + html.escape(root),
            'factor_build 输出: ' + html.escape(fb_out),
            'factor_test 输出: ' + html.escape(ft_out),
            '图表目录: ' + html.escape(plots_base),
            '',
        ]
        if config is not None:
            lines.append('MARK_DATES (国家队出手公告日):')
            for d in getattr(config, 'MARK_DATES', []):
                lines.append('  ' + str(d))
            lines.extend([
                '',
                'ROLLING_ZSCORE_WINDOW: ' + str(getattr(config, 'ROLLING_ZSCORE_WINDOW', '')),
                'FUSION_LAG_ALLOWED: ' + str(getattr(config, 'FUSION_LAG_ALLOWED', '')),
                'REGRESSION_MAX_PVALUE: ' + str(getattr(config, 'REGRESSION_MAX_PVALUE', '')),
            ])
        else:
            lines.append('(未加载 config)')
        lines.append('</pre>')
        return '\n'.join(lines)

    def _chart_folders(self, plots_base):
        if not os.path.isdir(plots_base):
            return []
        return [n for n in safe_listdir(plots_base) if os.path.isdir(os.path.join(plots_base, n))]

    def _chart_images(self, plots_base, folder):
        if not folder:
            return []
        path = os.path.join(plots_base, folder)
        if not os.path.isdir(path):
            return []
        return [f for f in safe_listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    def log_message(self, format, *args):
        print("[%s] %s" % (self.log_date_time_string(), format % args))


def run(port=8765, open_browser=True):
    init_paths()
    server = HTTPServer(('127.0.0.1', port), Handler)
    url = 'http://127.0.0.1:%s/' % port
    print('因子展示 Web 已启动: %s' % url)
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
    finally:
        server.server_close()


if __name__ == '__main__':
    import sys
    port = 8765
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port=port)
