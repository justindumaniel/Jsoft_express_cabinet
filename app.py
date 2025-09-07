from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import json
import hashlib
import random
import string
from datetime import datetime, timedelta
import shutil
import urllib.parse

app = Flask(__name__, static_folder='.', static_url_path='/')
app.secret_key = ''.join(random.choices(string.ascii_letters + string.digits, k=24))

# 配置
UPLOAD_FOLDER = './uploads'
ADMIN_CONFIG_FILE = './js/all/adminset.json'
FILE_DATA_FILE = './js/all/files_data.json'
DEFAULT_MAX_FILE_SIZE_MB = 50

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('./js/all', exist_ok=True)

# 检查是否已初始化
def check_initialized():
    return os.path.exists(ADMIN_CONFIG_FILE)

# 读取管理员配置
def read_admin_config():
    if check_initialized():
        with open(ADMIN_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 确保配置文件包含所有必要字段
            if 'max_file_size' not in config:
                config['max_file_size'] = DEFAULT_MAX_FILE_SIZE_MB
            if 'announcement' not in config:
                config['announcement'] = ''
            save_admin_config(config)
            return config
    return None

# 保存管理员配置
def save_admin_config(config):
    with open(ADMIN_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# 获取当前最大文件大小（MB）
def get_max_file_size():
    config = read_admin_config()
    if config and 'max_file_size' in config:
        return config['max_file_size']
    return DEFAULT_MAX_FILE_SIZE_MB

# 获取当前公告
def get_announcement():
    config = read_admin_config()
    if config and 'announcement' in config:
        return config['announcement']
    return ''

# 读取文件数据
def read_file_data():
    if os.path.exists(FILE_DATA_FILE):
        with open(FILE_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 保存文件数据
def save_file_data(data):
    with open(FILE_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 生成随机4位数取件码(1000-9999)
def generate_code():
    file_data = read_file_data()
    while True:
        code = str(random.randint(1000, 9999))
        if code not in file_data:
            return code

# 检查文件是否过期
def check_expired_files():
    file_data = read_file_data()
    current_time = datetime.now().timestamp()
    expired_codes = []
    
    for code, info in file_data.items():
        if current_time > info['expire_time']:
            # 删除文件
            if os.path.exists(info['file_path']):
                try:
                    os.remove(info['file_path'])
                except:
                    pass
            expired_codes.append(code)
    
    # 移除过期记录
    for code in expired_codes:
        del file_data[code]
    
    if expired_codes:
        save_file_data(file_data)

# 首页路由
@app.route('/')
def index():
    # 检查是否需要初始化
    if not check_initialized():
        return redirect(url_for('initialize'))
    
    # 检查并清理过期文件
    check_expired_files()
    
    return app.send_static_file('index.html')

# 初始化路由
@app.route('/initialize', methods=['GET', 'POST'])
def initialize():
    if check_initialized():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        if password:
            # MD5加密密码
            md5_password = hashlib.md5(password.encode()).hexdigest()
            # 创建包含所有必要字段的配置
            save_admin_config({
                'password': md5_password,
                'max_file_size': DEFAULT_MAX_FILE_SIZE_MB,
                'announcement': ''
            })
            # 创建空的文件数据文件
            save_file_data({})
            return redirect(url_for('index'))
    
    return render_template('initialize.html')

# 管理员登录路由
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if not check_initialized():
        return redirect(url_for('initialize'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        admin_config = read_admin_config()
        
        if admin_config and hashlib.md5(password.encode()).hexdigest() == admin_config['password']:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error='密码错误')
    
    return render_template('admin_login.html')

# 管理员面板路由
@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # 检查并清理过期文件
    check_expired_files()
    
    # 获取文件数据
    file_data = read_file_data()
    
    # 格式化过期时间
    for code, info in file_data.items():
        expire_time = datetime.fromtimestamp(info['expire_time'])
        info['formatted_expire_time'] = expire_time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 获取当前设置
    max_file_size = get_max_file_size()
    announcement = get_announcement()
    
    return render_template('admin_panel.html', files=file_data, max_file_size=max_file_size, announcement=announcement)

# 管理员登出路由
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

# 删除文件路由
@app.route('/admin/delete_file/<code>')
def delete_file(code):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    file_data = read_file_data()
    if code in file_data:
        # 删除文件
        if os.path.exists(file_data[code]['file_path']):
            try:
                os.remove(file_data[code]['file_path'])
            except:
                pass
        # 删除记录
        del file_data[code]
        save_file_data(file_data)
    
    return redirect(url_for('admin_panel'))

# 修改过期时间路由
@app.route('/admin/update_expire/<code>', methods=['POST'])
def update_expire(code):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    hours = request.form.get('hours', type=int)
    if hours and hours > 0:
        file_data = read_file_data()
        if code in file_data:
            new_expire_time = (datetime.now() + timedelta(hours=hours)).timestamp()
            file_data[code]['expire_time'] = new_expire_time
            file_data[code]['expire_hours'] = hours
            save_file_data(file_data)
    
    return redirect(url_for('admin_panel'))

# 上传页面路由
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not check_initialized():
        return redirect(url_for('initialize'))
    
    # 获取当前最大文件大小
    max_file_size_mb = get_max_file_size()
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    
    if request.method == 'POST':
        # 检查是否有文件上传
        if 'file' not in request.files:
            return render_template('upload.html', error='请选择要上传的文件')
        
        file = request.files['file']
        if file.filename == '':
            return render_template('upload.html', error='请选择要上传的文件')
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 移回文件开头
        
        if file_size > max_file_size_bytes:
            return render_template('upload.html', error=f'文件大小不能超过{max_file_size_mb}MB')
        
        # 获取有效期
        expire_hours = request.form.get('expire_hours', type=int)
        if not expire_hours or expire_hours not in [1, 3, 10, 24]:
            return render_template('upload.html', error='请选择有效的有效期')
        
        # 生成取件码
        code = generate_code()
        
        # 保存文件
        filename = f'{code}_{file.filename}'
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # 计算过期时间
        expire_time = (datetime.now() + timedelta(hours=expire_hours)).timestamp()
        
        # 保存文件信息
        file_data = read_file_data()
        file_data[code] = {
            'file_path': file_path,
            'original_filename': file.filename,
            'upload_time': datetime.now().timestamp(),
            'expire_time': expire_time,
            'expire_hours': expire_hours,
            'size': file_size
        }
        save_file_data(file_data)
        
        return render_template('upload.html', success=True, code=code)
    
    return render_template('upload.html')


# 更新管理员设置路由
@app.route('/admin/update_settings', methods=['POST'])
def update_admin_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    admin_config = read_admin_config()
    if not admin_config:
        return redirect(url_for('admin_login'))
    
    error = None
    success = None
    
    # 获取表单数据
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    max_file_size = request.form.get('max_file_size', type=int)
    announcement = request.form.get('announcement', '')
    
    # 处理密码修改
    if current_password or new_password or confirm_password:
        # 检查当前密码是否正确
        if not current_password:
            error = '请输入当前密码'
        elif hashlib.md5(current_password.encode()).hexdigest() != admin_config['password']:
            error = '当前密码错误'
        elif not new_password:
            error = '请输入新密码'
        elif new_password != confirm_password:
            error = '两次输入的新密码不一致'
        else:
            # 更新密码
            admin_config['password'] = hashlib.md5(new_password.encode()).hexdigest()
            success = '密码更新成功'
    
    # 处理最大文件大小修改
    if max_file_size is not None:
        if max_file_size < 1 or max_file_size > 1024:
            error = error or '最大文件大小必须在1-1024MB之间'
        else:
            admin_config['max_file_size'] = max_file_size
            if not error:
                success = success or '设置更新成功'
    
    # 处理公告修改
    admin_config['announcement'] = announcement
    
    # 处理背景图上传
    if 'background_image' in request.files:
        background_image = request.files['background_image']
        if background_image and background_image.filename:
            # 检查文件类型
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
            file_ext = background_image.filename.rsplit('.', 1)[1].lower() if '.' in background_image.filename else ''
            if file_ext not in allowed_extensions:
                error = error or '不支持的图片格式，请上传PNG、JPG、JPEG、GIF或BMP格式的图片'
            else:
                try:
                    # 确保背景图目录存在
                    bg_dir = os.path.join(app.root_path, 'css', 'all')
                    if not os.path.exists(bg_dir):
                        os.makedirs(bg_dir)
                    
                    # 保存上传的背景图，替换现有的bg.png
                    bg_path = os.path.join(bg_dir, 'bg.png')
                    # 读取上传的图片并转换为PNG格式保存
                    from PIL import Image
                    with Image.open(background_image) as img:
                        # 确保图片尺寸合理
                        max_size = (2560, 1440)  # 最大尺寸限制
                        img.thumbnail(max_size, Image.LANCZOS)
                        img.save(bg_path, 'PNG')
                    
                    success = '背景图更新成功' if not success else success
                except Exception as e:
                    error = error or f'上传背景图时出错: {str(e)}'
    
    # 保存配置
    if not error:
        save_admin_config(admin_config)
        
    # 重新获取文件数据和设置
    check_expired_files()
    file_data = read_file_data()
    
    for code, info in file_data.items():
        expire_time = datetime.fromtimestamp(info['expire_time'])
        info['formatted_expire_time'] = expire_time.strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('admin_panel.html', 
                          files=file_data, 
                          max_file_size=admin_config['max_file_size'], 
                          announcement=admin_config['announcement'],
                          error=error,
                          success=success)

# 验证取件码路由
@app.route('/verify_code')
def verify_code():
    if not check_initialized():
        return redirect(url_for('initialize'))
    
    code = request.args.get('code')
    file_data = read_file_data()
    
    if code in file_data:
        # 检查文件是否过期
        current_time = datetime.now().timestamp()
        if current_time > file_data[code]['expire_time']:
            # 删除过期文件
            if os.path.exists(file_data[code]['file_path']):
                try:
                    os.remove(file_data[code]['file_path'])
                except:
                    pass
            del file_data[code]
            save_file_data(file_data)
            return jsonify({'exists': False, 'message': '文件已过期'})
        
        return jsonify({
            'exists': True,
            'filename': file_data[code]['original_filename']
        })
    else:
        return jsonify({'exists': False, 'message': '取件码不存在'})

# 下载文件路由
@app.route('/download')
def download_file():
    if not check_initialized():
        return redirect(url_for('initialize'))
    
    # 获取更新后的防二次下载取件码
    new_code = request.args.get('new_code')
    file_data = read_file_data()
    
    if new_code in file_data:
        file_path = file_data[new_code]['file_path']
        original_filename = file_data[new_code]['original_filename']
        
        # 检查文件是否存在
        if os.path.exists(file_path):
            # 发送文件供下载
            try:
                # 对中文文件名进行url编码，确保HTTP响应头正确
                encoded_filename = urllib.parse.quote(original_filename)
                
                # 返回文件供下载
                return app.response_class(
                    open(file_path, 'rb').read(),
                    mimetype='application/octet-stream',
                    headers={
                        # 使用filename*参数支持UTF-8编码的文件名
                        'Content-Disposition': f'attachment; filename="{encoded_filename}"; filename*=UTF-8''{encoded_filename}',
                        'Content-Length': str(os.path.getsize(file_path))
                    }
                )
            except Exception as e:
                print(f"下载文件时出错: {e}")
                return jsonify({'success': False, 'message': '下载文件时出错'})
        else:
            # 文件不存在，清理记录
            del file_data[new_code]
            save_file_data(file_data)
            return jsonify({'success': False, 'message': '文件不存在'})
    else:
        return jsonify({'success': False, 'message': '更新后的取件码无效'})

# 更新取件码和有效期路由
@app.route('/update_code_and_expiry', methods=['POST'])
def update_code_and_expiry():
    if not check_initialized():
        return redirect(url_for('initialize'))
    
    data = request.get_json()
    old_code = data.get('old_code')
    
    if old_code:
        file_data = read_file_data()
        if old_code in file_data:
            # 保存文件信息
            file_info = file_data[old_code]
            
            # 生成新的取件码
            new_code = str(random.randint(10000, 99999))
            while new_code in file_data:
                new_code = str(random.randint(10000, 99999))
            
            # 更新有效期为10分钟
            new_expire_time = (datetime.now() + timedelta(minutes=10)).timestamp()
            file_info['expire_time'] = new_expire_time
            file_info['expire_hours'] = 10/60  # 转换为小时
            
            # 删除旧记录，添加新记录
            del file_data[old_code]
            file_data[new_code] = file_info
            
            # 重命名文件
            if os.path.exists(file_info['file_path']):
                try:
                    new_file_path = file_info['file_path'].replace(old_code, new_code, 1)
                    os.rename(file_info['file_path'], new_file_path)
                    file_info['file_path'] = new_file_path
                    file_data[new_code] = file_info
                    save_file_data(file_data)
                except Exception as e:
                    print(f"重命名文件时出错: {e}")
                    # 即使重命名失败，也要更新数据库
                    save_file_data(file_data)
            else:
                save_file_data(file_data)
            
            return jsonify({'success': True, 'new_code': new_code})
        else:
            return jsonify({'success': False, 'message': '取件码不存在'})
    else:
        return jsonify({'success': False, 'message': '参数错误'})

# 获取管理员配置
@app.route('/read_admin_config', methods=['GET'])
def read_admin_config_route():
    config = read_admin_config()
    return jsonify(config)

# 获取公告内容
@app.route('/get_announcement', methods=['GET'])
def get_announcement_route():
    config = read_admin_config()
    announcement = config.get('announcement', '')
    return jsonify({'announcement': announcement})

def create_template_files(template_folder):
    # initialize.html
    with open(os.path.join(template_folder, 'initialize.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>快递柜初始化</title>
    <link rel="icon" href="/css/all/Jsoft_logo.png" type="image/png">
    <link rel="stylesheet" href="/css/index/style.css">
    <style>
        .box {
            max-width: 400px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 16px;
            color: #333;
        }
        .form-group input {
            width: 100%;
            height: 45px;
            padding: 0 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus {
            outline: none;
            border-color: #2196F3;
        }
        .btn {
            width: 100%;
            height: 50px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .btn:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="box">
            <h2>快递柜初始化</h2>
            <form method="post">
                <div class="form-group">
                    <label for="password">设置管理员密码</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="btn">确认</button>
            </form>
        </div>
    </div>
</body>
</html>''')
    
    # admin_login.html
    with open(os.path.join(template_folder, 'admin_login.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理员登录</title>
    <link rel="icon" href="/css/all/Jsoft_logo.png" type="image/png">
    <link rel="stylesheet" href="/css/index/style.css">
    <style>
        .box {
            max-width: 400px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 16px;
            color: #333;
        }
        .form-group input {
            width: 100%;
            height: 45px;
            padding: 0 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus {
            outline: none;
            border-color: #2196F3;
        }
        .btn {
            width: 100%;
            height: 50px;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .btn:hover {
            background-color: #1976D2;
        }
        .error {
            color: #f44336;
            margin-bottom: 15px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="box">
            <h2>管理员登录</h2>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
            <form method="post">
                <div class="form-group">
                    <label for="password">输入管理员密码</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="btn">登录</button>
            </form>
        </div>
    </div>
</body>
</html>''')
    
    # admin_panel.html
    with open(os.path.join(template_folder, 'admin_panel.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>管理员面板</title>
    <link rel="icon" href="/css/all/Jsoft_logo.png" type="image/png">
    <link rel="stylesheet" href="/css/index/style.css">
    <style>
        .box {
            max-width: 800px;
            width: 90%;
        }
        .logout-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 8px 16px;
            background-color: #f44336;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background-color 0.3s ease;
        }
        .logout-btn:hover {
            background-color: #d32f2f;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: rgba(255, 255, 255, 0.5);
            font-weight: bold;
        }
        tr:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }
        .action-btn {
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            transition: background-color 0.3s ease;
        }
        .delete-btn {
            background-color: #f44336;
            color: white;
        }
        .delete-btn:hover {
            background-color: #d32f2f;
        }
        .update-btn {
            background-color: #2196F3;
            color: white;
        }
        .update-btn:hover {
            background-color: #1976D2;
        }
        .no-files {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .expire-form {
            display: inline-block;
        }
        .expire-select {
            padding: 3px 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <a href="{{ url_for('admin_logout') }}"><button class="logout-btn">退出登录</button></a>
    <div class="container">
        <div class="box">
            <h2>文件管理</h2>
            {% if files %}
                <table>
                    <tr>
                        <th>取件码</th>
                        <th>文件名</th>
                        <th>大小</th>
                        <th>过期时间</th>
                        <th>操作</th>
                    </tr>
                    {% for code, info in files.items() %}
                        <tr>
                            <td>{{ code }}</td>
                            <td>{{ info.original_filename }}</td>
                            <td>{{ "%.2f MB"|format(info.size / (1024 * 1024)) }}</td>
                            <td>{{ info.formatted_expire_time }}</td>
                            <td>
                                <form class="expire-form" method="post" action="{{ url_for('update_expire', code=code) }}">
                                    <select name="hours" class="expire-select">
                                        <option value="1">1小时</option>
                                        <option value="3">3小时</option>
                                        <option value="10">10小时</option>
                                        <option value="24">24小时</option>
                                    </select>
                                    <button type="submit" class="action-btn update-btn">更新</button>
                                </form>
                                <a href="{{ url_for('delete_file', code=code) }}" onclick="return confirm('确定要删除这个文件吗？');"><button class="action-btn delete-btn">删除</button></a>
                            </td>
                        </tr>
                    {% endfor %}
                </table>
            {% else %}
                <div class="no-files">暂无文件</div>
            {% endif %}
        </div>
    </div>
</body>
</html>''')
    
    # upload.html
    with open(os.path.join(template_folder, 'upload.html'), 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>上传文件</title>
    <link rel="icon" href="/css/all/Jsoft_logo.png" type="image/png">
    <link rel="stylesheet" href="/css/index/style.css">
    <style>
        .box {
            max-width: 500px;
            width: 90%;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 16px;
            color: #333;
        }
        .file-input {
            display: none;
        }
        .file-label {
            display: inline-block;
            padding: 12px 20px;
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .file-label:hover {
            background-color: #1976D2;
        }
        .file-name {
            margin-left: 10px;
            color: #666;
        }
        .expire-options {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .expire-option {
            flex: 1;
            min-width: 80px;
        }
        .expire-option input[type="radio"] {
            display: none;
        }
        .expire-option label {
            display: block;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .expire-option input[type="radio"]:checked + label {
            border-color: #2196F3;
            background-color: rgba(33, 150, 243, 0.1);
        }
        .btn {
            width: 100%;
            height: 50px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .btn:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .error {
            color: #f44336;
            margin-bottom: 15px;
            text-align: center;
        }
        .success {
            color: #4CAF50;
            margin-bottom: 15px;
            text-align: center;
            padding: 15px;
            border: 2px solid #4CAF50;
            border-radius: 10px;
            background-color: rgba(76, 175, 80, 0.1);
        }
        .code-display {
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 5px;
            color: #2196F3;
        }
        .progress-container {
            width: 100%;
            height: 20px;
            background-color: #f1f1f1;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-bar {
            height: 100%;
            background-color: #2196F3;
            width: 0%;
            transition: width 0.3s ease;
        }
        .uploading-text {
            text-align: center;
            margin-top: 10px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="box">
            <h2>上传文件</h2>
            {% if error %}
                <div class="error">{{ error }}</div>
            {% endif %}
            {% if success %}
                <div class="success">
                    <p>文件上传成功！</p>
                    <p>取件码：<span class="code-display">{{ code }}</span></p>
                    <p>请将取件码告知收件人</p>
                </div>
            {% else %}
                <form method="post" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="file">选择文件（最大50MB）</label>
                        <div>
                            <input type="file" id="file" name="file" class="file-input" required>
                            <label for="file" class="file-label">选择文件</label>
                            <span id="selected-file" class="file-name">未选择文件</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>有效期</label>
                        <div class="expire-options">
                            <div class="expire-option">
                                <input type="radio" id="expire-1" name="expire_hours" value="1" required>
                                <label for="expire-1">1小时</label>
                            </div>
                            <div class="expire-option">
                                <input type="radio" id="expire-3" name="expire_hours" value="3">
                                <label for="expire-3">3小时</label>
                            </div>
                            <div class="expire-option">
                                <input type="radio" id="expire-10" name="expire_hours" value="10">
                                <label for="expire-10">10小时</label>
                            </div>
                            <div class="expire-option">
                                <input type="radio" id="expire-24" name="expire_hours" value="24">
                                <label for="expire-24">24小时</label>
                            </div>
                        </div>
                    </div>
                    <button type="submit" class="btn" id="upload-btn">上传文件</button>
                </form>
            {% endif %}
        </div>
    </div>
    <script>
        // 文件选择预览
        document.getElementById('file').addEventListener('change', function() {
            if (this.files.length > 0) {
                document.getElementById('selected-file').textContent = this.files[0].name;
            } else {
                document.getElementById('selected-file').textContent = '未选择文件';
            }
        });
    </script>
</body>
</html>''')

if __name__ == '__main__':
    # 确保templates目录存在
    template_folder = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_folder):
        os.makedirs(template_folder)
        create_template_files(template_folder)
    
    app.run(debug=True, host='0.0.0.0', port=23478)