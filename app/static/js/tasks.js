/**
 * 切换显示不同的任务标签页
 * @param {string} tabId - 要显示的标签页ID ('settings'或'logs')
 */
function showTab(tabId) {
  // 隐藏所有内容
  document.querySelectorAll('.task-content').forEach(content => {
    content.classList.remove('active');
  });
  
  // 取消所有标签选中状态
  document.querySelectorAll('.task-tab').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // 显示选中的内容
  document.getElementById(tabId).classList.add('active');
  
  // 选中对应的标签
  document.querySelectorAll('.task-tab').forEach(tab => {
    if (tab.textContent.includes(tabId === 'settings' ? '任务设置' : '执行记录')) {
      tab.classList.add('active');
    }
  });
}

