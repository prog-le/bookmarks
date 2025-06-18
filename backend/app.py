import os
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from lxml import etree
import chardet
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
import re
from collections import defaultdict
import requests
from lxml import etree as letree
from flask_socketio import SocketIO, emit
import eventlet

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/api/upload', methods=['POST'])
def upload_bookmark():
    # 处理上传的书签文件
    file = request.files.get('file')
    if not file:
        return jsonify({'error': '未检测到文件'}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    # TODO: 解析书签并返回初步分类结果
    return jsonify({'message': '上传成功', 'filename': filename})

@app.route('/api/parse', methods=['POST'])
def parse_bookmark():
    # 解析HTML书签，返回结构化数据
    data = request.json
    filename = data.get('filename')
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': '文件不存在'}), 404
    # 自动检测编码
    with open(filepath, 'rb') as f:
        raw = f.read()
        try:
            html = raw.decode('utf-8')
        except UnicodeDecodeError:
            # 如果极少数不是utf-8，再用chardet兜底
            import chardet
            result = chardet.detect(raw)
            encoding = result['encoding'] or 'utf-8'
            html = raw.decode(encoding, errors='replace')
    # 解析HTML
    parser = etree.HTMLParser()
    tree = etree.HTML(html, parser)
    bookmarks = []
    def walk(node, folder_path):
        for elem in node:
            # 1. 书签
            if elem.tag == 'a':
                bookmarks.append({
                    'title': elem.text or '',
                    'url': elem.get('href', ''),
                    'add_date': elem.get('add_date', ''),
                    'folder': folder_path[-1] if folder_path else '',
                    'folders': folder_path,
                })
            # 2. 文件夹
            elif elem.tag == 'h3':
                folder = elem.text or ''
                # 下一个兄弟节点如果是DL，递归
                next_dl = None
                for sib in elem.itersiblings():
                    if sib.tag == 'dl':
                        next_dl = sib
                        break
                if next_dl is not None:
                    walk(next_dl, folder_path + [folder])
            # 3. 递归所有DL
            elif elem.tag == 'dl':
                walk(elem, folder_path)
            # 4. 递归所有子节点
            else:
                walk(elem, folder_path)
    # 从根节点递归
    roots = tree.xpath('//dl')
    if roots:
        walk(roots[0], [])
    return jsonify({'bookmarks': bookmarks})

@app.route('/api/classify', methods=['POST'])
def classify_bookmark():
    # 智能分类接口
    data = request.json
    bookmarks = data.get('bookmarks', [])
    method = data.get('method', 'keyword')
    # 1. 关键词规则分类
    if method == 'keyword':
        default_categories = {
            '技术': ['github', 'gitlab', 'csdn', 'stackoverflow', 'python', 'java', '编程', '开发', '技术', '代码', 'gitee', 'v2ex', 'segmentfault'],
            '娱乐': ['bilibili', 'b站', 'acfun', '抖音', '快手', '音乐', '视频', '娱乐', '游戏', '动漫'],
            '学习': ['mooc', '慕课', 'coursera', 'edx', '学习', '教程', 'w3school', 'edu', '大学', '知乎', 'wikipedia', '百科'],
            '新闻': ['news', '新闻', '头条', '网易', '新浪', '搜狐', '腾讯', 'bbc', 'cnn', '日报', '报纸'],
            '购物': ['淘宝', '京东', '拼多多', '购物', '商城', '亚马逊', 'aliexpress', 'ebay'],
            '生活': ['美食', '健康', '旅游', '出行', '天气', '生活', '家居', '房产', '汽车'],
            '社交': ['微博', '微信', 'qq', 'facebook', 'twitter', 'instagram', '社交', '论坛', '社区'],
        }
        custom_categories = data.get('categories', {})
        categories = default_categories.copy()
        categories.update(custom_categories)
        def match_category(bm):
            text = (bm.get('title', '') + ' ' + bm.get('url', '')).lower()
            for cat, keywords in categories.items():
                for kw in keywords:
                    if kw.lower() in text:
                        return cat
            return '未分类'
        for bm in bookmarks:
            bm['category'] = match_category(bm)
        # TF-IDF补充未分类
        unclassified = [bm for bm in bookmarks if bm['category'] == '未分类']
        if unclassified and len(unclassified) > 2:
            docs = [bm['title'] + ' ' + bm['url'] for bm in unclassified]
            vectorizer = TfidfVectorizer(max_features=10)
            X = vectorizer.fit_transform(docs)
            terms = vectorizer.get_feature_names_out()
            for i, bm in enumerate(unclassified):
                tfidf = X[i].toarray()[0]
                if tfidf.max() > 0:
                    idx = tfidf.argmax()
                    bm['category'] = '其他-' + terms[idx]
        return jsonify({'classified': bookmarks})
    # 2. TF-IDF语义聚类（简单实现：按主成分分组）
    elif method == 'tfidf':
        docs = [bm['title'] + ' ' + bm['url'] for bm in bookmarks]
        vectorizer = TfidfVectorizer(max_features=10)
        X = vectorizer.fit_transform(docs)
        terms = vectorizer.get_feature_names_out()
        for i, bm in enumerate(bookmarks):
            tfidf = X[i].toarray()[0]
            if tfidf.max() > 0:
                idx = tfidf.argmax()
                bm['category'] = terms[idx]
            else:
                bm['category'] = '未分类'
        return jsonify({'classified': bookmarks})
    # 3. 原始文件夹结构分类
    elif method == 'folder':
        for bm in bookmarks:
            bm['category'] = bm.get('folder', '未分类') or '未分类'
        return jsonify({'classified': bookmarks})
    # 4. 按域名分类
    elif method == 'domain':
        def extract_domain(url):
            if not url:
                return '无域名'
            m = re.match(r'https?://([^/]+)', url)
            if m:
                return m.group(1)
            return '无域名'
        for bm in bookmarks:
            bm['category'] = extract_domain(bm.get('url', ''))
        return jsonify({'classified': bookmarks})
    # 5. 智能关键词分类（实时抓取网页标题）
    elif method == 'smart_keyword':
        logs = []
        def log(msg):
            print(msg)
            logs.append(msg)
        default_categories = {
            '技术': ['github', 'gitlab', 'csdn', 'stackoverflow', 'python', 'java', '编程', '开发', '技术', '代码', 'gitee', 'v2ex', 'segmentfault'],
            '娱乐': ['bilibili', 'b站', 'acfun', '抖音', '快手', '音乐', '视频', '娱乐', '游戏', '动漫'],
            '学习': ['mooc', '慕课', 'coursera', 'edx', '学习', '教程', 'w3school', 'edu', '大学', '知乎', 'wikipedia', '百科'],
            '新闻': ['news', '新闻', '头条', '网易', '新浪', '搜狐', '腾讯', 'bbc', 'cnn', '日报', '报纸'],
            '购物': ['淘宝', '京东', '拼多多', '购物', '商城', '亚马逊', 'aliexpress', 'ebay'],
            '生活': ['美食', '健康', '旅游', '出行', '天气', '生活', '家居', '房产', '汽车'],
            '社交': ['微博', '微信', 'qq', 'facebook', 'twitter', 'instagram', '社交', '论坛', '社区'],
        }
        custom_categories = data.get('categories', {})
        categories = default_categories.copy()
        categories.update(custom_categories)
        def match_category(bm):
            text = (bm.get('title', '') + ' ' + bm.get('url', '')).lower()
            for cat, keywords in categories.items():
                for kw in keywords:
                    if kw.lower() in text:
                        return cat
            return '未分类'
        def fetch_title(url):
            try:
                log(f"[智能抓取] 正在请求: {url}")
                resp = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
                resp.encoding = resp.apparent_encoding
                html = resp.text
                tree = letree.HTML(html)
                title = tree.findtext('.//title')
                if title:
                    log(f"[智能抓取] 成功: {url} -> {title.strip()}")
                    return title.strip()
                else:
                    log(f"[智能抓取] 失败: {url} 未找到<title>")
            except Exception as e:
                log(f"[智能抓取] 失败: {url} 错误: {e}")
            return None
        for bm in bookmarks:
            real_title = fetch_title(bm.get('url', ''))
            if real_title:
                bm['title'] = real_title
            bm['category'] = match_category(bm)
        return jsonify({'classified': bookmarks, 'logs': logs})
    else:
        return jsonify({'classified': bookmarks})

@app.route('/api/export', methods=['POST'])
def export_bookmark():
    # 导出分类后的书签为HTML
    data = request.json
    bookmarks = data.get('bookmarks', [])
    # 按分类分组
    category_map = defaultdict(list)
    for bm in bookmarks:
        cat = bm.get('category', '未分类') or '未分类'
        category_map[cat].append(bm)
    # 生成HTML
    export_path = os.path.join(UPLOAD_FOLDER, 'exported_bookmarks.html')
    with open(export_path, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE NETSCAPE-Bookmark-file-1>\n')
        f.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n')
        f.write('<TITLE>分类书签</TITLE>\n')
        f.write('<H1>分类书签</H1>\n')
        for cat, items in category_map.items():
            f.write(f'<DT><H3>{cat}</H3>\n')
            f.write('<DL><p>\n')
            for bm in items:
                f.write(f'<DT><A HREF="{bm["url"]}" ADD_DATE="{bm.get("add_date", "")}">{bm["title"]}</A>\n')
            f.write('</DL><p>\n')
    return send_file(export_path, as_attachment=True)

@app.route('/api/classify_stream', methods=['GET'])
def classify_bookmark_stream():
    import json
    from urllib.parse import unquote
    bookmarks = json.loads(unquote(request.args.get('bookmarks', '[]')))
    method = request.args.get('method', 'smart_keyword')
    if method != 'smart_keyword':
        return jsonify({'error': '仅支持智能关键词分类流式日志'}), 400
    def event_stream():
        default_categories = {
            '技术': ['github', 'gitlab', 'csdn', 'stackoverflow', 'python', 'java', '编程', '开发', '技术', '代码', 'gitee', 'v2ex', 'segmentfault'],
            '娱乐': ['bilibili', 'b站', 'acfun', '抖音', '快手', '音乐', '视频', '娱乐', '游戏', '动漫'],
            '学习': ['mooc', '慕课', 'coursera', 'edx', '学习', '教程', 'w3school', 'edu', '大学', '知乎', 'wikipedia', '百科'],
            '新闻': ['news', '新闻', '头条', '网易', '新浪', '搜狐', '腾讯', 'bbc', 'cnn', '日报', '报纸'],
            '购物': ['淘宝', '京东', '拼多多', '购物', '商城', '亚马逊', 'aliexpress', 'ebay'],
            '生活': ['美食', '健康', '旅游', '出行', '天气', '生活', '家居', '房产', '汽车'],
            '社交': ['微博', '微信', 'qq', 'facebook', 'twitter', 'instagram', '社交', '论坛', '社区'],
        }
        custom_categories = json.loads(unquote(request.args.get('categories', '{}')))
        categories = default_categories.copy()
        categories.update(custom_categories)
        def match_category(bm):
            text = (bm.get('title', '') + ' ' + bm.get('url', '')).lower()
            for cat, keywords in categories.items():
                for kw in keywords:
                    if kw.lower() in text:
                        return cat
            return '未分类'
        for bm in bookmarks:
            url = bm.get('url', '')
            try:
                msg = f"[智能抓取] 正在请求: {url}"
                yield f"data: {json.dumps({'log': msg})}\n\n"
                resp = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
                resp.encoding = resp.apparent_encoding
                html = resp.text
                tree = letree.HTML(html)
                title = tree.findtext('.//title')
                if title:
                    real_title = title.strip()
                    msg = f"[智能抓取] 成功: {url} -> {real_title}"
                    bm['title'] = real_title
                    yield f"data: {json.dumps({'log': msg})}\n\n"
                else:
                    msg = f"[智能抓取] 失败: {url} 未找到<title>"
                    yield f"data: {json.dumps({'log': msg})}\n\n"
            except Exception as e:
                msg = f"[智能抓取] 失败: {url} 错误: {e}"
                yield f"data: {json.dumps({'log': msg})}\n\n"
            bm['category'] = match_category(bm)
        # 推送最终结果
        yield f"data: {json.dumps({'result': bookmarks})}\n\n"
    return Response(event_stream(), mimetype='text/event-stream')

@socketio.on('smart_keyword_classify')
def handle_smart_keyword_classify(data):
    bookmarks = data.get('bookmarks', [])
    default_categories = {
        '技术': ['github', 'gitlab', 'csdn', 'stackoverflow', 'python', 'java', '编程', '开发', '技术', '代码', 'gitee', 'v2ex', 'segmentfault'],
        '娱乐': ['bilibili', 'b站', 'acfun', '抖音', '快手', '音乐', '视频', '娱乐', '游戏', '动漫'],
        '学习': ['mooc', '慕课', 'coursera', 'edx', '学习', '教程', 'w3school', 'edu', '大学', '知乎', 'wikipedia', '百科'],
        '新闻': ['news', '新闻', '头条', '网易', '新浪', '搜狐', '腾讯', 'bbc', 'cnn', '日报', '报纸'],
        '购物': ['淘宝', '京东', '拼多多', '购物', '商城', '亚马逊', 'aliexpress', 'ebay'],
        '生活': ['美食', '健康', '旅游', '出行', '天气', '生活', '家居', '房产', '汽车'],
        '社交': ['微博', '微信', 'qq', 'facebook', 'twitter', 'instagram', '社交', '论坛', '社区'],
    }
    custom_categories = data.get('categories', {})
    categories = default_categories.copy()
    categories.update(custom_categories)
    def match_category(bm):
        if bm.get('category') in ['无法识别', '没有标题']:
            return bm['category']
        text = (bm.get('title', '') + ' ' + bm.get('url', '')).lower()
        for cat, keywords in categories.items():
            for kw in keywords:
                if kw.lower() in text:
                    return cat
        return '未分类'
    for bm in bookmarks:
        url = bm.get('url', '')
        try:
            msg = f"[智能抓取] 正在请求: {url}"
            emit('smart_keyword_log', {'log': msg})
            resp = requests.get(url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
            resp.encoding = resp.apparent_encoding
            html = resp.text
            tree = letree.HTML(html)
            title = tree.findtext('.//title')
            if title is not None:
                real_title = title.strip()
                if real_title:
                    msg = f"[智能抓取] 成功: {url} -> {real_title}"
                    bm['title'] = real_title
                    emit('smart_keyword_log', {'log': msg})
                else:
                    msg = f"[智能抓取] 失败: {url} <title>为空"
                    emit('smart_keyword_log', {'log': msg})
                    bm['category'] = '没有标题'
            else:
                msg = f"[智能抓取] 失败: {url} 未找到<title>"
                emit('smart_keyword_log', {'log': msg})
                bm['category'] = '没有标题'
        except Exception as e:
            msg = f"[智能抓取] 失败: {url} 错误: {e}"
            emit('smart_keyword_log', {'log': msg})
            bm['category'] = '无法识别'
        if 'category' not in bm:
            bm['category'] = match_category(bm)
        eventlet.sleep(0)  # 让出控制权，保证实时推送
    emit('smart_keyword_result', {'result': bookmarks})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000) 