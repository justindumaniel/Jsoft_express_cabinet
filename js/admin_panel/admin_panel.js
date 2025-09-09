// 标签切换功能
function switchTab(tabId) {
    // 隐藏所有标签内容
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.style.display = 'none';
    });
    
    // 移除所有标签的激活状态
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 显示选中的标签内容并激活对应标签
    document.getElementById(tabId).style.display = 'block';
    event.currentTarget.classList.add('active');
}

// 图片选择预览
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('background_image');
    const selectedImage = document.getElementById('selected-image');
    
    // 背景图文件选择
    if (fileInput && selectedImage) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                selectedImage.textContent = this.files[0].name;
            } else {
                selectedImage.textContent = '未选择图片';
            }
        });
    }
    
    // 网站图标文件选择
    const faviconInput = document.getElementById('favicon');
    const selectedFavicon = document.getElementById('selected-favicon');
    
    if (faviconInput && selectedFavicon) {
        faviconInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                selectedFavicon.textContent = this.files[0].name;
            } else {
                selectedFavicon.textContent = '未选择图标';
            }
        });
    }
    
    // 添加预览更新功能，确保每次切换到界面设置时都能显示最新背景和图标
    const interfaceTab = document.querySelector('.tab[onclick="switchTab(\'interface\')"]');
    if (interfaceTab) {
        interfaceTab.addEventListener('click', function() {
            setTimeout(function() {
                // 更新背景图预览
                const bgPreview = document.getElementById('current-bg-image');
                if (bgPreview) {
                    // 添加随机参数防止缓存
                    const timestamp = new Date().getTime();
                    bgPreview.src = '/css/all/bg.png?t=' + timestamp;
                }
                
                // 更新图标预览
                const faviconPreview = document.getElementById('current-favicon');
                if (faviconPreview) {
                    // 添加随机参数防止缓存
                    const timestamp = new Date().getTime();
                    faviconPreview.src = '/css/all/icon.png?t=' + timestamp;
                }
            }, 100);
        });
    }
});

// 重启后端按钮功能
document.getElementById('restart-btn').addEventListener('click', function() {
    // 直接使用confirm对话框确认重启
    if (confirm('确定要重启后端吗？此功能应仅在故障时使用')) {
        restartBackend();
    }
});

// 测试推送按钮功能
document.addEventListener('DOMContentLoaded', function() {
    const testPushBtn = document.getElementById('test_push_btn');
    if (testPushBtn) {
        testPushBtn.addEventListener('click', function() {
            // 发送AJAX请求到后端进行测试推送
            fetch('/admin/test_push', {
                method: 'POST',
                credentials: 'same-origin' // 包含cookie以保持会话
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('测试推送发送成功');
                } else {
                    alert('测试推送失败：' + data.message);
                }
            })
            .catch(error => {
                console.error('请求出错:', error);
                alert('测试推送请求失败');
            });
        });
    }
});

// 重启后端函数
function restartBackend() {
    // 发送AJAX请求到后端重启API
    fetch('/admin/restart_backend', {
        method: 'POST',
        credentials: 'same-origin' // 包含cookie以保持会话
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 显示重启中提示
            alert(data.message + '\n预计将在5秒后自动刷新页面...');
            
            // 显示倒计时提示
            const countdown = 5;
            let remaining = countdown;
            
            const countdownInterval = setInterval(() => {
                remaining--;
                if (remaining <= 0) {
                    clearInterval(countdownInterval);
                    // 后端重启后，刷新页面
                    window.location.reload();
                } else {
                    // 可以在控制台显示倒计时
                    console.log(`预计将在${remaining}秒后刷新...`);
                }
            }, 1000);
        } else {
            alert('重启失败：' + data.message);
        }
    })
    .catch(error => {
        console.error('请求出错:', error);
        alert('未收到后端重启反馈，请静待刷新，如超20秒没有刷新，即重启失败');
        // 即使请求失败，也尝试刷新页面
        setTimeout(function() {
            window.location.reload();
        }, 1000);
    });
}