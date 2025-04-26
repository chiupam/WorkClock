/**
 * 获取部门详细信息
 * @param {string} depId - 部门ID
 */
async function getDepartmentDetails(depId) {
  try {
    // 发送POST请求获取部门信息
    const response = await fetch('/admin/super', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ depId: depId })
    });

    if (!response.ok) {
      throw new Error('网络请求失败');
    }

    // 解析响应数据
    const result = await response.json();
    if (result.success) {
      // 更新当前页面内容,显示部门用户列表
      document.querySelector('.content').innerHTML = `
        <div class="user-list">
          ${result.users.map(user => `
            <div class="user-item">
              <div>
                <strong>${user.username}</strong>
                <span class="department-count">(${user.userid})</span>
              </div>
              <form action="/admin/user" method="POST" style="display: none;" id="form-${user.userid}">
                <input type="hidden" name="userId" value="${user.userid}">
                <input type="hidden" name="username" value="${user.username}">
                <input type="hidden" name="depId" value="${depId}">
              </form>
              <button onclick="submitForm('${user.userid}')" class="btn">查询</button>
            </div>
          `).join('')}
        </div>
      `;
    } else {
      // 显示错误信息
      alert(result.message || '获取部门详情失败');
    }
  } catch (error) {
    // 请求异常处理
    console.error('Error:', error);
    alert('操作失败：' + error.message);
  }
}

/**
 * 提交用户表单数据并处理响应
 * @param {string} userId - 用户ID
 */
function submitForm(userId) {
  // 获取对应用户ID的表单元素
  const form = document.getElementById(`form-${userId}`);
  // 创建FormData对象获取表单数据
  const formData = new FormData(form);
  
  // 发送POST请求到服务器
  fetch('/admin/user', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    // 将FormData转换为JSON字符串
    body: JSON.stringify(Object.fromEntries(formData))
  })
  .then(response => response.json())
  .then(data => {
    // 重定向到指定页面
    window.location.href = data.redirect
  })
  .catch(error => {
    // 请求失败处理
    alert('操作失败');
    window.location.href = '/';
  });
} 