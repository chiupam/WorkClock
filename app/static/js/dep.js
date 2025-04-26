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
    if (data.success) {
      // 请求成功,保存用户数据到localStorage
      localStorage.setItem('userData', JSON.stringify({
        userId: data.userId,
        depId: data.depId,
        userName: data.userName,
        position: data.position,
        depName: data.depName,
        token: data.token
      }));
      // 重定向到指定页面
      window.location.href = data.redirect;
    } else {
      // 显示错误信息
      alert(data.message);
    }
  })
  .catch(error => {
    // 请求失败处理
    alert('操作失败');
    window.location.href = '/';
  });
}