// 页面加载完成后执行
window.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const codeInput = document.getElementById('codeInput');
    const numberBtns = document.querySelectorAll('.number-btn');
    const deleteBtn = document.querySelector('.delete-btn');
    const confirmBtn = document.querySelector('.confirm-btn');

    // 弹窗相关元素
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const countdown = document.getElementById('countdown');
    const countdownNumber = document.getElementById('countdown-number');
    const downloadInfo = document.getElementById('download-info');
    const modalClose = document.getElementById('modal-close');
    
    // 跟踪是否处于倒计时阶段
    let isInCountdownPhase = false;
    
    // 公告弹窗相关元素
    const announcementModal = document.getElementById('announcement-modal');
    const announcementContent = document.getElementById('announcement-content');
    const announcementClose = document.getElementById('announcement-close');
    
    // 检查公告弹窗DOM元素是否已正确加载
    console.log('公告弹窗元素加载检查:');
    console.log('announcementModal:', announcementModal);
    console.log('announcementContent:', announcementContent);
    console.log('announcementClose:', announcementClose);
    
    // 获取并显示公告
    fetchAnnouncement();

    // 检查DOM元素是否都已正确加载
    console.log('DOM元素加载检查:');
    console.log('codeInput:', codeInput);
    console.log('numberBtns:', numberBtns);
    console.log('deleteBtn:', deleteBtn);
    console.log('confirmBtn:', confirmBtn);
    console.log('modal:', modal);

    // 数字按钮点击事件
    numberBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // 检查输入框内容长度是否小于4
            if (codeInput.value.length < 4) {
                // 添加数字到输入框
                codeInput.value += btn.textContent;
                console.log('输入数字:', btn.textContent, '当前输入:', codeInput.value);
            }
        });
    });

    // 删除按钮点击事件
    deleteBtn.addEventListener('click', () => {
        // 删除最后一个字符
        codeInput.value = codeInput.value.slice(0, -1);
        console.log('删除字符，当前输入:', codeInput.value);
    });

    // 显示弹窗函数
    function showModal(title, message, showCountdown = false, showDownloadInfo = false) {
        console.log('显示弹窗:', title, message);
        modalTitle.textContent = title;
        modalMessage.textContent = message;
        
        countdown.style.display = showCountdown ? 'block' : 'none';
        downloadInfo.style.display = showDownloadInfo ? 'block' : 'none';
        
        // 在倒计时阶段隐藏关闭按钮，其他情况下显示关闭按钮
        if (showCountdown) {
            modalClose.style.display = 'none';
            isInCountdownPhase = true;
        } else {
            modalClose.style.display = 'inline-block';
            isInCountdownPhase = false;
        }
        
        modal.style.display = 'flex';
    }

    // 隐藏弹窗函数
    function hideModal() {
        console.log('隐藏弹窗');
        modal.style.display = 'none';
    }
    
    // 显示公告弹窗函数
    function showAnnouncementModal(content) {
        console.log('显示公告弹窗:', content);
        announcementContent.textContent = content;
        announcementModal.style.display = 'flex';
    }
    
    // 隐藏公告弹窗函数
    function hideAnnouncementModal() {
        console.log('隐藏公告弹窗');
        announcementModal.style.display = 'none';
    }
    
    // 获取公告内容
    function fetchAnnouncement() {
        console.log('开始获取公告内容');
        fetch('/get_announcement')
            .then(response => {
                console.log('公告响应状态:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP错误! 状态码: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('公告响应数据:', data);
                if (data.announcement && data.announcement.trim() !== '') {
                    // 有公告内容，显示公告弹窗
                    showAnnouncementModal(data.announcement);
                } else {
                    console.log('没有公告内容');
                }
            })
            .catch(error => {
                console.error('获取公告时出错:', error);
                // 出错时不显示公告，避免影响用户体验
            });
    }

    // 关闭弹窗按钮点击事件
    modalClose.addEventListener('click', hideModal);
    
    // 关闭公告弹窗按钮点击事件
    announcementClose.addEventListener('click', hideAnnouncementModal);

    // 点击弹窗外部关闭弹窗
    // 倒计时阶段不允许通过点击空白处关闭弹窗
    modal.addEventListener('click', (e) => {
        if (e.target === modal && !isInCountdownPhase) {
            hideModal();
        }
    });
    
    // 点击公告弹窗外部关闭弹窗
    announcementModal.addEventListener('click', (e) => {
        if (e.target === announcementModal) {
            hideAnnouncementModal();
        }
    });

    // 确认按钮点击事件
    confirmBtn.addEventListener('click', () => {
        const code = codeInput.value;
        console.log('点击确认按钮，取件码:', code);
        
        // 检查取件码是否为4位数字
        if (code.length === 4 && /^\d{4}$/.test(code)) {
            // 验证取件码并获取文件信息
            verifyCode(code);
        } else {
            showModal('提示', '请输入4位数字的取件码');
        }
    });

    // 验证取件码并获取文件信息
    function verifyCode(code) {
        console.log('开始验证取件码:', code);
        // 发送请求到后端验证取件码
        fetch(`/verify_code?code=${code}`)
            .then(response => {
                console.log('验证响应状态:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP错误! 状态码: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('验证响应数据:', data);
                if (data.exists) {
                    // 文件存在，显示倒计时弹窗
                    showModal('文件已找到', `您的文件已找到：${data.filename}`, true, false);
                    
                    // 倒计时3秒后开始下载
                    let seconds = 3;
                    countdownNumber.textContent = seconds;
                    
                    const countdownInterval = setInterval(() => {
                        seconds--;
                        countdownNumber.textContent = seconds;
                        console.log('倒计时:', seconds);
                        
                        if (seconds <= 0) {
                            clearInterval(countdownInterval);
                            
                            // 清空输入框
                            codeInput.value = '';
                            
                            // 更新取件码和有效期，然后使用新取件码下载
                            updateCodeAndExpiry(code, function(newCode) {
                                // 使用更新后的取件码下载文件
                                downloadFile(newCode);
                                
                                // 更新弹窗信息
                                showModal('下载开始', `您的文件 ${data.filename} 正在下载中`, false, true);
                            });
                        }
                    }, 1000);
                } else {
                    // 文件不存在或已过期
                    showModal('提示', '取件码不存在或文件已过期');
                }
            })
            .catch(error => {
                console.error('验证取件码时出错:', error);
                showModal('错误', `验证取件码时发生错误: ${error.message}`);
            });
    }

    // 下载文件
    function downloadFile(code) {
        console.log('开始下载文件，取件码:', code);
        // 创建下载链接并触发下载
        const downloadLink = document.createElement('a');
        downloadLink.href = `/download?new_code=${code}`;
        downloadLink.style.display = 'none';
        document.body.appendChild(downloadLink);
        console.log('触发下载点击事件');
        downloadLink.click();
        document.body.removeChild(downloadLink);
        console.log('下载链接已移除');
    }

    // 更新取件码和有效期
    function updateCodeAndExpiry(oldCode, callback) {
        fetch('/update_code_and_expiry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ old_code: oldCode })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('更新取件码和有效期时出错:', data.message);
                // 如果出错，使用旧取件码继续下载
                if (callback) callback(oldCode);
            } else {
                console.log('取件码和有效期更新成功，新取件码:', data.new_code);
                // 调用回调函数，传递新取件码
                if (callback) callback(data.new_code);
            }
        })
        .catch(error => {
            console.error('更新取件码和有效期时发生网络错误:', error);
            // 如果出错，使用旧取件码继续下载
            if (callback) callback(oldCode);
        });
    }

    // 添加键盘支持
    document.addEventListener('keydown', (e) => {
        // 数字键(0-9)或小键盘数字键(96-105)
        const keyCode = e.keyCode;
        
        // 检查是否是数字键
        if ((keyCode >= 48 && keyCode <= 57) || (keyCode >= 96 && keyCode <= 105)) {
            // 阻止默认行为
            e.preventDefault();
            
            // 获取数字
            const num = (keyCode >= 96) ? keyCode - 96 : keyCode - 48;
            
            // 添加到输入框
            if (codeInput.value.length < 4) {
                codeInput.value += num;
                console.log('键盘输入数字:', num, '当前输入:', codeInput.value);
            }
        } 
        // 退格键
        else if (keyCode === 8) {
            e.preventDefault();
            codeInput.value = codeInput.value.slice(0, -1);
            console.log('键盘删除字符，当前输入:', codeInput.value);
        } 
        // 回车键或空格键（确认）
        else if (keyCode === 13 || keyCode === 32) {
            e.preventDefault();
            // 触发确认按钮点击事件
            confirmBtn.click();
        }
        // Escape键（关闭弹窗）
        else if (keyCode === 27 && modal.style.display === 'flex') {
            e.preventDefault();
            hideModal();
        }
    });

    // 初始化完成
    console.log('文件快递柜页面初始化完成');
});